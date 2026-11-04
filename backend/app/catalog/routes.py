import threading
import secrets
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field
from ..db import engine
from .core import ContractError, assess_source
from .jobs import Jobs
from ..config import settings
from .payments import Payments

router = APIRouter(prefix='/api/catalog/jobs', tags=['Catalogue demo'])
jobs = Jobs(engine)


class Input(BaseModel):
    csv: str = Field(min_length=1, max_length=262144)
    currency: str = Field(pattern='^(PLN|USD|EUR|GBP)$')
    provider: str = Field(default='rules', pattern='^(rules|azure)$')
    payment_mode: str = Field(default='demo', pattern='^(demo|sandbox)$')


def require_operator(value):
    cfg=settings()
    if len(cfg.operator_token)<32 or not secrets.compare_digest(value,cfg.operator_token):
        raise HTTPException(403,'This Sandbox/model operation requires the operator token')


def token(header):
    if engine.dialect.name != 'sqlite':
        raise HTTPException(503, 'Catalogue prototype requires single-instance SQLite')
    return header.removeprefix('Bearer ') if header.startswith('Bearer ') else ''


@router.post('', status_code=201)
def create(body: Input, x_operator_token: str = Header(default='')):
    token('')
    if body.provider == 'azure' or body.payment_mode == 'sandbox':
        require_operator(x_operator_token)
    if body.payment_mode == 'sandbox':
        cfg=settings()
        if not cfg.catalog_paypal_sandbox_enabled or not all([cfg.paypal_client_id,cfg.paypal_client_secret]):
            raise HTTPException(503,'Catalogue Sandbox payments are not configured')
    if body.provider == 'azure':
        cfg = settings()
        if not all([cfg.azure_openai_endpoint, cfg.azure_openai_api_key, cfg.azure_openai_deployment]):
            raise HTTPException(503, 'Azure extraction is not configured')
    try:
        return jobs.create(body.csv.encode(), body.currency, body.provider, body.payment_mode,
                           source_assessment=True)
    except (ContractError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from None


@router.post('/assessment')
def assessment(body: Input):
    try:
        return assess_source(body.csv.encode(), body.currency)
    except ContractError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get('/{job_id}')
def read(job_id: str, authorization: str = Header(default='')):
    try:
        result = jobs.get(job_id, token(authorization))
        return Payments(jobs).view({k: v for k, v in result.items() if k != 'export'})
    except KeyError:
        raise HTTPException(404, 'Job not found') from None


@router.post('/{job_id}/checkout')
def checkout(job_id: str, authorization: str = Header(default='')):
    try:
        access=token(authorization)
        job=jobs.get(job_id,access)
        return Payments(jobs).checkout(job_id,access) if job['snapshot']['payment_mode']=='sandbox' else jobs.checkout(job_id,access)
    except KeyError:
        raise HTTPException(404, 'Job not found') from None


@router.post('/{job_id}/capture')
def capture(job_id: str, authorization: str = Header(default='')):
    try:
        return Payments(jobs).capture(job_id,token(authorization))
    except KeyError:
        raise HTTPException(404,'Job not found') from None


@router.post('/{job_id}/refund')
def refund(job_id: str, authorization: str = Header(default=''), x_operator_token: str = Header(default='')):
    require_operator(x_operator_token)
    try:
        return Payments(jobs).refund(job_id,token(authorization))
    except KeyError:
        raise HTTPException(404,'Job not found') from None


@router.post('/{job_id}/payment-status')
def payment_status(job_id: str, authorization: str = Header(default='')):
    try:
        return Payments(jobs).reconcile(job_id,token(authorization))
    except KeyError:
        raise HTTPException(404,'Job not found') from None


@router.get('/{job_id}/products.csv')
def download(job_id: str, authorization: str = Header(default='')):
    try:
        result = jobs.get(job_id, token(authorization))
    except KeyError:
        raise HTTPException(404, 'Job not found') from None
    if result['status'] != 'completed' or result['export'] is None:
        raise HTTPException(409, 'Export is not ready')
    return Response(result['export'], media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="products.csv"'})


@router.get('/{job_id}/report.json')
def report(job_id: str, authorization: str = Header(default='')):
    result = read(job_id, authorization)
    import json
    return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type='application/json',
                    headers={'Content-Disposition': 'attachment; filename="catalog-report.json"'})


def start_worker():
    stop = threading.Event()
    if engine.dialect.name != 'sqlite':
        return stop, None
    jobs.migrate()
    Payments(jobs).migrate()
    jobs.recover()
    def work():
        while not stop.is_set():
            try:
                if jobs.tick():
                    continue
            except Exception:
                # Restart recovery retains reserved attempts and checkpoints.
                jobs.recover()
            stop.wait(0.5)
    thread = threading.Thread(target=work, daemon=True, name='catalogue-worker')
    thread.start()
    return stop, thread
