import pytest
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from fastapi import HTTPException
from app.catalog.jobs import Jobs
from app.catalog.payments import Payments, amount
from app.catalog.providers import RuleProvider
from app.config import settings
from app import paypal

CSV=b'source_id,sku,name,price,currency,supplier_text\n1,001,Blue cover,20.00,PLN,Color: blue. Material: cotton.\n2,002,Green cover,30.00,PLN,Color: green.\n'


@pytest.fixture
def flow(tmp_path,monkeypatch):
    jobs=Jobs(create_engine('sqlite:///'+str(tmp_path/'payments.db'),connect_args={'check_same_thread':False}))
    jobs.migrate();payments=Payments(jobs);payments.migrate()
    monkeypatch.setattr(settings(),'catalog_paypal_sandbox_enabled',True)
    calls=[]
    def provider(path,payload,request_id,method='POST'):
        calls.append((path,payload,request_id,method))
        if path=='/v2/checkout/orders':
            return {'id':'ORDER-1','links':[{'rel':'payer-action','href':'https://www.sandbox.paypal.com/checkoutnow?token=ORDER-1'}]}
        if path=='/v2/checkout/orders/ORDER-1' and method=='GET':return {'status':'APPROVED'}
        if path.endswith('/capture'):
            return {'status':'COMPLETED','purchase_units':[{'payments':{'captures':[{'id':'CAP-1','status':'COMPLETED','amount':amount(200)}]}}]}
        if path.endswith('/refund'):
            return {'id':'REF-1','status':'PENDING','amount':amount(100)}
        if path=='/v2/payments/refunds/REF-1':
            return {'id':'REF-1','status':'COMPLETED','amount':amount(100)}
        raise AssertionError('Unexpected provider operation')
    monkeypatch.setattr(paypal,'call',provider)
    job=jobs.create(CSV,'PLN','rules','sandbox')
    return jobs,payments,job,calls


def test_sandbox_cannot_be_queued_by_demo_checkout(flow):
    jobs,payments,job,calls=flow
    with pytest.raises(ValueError):jobs.checkout(job['id'],job['access_token'])
    assert not jobs.tick()
    assert not calls


def test_capture_gates_delivery_and_refund_requires_completion(flow):
    jobs,payments,job,calls=flow
    with pytest.raises(HTTPException):payments.capture(job['id'],job['access_token'])
    payments.checkout(job['id'],job['access_token'])
    assert not jobs.tick()
    with pytest.raises(HTTPException):payments.refund(job['id'],job['access_token'])
    payments.capture(job['id'],job['access_token'])
    jobs.tick(RuleProvider())
    result=payments.view(jobs.get(job['id'],job['access_token']))
    assert result['payment']['state']=='refund_required'
    assert result['settlement']['simulation'] is False
    assert result['settlement']['payment_environment']=='sandbox'


def test_repeated_refund_and_restart_preserve_single_operation(flow):
    jobs,payments,job,calls=flow
    payments.checkout(job['id'],job['access_token']);payments.capture(job['id'],job['access_token']);jobs.tick()
    first=payments.refund(job['id'],job['access_token'])
    assert first['payment']['state']=='refund_pending'
    restarted=Payments(Jobs(jobs.engine))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _: restarted.refund(job['id'],job['access_token']),range(3)))
    assert all(r['payment']['state']=='refunded' for r in results)
    assert sum(p.endswith('/refund') and m=='POST' for p,_,_,m in calls)==1
    assert restarted.capture(job['id'],job['access_token'])['status']=='completed'
    assert sum(p.endswith('/capture') for p,_,_,_ in calls)==1


def test_wrong_capture_amount_never_starts_processing(flow,monkeypatch):
    jobs,payments,job,calls=flow
    payments.checkout(job['id'],job['access_token'])
    original=paypal.call
    def wrong(path,payload,key,method='POST'):
        value=original(path,payload,key,method)
        if path.endswith('/capture'):value['purchase_units'][0]['payments']['captures'][0]['amount']=amount(1)
        return value
    monkeypatch.setattr(paypal,'call',wrong)
    with pytest.raises(HTTPException):payments.capture(job['id'],job['access_token'])
    assert jobs.get(job['id'],job['access_token'])['status']=='quoted'
    assert not jobs.tick()


def test_old_uncertain_operation_is_not_reissued(flow):
    jobs,payments,job,calls=flow
    with jobs.engine.begin() as db:
        db.execute(text("INSERT INTO catalog_payments(job_id,state,create_at) VALUES (:id,'creating',1)"),{'id':job['id']})
    with pytest.raises(HTTPException):payments.checkout(job['id'],job['access_token'])
    assert not calls


def test_approval_url_must_be_sandbox(flow,monkeypatch):
    jobs,payments,job,calls=flow
    monkeypatch.setattr(paypal,'call',lambda *a,**k:{'id':'BAD','links':[{'rel':'approve','href':'https://www.paypal.com/checkoutnow?token=BAD'}]})
    with pytest.raises(HTTPException):payments.checkout(job['id'],job['access_token'])


def test_refund_amount_is_fixed_and_full_refund_is_supported(flow,monkeypatch):
    jobs,payments,job,calls=flow
    payments.checkout(job['id'],job['access_token']);payments.capture(job['id'],job['access_token'])
    class Failing(RuleProvider):
        def extract(self,rows,feedback=None):
            from app.catalog.providers import ProviderError
            raise ProviderError('Unavailable')
    jobs.tick(Failing())
    original=paypal.call
    def full(path,payload,key,method='POST'):
        if path.endswith('/refund'):
            assert payload['amount']==amount(200)
            return {'id':'FULL','status':'COMPLETED','amount':amount(200)}
        return original(path,payload,key,method)
    monkeypatch.setattr(paypal,'call',full)
    assert payments.refund(job['id'],job['access_token'])['payment']['state']=='refunded'
