"""Sandbox-only catalogue checkout. Single-process, durable financial intents."""
import json
import threading
import time
import os
import sqlite3
from pathlib import Path
from contextlib import closing
from urllib.parse import urlparse
from sqlalchemy import text
from fastapi import HTTPException
from .. import paypal
from ..config import settings


def amount(cents):
    return {'currency_code':'USD', 'value':f'{cents/100:.2f}'}


class Payments:
    operation_lock = threading.Lock()
    def __init__(self, jobs):
        self.jobs = jobs
        self.engine = jobs.engine
        self.lock = self.operation_lock

    def migrate(self):
        database=self.engine.url.database
        if database and database!=':memory:' and Path(database).exists():
            backup=database+'.before-catalog-v2.sqlite'
            with self.engine.connect() as db:
                installed=db.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_payments'")).first()
            if not installed and not Path(backup).exists():
                fd=os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
                try:
                    with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(backup)) as target:
                        source.backup(target)
                except Exception:
                    Path(backup).unlink(missing_ok=True)
                    raise
        with self.engine.begin() as db:
            db.execute(text('''CREATE TABLE IF NOT EXISTS catalog_payments (
                job_id TEXT PRIMARY KEY, state TEXT NOT NULL, order_id TEXT,
                approval_url TEXT, capture_id TEXT, refund_id TEXT,
                create_at REAL, capture_at REAL, refund_at REAL)'''))
            db.execute(text('INSERT OR IGNORE INTO catalog_migrations(version) VALUES (2)'))

    def row(self, job_id):
        with self.engine.connect() as db:
            result=db.execute(text('SELECT * FROM catalog_payments WHERE job_id=:id'),{'id':job_id}).mappings().first()
            return dict(result) if result else None

    def update(self, job_id, **values):
        allowed={'state','order_id','approval_url','capture_id','refund_id','create_at','capture_at','refund_at'}
        assert set(values) <= allowed
        with self.engine.begin() as db:
            db.execute(text('UPDATE catalog_payments SET '+','.join(k+'=:'+k for k in values)+' WHERE job_id=:job_id'), {**values,'job_id':job_id})

    def view(self, job):
        payment=self.row(job['id']) if job['snapshot']['payment_mode']=='sandbox' else None
        if payment:
            payment={k:v for k,v in payment.items() if k not in {'create_at','capture_at','refund_at'}}
            if payment['state']=='captured' and job['status']=='completed' and job['settlement']['refund_eligible_cents']:
                payment['state']='refund_required'
        return {**job, 'payment':payment}

    def require_sandbox(self, job):
        if job['snapshot']['payment_mode']!='sandbox':
            raise HTTPException(409,'This operation requires a Sandbox order')
        if not settings().catalog_paypal_sandbox_enabled:
            raise HTTPException(503,'Catalogue Sandbox payments are disabled')

    def reserve(self, job_id, operation, state):
        row=self.row(job_id)
        key=operation+'_at'
        if row[key] and time.time()-row[key]>3600:
            raise HTTPException(409,'Uncertain old payment operation requires manual reconciliation; do not create a replacement transaction')
        self.update(job_id, **{key:row[key] or time.time(),'state':state})

    def checkout(self, job_id, token):
        with self.lock:
            job=self.jobs.get(job_id,token)
            self.require_sandbox(job)
            with self.engine.begin() as db:
                db.execute(text("INSERT OR IGNORE INTO catalog_payments(job_id,state) VALUES (:id,'creating')"),{'id':job_id})
            row=self.row(job_id)
            if row['order_id']:
                return self.view(job)
            self.reserve(job_id,'create','creating')
            url=settings().public_url.rstrip('/')
            response=paypal.call('/v2/checkout/orders',{
                'intent':'CAPTURE','purchase_units':[{'reference_id':job_id,'custom_id':job_id,
                    'description':'ServicePromise catalogue processing (Sandbox)',
                    'amount':amount(job['snapshot']['quoted_cents'])}],
                'payment_source':{'paypal':{'experience_context':{
                    'return_url':url+'/?catalog='+job_id+'&approved=1',
                    'cancel_url':url+'/?catalog='+job_id+'&cancelled=1','user_action':'PAY_NOW'}}},
            },'cat-create-'+job_id)
            approval=next((link['href'] for link in response.get('links',[]) if link.get('rel') in {'approve','payer-action'}),None)
            if not approval or urlparse(approval).scheme!='https' or urlparse(approval).hostname!='www.sandbox.paypal.com':
                raise HTTPException(502,'PayPal did not provide a Sandbox approval URL')
            self.update(job_id,state='awaiting_approval',order_id=response['id'],approval_url=approval)
            return self.view(job)

    def capture(self, job_id, token):
        with self.lock:
            job=self.jobs.get(job_id,token)
            self.require_sandbox(job)
            row=self.row(job_id)
            if not row or not row['order_id']:
                raise HTTPException(409,'Create checkout and approve it before capture')
            if row['capture_id']:
                self.jobs.queue_paid(job_id)
                return self.view(self.jobs.get(job_id,token))
            # Reconcile an uncertain capture by reading its order before retrying.
            response=paypal.call('/v2/checkout/orders/'+row['order_id'],None,'cat-read-'+job_id,method='GET')
            if response.get('status')!='COMPLETED':
                self.reserve(job_id,'capture','capture_requested')
                response=paypal.call('/v2/checkout/orders/'+row['order_id']+'/capture',{},'cat-capture-'+job_id)
            captures=[c for u in response.get('purchase_units',[]) for c in u.get('payments',{}).get('captures',[])]
            if response.get('status')!='COMPLETED' or len(captures)!=1 or captures[0].get('status')!='COMPLETED' or captures[0].get('amount')!=amount(job['snapshot']['quoted_cents']):
                raise HTTPException(409,'PayPal has not confirmed the exact captured amount; no delivery started')
            self.update(job_id,state='captured',capture_id=captures[0]['id'])
            self.jobs.queue_paid(job_id)
            return self.view(self.jobs.get(job_id,token))

    def refund(self, job_id, token):
        with self.lock:
            job=self.jobs.get(job_id,token)
            self.require_sandbox(job)
            row=self.row(job_id)
            if not row or not row['capture_id'] or job['status']!='completed' or not job['settlement']:
                raise HTTPException(409,'Captured payment and completed delivery are required')
            cents=job['settlement']['refund_eligible_cents']
            if not 0<cents<=job['snapshot']['quoted_cents']:
                raise HTTPException(409,'No policy refund is eligible')
            if row['refund_id']:
                return self._reconcile(job,row)
            self.reserve(job_id,'refund','refund_requested')
            response=paypal.call('/v2/payments/captures/'+row['capture_id']+'/refund',{
                'amount':amount(cents),'note_to_payer':'Sandbox: service fee for undelivered catalogue items'},'cat-refund-'+job_id)
            self._save_refund(job,response)
            return self.view(job)

    def _save_refund(self, job, response):
        if response.get('status') not in {'COMPLETED','PENDING'} or not response.get('id') or response.get('amount')!=amount(job['settlement']['refund_eligible_cents']):
            raise HTTPException(502,'PayPal did not confirm the expected refund; retry the same operation')
        self.update(job['id'],refund_id=response['id'],state='refunded' if response['status']=='COMPLETED' else 'refund_pending')

    def _reconcile(self, job, row):
        if row['state']!='refunded':
            response=paypal.call('/v2/payments/refunds/'+row['refund_id'],None,'cat-refund-read-'+job['id'],method='GET')
            self._save_refund(job,response)
        return self.view(job)

    def reconcile(self, job_id, token):
        with self.lock:
            job=self.jobs.get(job_id,token)
            self.require_sandbox(job)
            row=self.row(job_id)
            return self._reconcile(job,row) if row and row['refund_id'] else self.view(job)
