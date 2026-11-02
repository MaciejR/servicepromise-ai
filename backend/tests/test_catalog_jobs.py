from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from sqlalchemy import create_engine
from app.catalog.jobs import Jobs
from app.catalog.providers import RuleProvider

CSV = b'source_id,sku,name,price,currency,supplier_text\n1,001,Pillow,20.00,PLN,Color: blue. Material: cotton.\n2,002,Case,30.00,PLN,Color: green.\n'


@pytest.fixture
def store(tmp_path):
    jobs = Jobs(create_engine('sqlite:///'+str(tmp_path/'catalog.db'), connect_args={'check_same_thread':False}))
    jobs.migrate()
    return jobs


def test_migration_reentrant_and_quote_immutable(store):
    store.migrate()
    job = store.create(CSV, 'PLN')
    assert job['snapshot']['quoted_cents'] == 200
    original = job['snapshot']
    assert not store.tick()  # No processing before simulated capture.
    store.checkout(job['id'], job['access_token'])
    store.tick()
    final = store.get(job['id'], job['access_token'])
    assert final['snapshot'] == original
    assert final['settlement']['refund_eligible_cents'] == 100
    assert final['settlement']['payment_executed'] is False
    assert '001' in final['export'] and '002' not in final['export']
    assert store.checkout(job['id'], job['access_token']) == final
    assert not store.tick()


def test_capability_required(store):
    job = store.create(CSV, 'PLN')
    with pytest.raises(KeyError):
        store.get(job['id'], 'wrong')
    with pytest.raises(KeyError):
        store.checkout(job['id'], '')


def test_restart_resumes_without_regenerating_completed_items(store):
    class Crash(RuleProvider):
        def extract(self, rows, feedback=None):
            if rows[0].source_id == '2':
                raise RuntimeError('simulated process death')
            return super().extract(rows, feedback)
    job = store.create(CSV, 'PLN')
    store.checkout(job['id'], job['access_token'])
    with pytest.raises(RuntimeError):
        store.tick(Crash())
    restarted = Jobs(store.engine)
    restarted.recover()
    class Resume(RuleProvider):
        def extract(self, rows, feedback=None):
            assert rows[0].source_id != '1'
            return super().extract(rows, feedback)
    restarted.tick(Resume())
    final = restarted.get(job['id'], job['access_token'])
    assert final['status'] == 'completed'
    assert len(final['results'][0]['attempts']) == 1
    assert len(final['results'][1]['attempts']) == 2


def test_concurrent_workers_settle_once(store):
    job = store.create(CSV, 'PLN')
    store.checkout(job['id'], job['access_token'])
    with ThreadPoolExecutor(max_workers=3) as pool:
        claims = list(pool.map(lambda _: store.tick(), range(3)))
    assert sum(claims) == 1
    assert store.get(job['id'], job['access_token'])['status'] == 'completed'


def test_api_flow(store, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.catalog import routes
    monkeypatch.setattr(routes, 'jobs', store)
    with TestClient(app) as client:
        response = client.post('/api/catalog/jobs', json={'csv': CSV.decode(), 'currency':'PLN'})
        assert response.status_code == 201
        job = response.json()
        url = '/api/catalog/jobs/'+job['id']
        headers = {'Authorization':'Bearer '+job['access_token']}
        assert client.get(url).status_code == 404
        assert client.get(url+'/products.csv', headers=headers).status_code == 409
        assert client.post(url+'/checkout', headers=headers).status_code == 200
        for _ in range(100):
            result = client.get(url, headers=headers).json()
            if result['status'] == 'completed':
                break
            time.sleep(0.01)
        assert result['status'] == 'completed'
        assert result['settlement']['refund_eligible_cents'] == 100
        assert client.get(url+'/products.csv', headers=headers).status_code == 200
        assert client.get(url+'/report.json').status_code == 404
        evidence = client.get(url+'/report.json', headers=headers)
        assert evidence.status_code == 200
        assert 'token' not in evidence.text
        assert evidence.json()['settlement']['payment_executed'] is False


def test_first_migration_backs_up_legacy_data_without_rewriting_it(tmp_path):
    import sqlite3
    path = tmp_path/'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE orders(id TEXT, policy TEXT)')
        db.execute("INSERT INTO orders VALUES ('legacy-1','original-v1')")
    jobs = Jobs(create_engine('sqlite:///'+str(path)))
    jobs.migrate()
    with sqlite3.connect(str(path)+'.before-catalog-v1.sqlite') as backup:
        assert backup.execute('SELECT * FROM orders').fetchall() == [('legacy-1','original-v1')]
    jobs.migrate()
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT * FROM orders').fetchall() == [('legacy-1','original-v1')]


def test_real_model_jobs_require_operator_at_creation(store, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.catalog import routes
    from app.config import settings
    monkeypatch.setattr(routes, 'jobs', store)
    cfg = settings()
    monkeypatch.setattr(cfg, 'operator_token', 'x'*40)
    monkeypatch.setattr(cfg, 'azure_openai_endpoint', 'https://example.invalid')
    monkeypatch.setattr(cfg, 'azure_openai_api_key', 'test-only')
    monkeypatch.setattr(cfg, 'azure_openai_deployment', 'test-only')
    with TestClient(app) as client:
        body = {'csv': CSV.decode(), 'currency':'PLN', 'provider':'azure'}
        assert client.post('/api/catalog/jobs', json=body).status_code == 403
        result = client.post('/api/catalog/jobs', json=body, headers={'X-Operator-Token':'x'*40})
        assert result.status_code == 201
        assert result.json()['snapshot']['provider'] == 'azure'
        assert result.json()['status'] == 'quoted'
