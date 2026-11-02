"""Durable, single-instance SQLite catalogue jobs. Demo payments and rules only."""
import hashlib
import json
import secrets
import threading
import time
import os
import sqlite3
from pathlib import Path
from contextlib import closing
from uuid import uuid4
from sqlalchemy import text
from .core import ALIASES, VERSION, Extraction, SourceRow, export_csv, preflight, settlement, validate
from .providers import AzureProvider, ProviderError, RuleProvider


class Jobs:
    def __init__(self, engine):
        self.engine = engine
        self.lock = threading.Lock()

    def migrate(self):
        if self.engine.dialect.name != 'sqlite':
            return
        # Online SQLite backup preserves a consistent legacy database before
        # the first catalogue migration; never overwrite the original snapshot.
        database = self.engine.url.database
        if database and database != ':memory:' and Path(database).exists():
            with self.engine.connect() as connection:
                installed = connection.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_migrations'")).first()
            if not installed:
                backup = database + '.before-catalog-v1.sqlite'
                try:
                    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    pass
                else:
                    os.close(fd)
                    try:
                        with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(backup)) as target:
                            source.backup(target)
                    except Exception:
                        Path(backup).unlink(missing_ok=True)
                        raise
        # Additive migration: no changes to legacy orders or their policy.
        with self.engine.begin() as db:
            db.execute(text('CREATE TABLE IF NOT EXISTS catalog_migrations (version INTEGER PRIMARY KEY)'))
            db.execute(text('''CREATE TABLE IF NOT EXISTS catalog_jobs (
                id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, status TEXT NOT NULL,
                snapshot TEXT NOT NULL, results TEXT NOT NULL DEFAULT '[]',
                export TEXT, settlement TEXT, deadline REAL, created_at REAL NOT NULL)'''))
            db.execute(text('INSERT OR IGNORE INTO catalog_migrations(version) VALUES (1)'))

    def recover(self):
        # Only one application process/worker is supported. Call at startup.
        with self.engine.begin() as db:
            db.execute(text("UPDATE catalog_jobs SET status='queued' WHERE status='running'"))

    def create(self, data, currency, provider='rules'):
        if provider not in {'rules', 'azure'}:
            raise ValueError('Unsupported extraction provider')
        quote = preflight(data, currency)
        if not quote['rows']:
            raise ValueError('No valid rows to quote')
        token = secrets.token_urlsafe(32)
        snapshot = {k: v for k, v in quote.items() if k != 'rows'}
        snapshot.update(rows=[r.model_dump() for r in quote['rows']], aliases=ALIASES,
                        unit_cents=100, max_attempts=2, provider=provider, payment_mode='demo')
        job_id = str(uuid4())
        with self.engine.begin() as db:
            db.execute(text('INSERT INTO catalog_jobs(id,token_hash,status,snapshot,created_at) VALUES (:id,:token,:status,:snapshot,:at)'),
                       dict(id=job_id, token=hashlib.sha256(token.encode()).hexdigest(), status='quoted',
                            snapshot=json.dumps(snapshot), at=time.time()))
        return {**self.get(job_id, token), 'access_token': token}

    def get(self, job_id, token):
        with self.engine.connect() as db:
            row = db.execute(text('SELECT * FROM catalog_jobs WHERE id=:id'), {'id': job_id}).mappings().first()
        if row is None or not secrets.compare_digest(row['token_hash'], hashlib.sha256(token.encode()).hexdigest()):
            raise KeyError('Job not found')
        return {'id': row['id'], 'status': row['status'], 'snapshot': json.loads(row['snapshot']),
                'results': json.loads(row['results']), 'settlement': json.loads(row['settlement']) if row['settlement'] else None,
                'export': row['export']}

    def checkout(self, job_id, token):
        self.get(job_id, token)
        with self.engine.begin() as db:
            db.execute(text("UPDATE catalog_jobs SET status='queued', deadline=:deadline WHERE id=:id AND status='quoted'"),
                       {'id': job_id, 'deadline': time.time()+600})
        return self.get(job_id, token)

    def tick(self, provider=None):
        if not self.lock.acquire(blocking=False):
            return False
        try:
            return self._tick(provider)
        finally:
            self.lock.release()

    def _tick(self, provider=None):
        with self.engine.begin() as db:
            job = db.execute(text("SELECT * FROM catalog_jobs WHERE status='queued' ORDER BY created_at LIMIT 1")).mappings().first()
            if not job:
                return False
            claimed = db.execute(text("UPDATE catalog_jobs SET status='running' WHERE id=:id AND status='queued'"), {'id': job['id']})
            if claimed.rowcount != 1:
                return False
        snapshot = json.loads(job['snapshot'])
        if provider is None:
            if snapshot['provider'] == 'azure':
                try:
                    provider = AzureProvider()
                except (ProviderError, ValueError):
                    class Unavailable(RuleProvider):
                        def extract(self, rows, feedback=None):
                            raise ProviderError('Provider configuration unavailable')
                    provider = Unavailable()
            else:
                provider = RuleProvider()
        outcomes = json.loads(job['results'])
        rows = [SourceRow(**r) for r in snapshot['rows']]
        compatible = snapshot['contract'] == VERSION and snapshot['aliases'] == ALIASES
        for row in rows:
            current = next((r for r in outcomes if r['source_id'] == row.source_id), None)
            if current is None:
                current = {'source_id': row.source_id, 'status': 'undelivered', 'attempts': [], 'issues': [], 'extraction': {}}
                outcomes.append(current)
            if current['status'] == 'accepted':
                continue
            while len(current['attempts']) < snapshot['max_attempts'] and compatible and time.time() < job['deadline']:
                # Reserve an attempt durably before the external operation. A
                # crash consumes that attempt, bounding model costs on restart.
                attempt = {'number': len(current['attempts'])+1, 'issues': ['interrupted_attempt']}
                current['attempts'].append(attempt)
                self._checkpoint(job['id'], outcomes)
                try:
                    candidate = provider.extract([row], {row.source_id: current['issues']}).get(row.source_id, Extraction(source_id=row.source_id))
                    issues = validate(row, candidate)
                except ProviderError:
                    candidate, issues = Extraction(source_id=row.source_id), ['provider_error']
                attempt['issues'] = issues
                current.update(issues=issues, extraction=candidate.model_dump(), status='accepted' if not issues else 'undelivered')
                self._checkpoint(job['id'], outcomes)
                if not issues:
                    break
            if current['status'] != 'accepted' and not current['issues']:
                current['issues'] = ['contract_unavailable' if not compatible else 'deadline_or_attempts_exhausted']
                self._checkpoint(job['id'], outcomes)
        try:
            exported = export_csv(rows, outcomes)
        except ValueError:
            exported = None
            for result in outcomes:
                result.update(status='undelivered', issues=['export_failed'])
        final = settlement(outcomes)
        # No PayPal call. Final result and its sole simulated settlement are
        # committed atomically; completed jobs are never selected again.
        with self.engine.begin() as db:
            db.execute(text("UPDATE catalog_jobs SET status='completed', results=:results, export=:export, settlement=:settlement WHERE id=:id AND status='running'"),
                       {'id': job['id'], 'results': json.dumps(outcomes), 'export': exported, 'settlement': json.dumps(final)})
        return True

    def _checkpoint(self, job_id, results):
        with self.engine.begin() as db:
            db.execute(text('UPDATE catalog_jobs SET results=:results WHERE id=:id'), {'id': job_id, 'results': json.dumps(results)})
