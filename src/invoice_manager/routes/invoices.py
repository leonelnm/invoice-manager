from datetime import date, datetime, time
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, func, select

from ..config import get_settings
from ..models import IdempotencyRequest, Invoice, InvoiceSequence, SourceSystem, User
from ..security import fingerprint
from ..templates import templates
from .common import CurrentUser, Db, ensure_csrf, session_context

router = APIRouter()


def sources(db):
    return db.scalars(select(SourceSystem).where(SourceSystem.is_active.is_(True)).order_by(SourceSystem.name)).all()


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: CurrentUser, db: Db):
    return templates.TemplateResponse(request, "home.html", session_context(request) | {"sources": sources(db), "result": None, "already_exists": False, "error": None, "idempotency_key": str(uuid4())})


@router.post("/invoices", response_class=HTMLResponse)
def create_invoice(request: Request, user: CurrentUser, db: Db, source_code: str = Form(), report_id: str = Form(), idempotency_key: str = Form(), csrf: str = Form()):
    ensure_csrf(request, csrf)
    report_id = report_id.strip()
    if not report_id or len(report_id) > 150:
        return templates.TemplateResponse(request, "home.html", session_context(request) | {"sources": sources(db), "error": "Introduce un identificador válido", "result": None, "already_exists": False, "idempotency_key": str(uuid4())}, status_code=422)
    try:
        UUID(idempotency_key)
    except ValueError:
        raise HTTPException(422, "Clave de idempotencia inválida")
    source = db.scalar(select(SourceSystem).where(SourceSystem.code == source_code, SourceSystem.is_active.is_(True)))
    if not source:
        raise HTTPException(422, "Sistema de origen inválido")
    fp = fingerprint(source.code, report_id)
    db.rollback()
    already_exists = False
    with db.begin():
        prior_request = db.scalar(select(IdempotencyRequest).where(IdempotencyRequest.idempotency_key == idempotency_key))
        if prior_request:
            if prior_request.request_fingerprint != fp:
                raise HTTPException(409, "La clave de idempotencia ya se usó para otra operación")
            invoice = db.get(Invoice, prior_request.invoice_id)
        else:
            invoice = db.scalar(select(Invoice).where(Invoice.source_system_id == source.id, Invoice.report_id == report_id))
            already_exists = invoice is not None
            if not invoice:
                sequence = db.scalar(select(InvoiceSequence).where(InvoiceSequence.series == "FAC", InvoiceSequence.fiscal_year.is_(None)).with_for_update())
                if not sequence:
                    sequence = InvoiceSequence(series="FAC", fiscal_year=None, last_number=0)
                    db.add(sequence)
                    db.flush()
                sequence.last_number += 1
                invoice = Invoice(sequence_id=sequence.id, sequence_number=sequence.last_number, invoice_number=f"FAC-{sequence.last_number:06d}", source_system_id=source.id, report_id=report_id, created_by=user.id)
                db.add(invoice)
                db.flush()
            db.add(IdempotencyRequest(idempotency_key=idempotency_key, request_fingerprint=fp, invoice_id=invoice.id, created_by=user.id))
    return templates.TemplateResponse(request, "home.html", session_context(request) | {"sources": sources(db), "result": invoice, "already_exists": already_exists, "error": None, "idempotency_key": str(uuid4())})


@router.get("/invoices", response_class=HTMLResponse)
def history(request: Request, user: CurrentUser, db: Db, invoice_number: str | None = Query(None), report_id: str | None = Query(None), source_code: str | None = Query(None), worker_id: int | None = Query(None), date_from: date | None = Query(None), date_to: date | None = Query(None), page: int = Query(1, ge=1)):
    settings = get_settings()
    filters = []
    if invoice_number: filters.append(Invoice.invoice_number.contains(invoice_number.strip()))
    if report_id: filters.append(Invoice.report_id.contains(report_id.strip()))
    if source_code: filters.append(SourceSystem.code == source_code)
    if worker_id: filters.append(Invoice.created_by == worker_id)
    if date_from: filters.append(Invoice.created_at >= datetime.combine(date_from, time.min))
    if date_to: filters.append(Invoice.created_at < datetime.combine(date_to, time.max))
    base = select(Invoice).join(SourceSystem).join(User).where(*filters).order_by(desc(Invoice.created_at), desc(Invoice.id))
    total = db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    pages = max(1, (total + settings.page_size - 1) // settings.page_size)
    page = min(page, pages)
    rows = db.scalars(base.offset((page - 1) * settings.page_size).limit(settings.page_size)).all()
    workers = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.display_name)).all()
    return templates.TemplateResponse(request, "history.html", session_context(request) | {"rows": rows, "sources": sources(db), "workers": workers, "page": page, "pages": pages, "total": total, "filters": request.query_params})


@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
def detail(invoice_id: int, request: Request, user: CurrentUser, db: Db):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Factura no encontrada")
    return templates.TemplateResponse(request, "detail.html", session_context(request) | {"invoice": invoice})
