"""InvoiceForge — веб-приложение (FastAPI).

Панель для создания счетов и коммерческих предложений, ведения клиентов,
экспорта в PDF (через печать браузера) и защиты по лицензии.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from . import __version__
from .auth import COOKIE_NAME, check_password, create_session_token, is_authenticated
from .config import settings
from .database import get_session, init_db
from .i18n import get_translator
from .licensing import LicenseInfo, machine_id, verify_license
from .models import Client, CompanySettings, Document, LineItem
from .utils import compute_totals, currency_symbol, format_money

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="InvoiceForge", version=__version__)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

STATUSES = ["draft", "sent", "paid", "overdue"]


@app.on_event("startup")
def _startup() -> None:
    init_db()


# --------------------------------------------------------------------------
#  Лицензия
# --------------------------------------------------------------------------
def load_license() -> LicenseInfo:
    """Читает сохранённый лицензионный ключ и проверяет его."""
    path = settings.license_path
    key = path.read_text(encoding="utf-8").strip() if path.exists() else None
    return verify_license(key)


def get_company(session: Session) -> CompanySettings:
    company = session.get(CompanySettings, 1)
    if company is None:
        company = CompanySettings(id=1)
        session.add(company)
        session.commit()
        session.refresh(company)
    return company


def context(request: Request, session: Session, **extra) -> dict:
    """Общий контекст для шаблонов (навигация, локализация, лицензия)."""
    company = get_company(session)
    license_info = load_license()
    base = {
        "request": request,
        "t": get_translator(company.language),
        "company": company,
        "license": license_info,
        "app_version": __version__,
        "format_money": format_money,
        "currency_symbol": currency_symbol,
        "statuses": STATUSES,
        "today": date.today(),
    }
    base.update(extra)
    return base


def require_auth(request: Request) -> RedirectResponse | None:
    if not is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    return None


# --------------------------------------------------------------------------
#  Аутентификация
# --------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, session: Session = Depends(get_session)):
    if is_authenticated(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", context(request, session, error=None))


@app.post("/login")
def login_submit(
    request: Request,
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    if not check_password(password):
        return templates.TemplateResponse(
            "login.html",
            context(request, session, error="Неверный пароль"),
            status_code=401,
        )
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        COOKIE_NAME, create_session_token(), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


# --------------------------------------------------------------------------
#  Активация лицензии
# --------------------------------------------------------------------------
@app.get("/activate", response_class=HTMLResponse)
def activate_form(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    return templates.TemplateResponse(
        "activate.html",
        context(request, session, error=None, saved=False, machine=machine_id()),
    )


@app.post("/activate", response_class=HTMLResponse)
def activate_submit(
    request: Request,
    license_key: str = Form(...),
    session: Session = Depends(get_session),
):
    if (redirect := require_auth(request)) is not None:
        return redirect
    info = verify_license(license_key.strip())
    if not info.valid:
        return templates.TemplateResponse(
            "activate.html",
            context(request, session, error=info.error or "Лицензия недействительна",
                    saved=False, machine=machine_id()),
            status_code=400,
        )
    settings.license_path.write_text(license_key.strip(), encoding="utf-8")
    return RedirectResponse("/", status_code=302)


# --------------------------------------------------------------------------
#  Дашборд
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect

    documents = session.exec(select(Document).order_by(Document.created_at.desc())).all()
    clients = session.exec(select(Client)).all()
    client_map = {c.id: c for c in clients}

    revenue = 0.0
    outstanding = 0.0
    enriched = []
    for doc in documents:
        items = session.exec(select(LineItem).where(LineItem.document_id == doc.id)).all()
        totals = compute_totals(doc, items)
        if doc.status == "paid":
            revenue += totals["total"]
        elif doc.status in ("sent", "overdue"):
            outstanding += totals["total"]
        enriched.append({"doc": doc, "total": totals["total"], "client": client_map.get(doc.client_id)})

    stats = {
        "revenue": revenue,
        "outstanding": outstanding,
        "documents": len(documents),
        "clients": len(clients),
    }
    return templates.TemplateResponse(
        "dashboard.html",
        context(request, session, stats=stats, recent=enriched[:8]),
    )


# --------------------------------------------------------------------------
#  Клиенты
# --------------------------------------------------------------------------
@app.get("/clients", response_class=HTMLResponse)
def clients_list(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    clients = session.exec(select(Client).order_by(Client.name)).all()
    return templates.TemplateResponse("clients.html", context(request, session, clients=clients))


@app.get("/clients/new", response_class=HTMLResponse)
def client_new(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    license_info = load_license()
    count = len(session.exec(select(Client)).all())
    if not license_info.is_pro and count >= settings.demo_max_clients:
        return templates.TemplateResponse(
            "clients.html",
            context(request, session, clients=session.exec(select(Client)).all(),
                    limit_error=f"Демо-версия: лимит {settings.demo_max_clients} клиентов. "
                                f"Активируйте лицензию, чтобы снять ограничение."),
        )
    return templates.TemplateResponse(
        "client_form.html", context(request, session, client=None)
    )


@app.post("/clients")
def client_create(
    request: Request,
    name: str = Form(...),
    company: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    tax_id: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    if (redirect := require_auth(request)) is not None:
        return redirect
    license_info = load_license()
    count = len(session.exec(select(Client)).all())
    if not license_info.is_pro and count >= settings.demo_max_clients:
        return RedirectResponse("/clients/new", status_code=302)
    client = Client(name=name, company=company, email=email, phone=phone,
                    address=address, tax_id=tax_id, notes=notes)
    session.add(client)
    session.commit()
    return RedirectResponse("/clients", status_code=302)


@app.get("/clients/{client_id}/edit", response_class=HTMLResponse)
def client_edit(client_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    client = session.get(Client, client_id)
    if client is None:
        return RedirectResponse("/clients", status_code=302)
    return templates.TemplateResponse(
        "client_form.html", context(request, session, client=client)
    )


@app.post("/clients/{client_id}")
def client_update(
    client_id: int,
    request: Request,
    name: str = Form(...),
    company: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    tax_id: str = Form(""),
    notes: str = Form(""),
    session: Session = Depends(get_session),
):
    if (redirect := require_auth(request)) is not None:
        return redirect
    client = session.get(Client, client_id)
    if client is None:
        return RedirectResponse("/clients", status_code=302)
    client.name = name
    client.company = company
    client.email = email
    client.phone = phone
    client.address = address
    client.tax_id = tax_id
    client.notes = notes
    session.add(client)
    session.commit()
    return RedirectResponse("/clients", status_code=302)


@app.post("/clients/{client_id}/delete")
def client_delete(client_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    client = session.get(Client, client_id)
    if client is not None:
        session.delete(client)
        session.commit()
    return RedirectResponse("/clients", status_code=302)


# --------------------------------------------------------------------------
#  Документы (счета и КП)
# --------------------------------------------------------------------------
def _next_number(company: CompanySettings, doc_type: str) -> str:
    if doc_type == "proposal":
        number = f"{company.proposal_prefix}{company.next_proposal_number:04d}"
        company.next_proposal_number += 1
    else:
        number = f"{company.invoice_prefix}{company.next_invoice_number:04d}"
        company.next_invoice_number += 1
    return number


def _parse_items(form, document_id: int) -> list[LineItem]:
    descriptions = form.getlist("item_description")
    quantities = form.getlist("item_quantity")
    prices = form.getlist("item_price")
    items: list[LineItem] = []
    for idx, description in enumerate(descriptions):
        description = description.strip()
        if not description:
            continue
        try:
            quantity = float(quantities[idx] or 0)
            price = float(prices[idx] or 0)
        except (ValueError, IndexError):
            quantity, price = 0.0, 0.0
        items.append(LineItem(document_id=document_id, description=description,
                              quantity=quantity, unit_price=price, position=idx))
    return items


@app.get("/documents", response_class=HTMLResponse)
def documents_list(
    request: Request,
    type: str = "invoice",
    session: Session = Depends(get_session),
):
    if (redirect := require_auth(request)) is not None:
        return redirect
    doc_type = "proposal" if type == "proposal" else "invoice"
    documents = session.exec(
        select(Document).where(Document.doc_type == doc_type).order_by(Document.created_at.desc())
    ).all()
    clients = {c.id: c for c in session.exec(select(Client)).all()}
    rows = []
    for doc in documents:
        items = session.exec(select(LineItem).where(LineItem.document_id == doc.id)).all()
        rows.append({"doc": doc, "total": compute_totals(doc, items)["total"],
                     "client": clients.get(doc.client_id)})
    return templates.TemplateResponse(
        "documents.html", context(request, session, rows=rows, doc_type=doc_type)
    )


@app.get("/documents/new", response_class=HTMLResponse)
def document_new(
    request: Request,
    type: str = "invoice",
    session: Session = Depends(get_session),
):
    if (redirect := require_auth(request)) is not None:
        return redirect
    doc_type = "proposal" if type == "proposal" else "invoice"
    clients = session.exec(select(Client).order_by(Client.name)).all()
    license_info = load_license()
    count = len(session.exec(select(Document)).all())
    limit_error = None
    if not license_info.is_pro and count >= settings.demo_max_documents:
        limit_error = (f"Демо-версия: лимит {settings.demo_max_documents} документов. "
                       f"Активируйте лицензию, чтобы снять ограничение.")
    return templates.TemplateResponse(
        "document_form.html",
        context(request, session, document=None, items=[], clients=clients,
                doc_type=doc_type, limit_error=limit_error),
    )


@app.post("/documents")
async def document_create(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    form = await request.form()
    doc_type = "proposal" if form.get("doc_type") == "proposal" else "invoice"

    license_info = load_license()
    count = len(session.exec(select(Document)).all())
    if not license_info.is_pro and count >= settings.demo_max_documents:
        return RedirectResponse(f"/documents/new?type={doc_type}", status_code=302)

    company = get_company(session)
    document = Document(
        doc_type=doc_type,
        number=_next_number(company, doc_type),
        client_id=int(form.get("client_id")),
        issue_date=date.fromisoformat(form.get("issue_date") or date.today().isoformat()),
        due_date=date.fromisoformat(form["due_date"]) if form.get("due_date") else None,
        status=form.get("status", "draft"),
        currency=form.get("currency", company.currency),
        tax_rate=float(form.get("tax_rate") or 0),
        discount=float(form.get("discount") or 0),
        notes=form.get("notes", ""),
    )
    session.add(document)
    session.add(company)
    session.commit()
    session.refresh(document)

    for item in _parse_items(form, document.id):
        session.add(item)
    session.commit()
    return RedirectResponse(f"/documents/{document.id}", status_code=302)


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def document_view(document_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    document = session.get(Document, document_id)
    if document is None:
        return RedirectResponse("/documents", status_code=302)
    items = session.exec(
        select(LineItem).where(LineItem.document_id == document_id).order_by(LineItem.position)
    ).all()
    client = session.get(Client, document.client_id)
    totals = compute_totals(document, items)
    return templates.TemplateResponse(
        "document_view.html",
        context(request, session, document=document, items=items, client=client, totals=totals),
    )


@app.get("/documents/{document_id}/edit", response_class=HTMLResponse)
def document_edit(document_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    document = session.get(Document, document_id)
    if document is None:
        return RedirectResponse("/documents", status_code=302)
    items = session.exec(
        select(LineItem).where(LineItem.document_id == document_id).order_by(LineItem.position)
    ).all()
    clients = session.exec(select(Client).order_by(Client.name)).all()
    return templates.TemplateResponse(
        "document_form.html",
        context(request, session, document=document, items=items, clients=clients,
                doc_type=document.doc_type, limit_error=None),
    )


@app.post("/documents/{document_id}")
async def document_update(document_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    document = session.get(Document, document_id)
    if document is None:
        return RedirectResponse("/documents", status_code=302)
    form = await request.form()
    document.client_id = int(form.get("client_id"))
    document.issue_date = date.fromisoformat(form.get("issue_date") or date.today().isoformat())
    document.due_date = date.fromisoformat(form["due_date"]) if form.get("due_date") else None
    document.status = form.get("status", document.status)
    document.currency = form.get("currency", document.currency)
    document.tax_rate = float(form.get("tax_rate") or 0)
    document.discount = float(form.get("discount") or 0)
    document.notes = form.get("notes", "")
    session.add(document)

    # Пересобираем позиции: удаляем старые, добавляем новые.
    old_items = session.exec(select(LineItem).where(LineItem.document_id == document_id)).all()
    for item in old_items:
        session.delete(item)
    session.commit()
    for item in _parse_items(form, document_id):
        session.add(item)
    session.commit()
    return RedirectResponse(f"/documents/{document_id}", status_code=302)


@app.post("/documents/{document_id}/status")
def document_status(
    document_id: int,
    request: Request,
    status: str = Form(...),
    session: Session = Depends(get_session),
):
    if (redirect := require_auth(request)) is not None:
        return redirect
    document = session.get(Document, document_id)
    if document is not None and status in STATUSES:
        document.status = status
        session.add(document)
        session.commit()
    return RedirectResponse(f"/documents/{document_id}", status_code=302)


@app.post("/documents/{document_id}/delete")
def document_delete(document_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    document = session.get(Document, document_id)
    if document is not None:
        for item in session.exec(select(LineItem).where(LineItem.document_id == document_id)).all():
            session.delete(item)
        session.delete(document)
        session.commit()
        redirect_type = document.doc_type
    else:
        redirect_type = "invoice"
    return RedirectResponse(f"/documents?type={redirect_type}", status_code=302)


@app.get("/documents/{document_id}/print", response_class=HTMLResponse)
def document_print(document_id: int, request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    document = session.get(Document, document_id)
    if document is None:
        return RedirectResponse("/documents", status_code=302)
    items = session.exec(
        select(LineItem).where(LineItem.document_id == document_id).order_by(LineItem.position)
    ).all()
    client = session.get(Client, document.client_id)
    totals = compute_totals(document, items)
    license_info = load_license()
    return templates.TemplateResponse(
        "pdf_document.html",
        context(request, session, document=document, items=items, client=client,
                totals=totals, show_watermark=not license_info.is_pro),
    )


# --------------------------------------------------------------------------
#  Настройки и язык
# --------------------------------------------------------------------------
@app.get("/settings", response_class=HTMLResponse)
def settings_form(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    return templates.TemplateResponse("settings.html", context(request, session, saved=False))


@app.post("/settings")
async def settings_save(request: Request, session: Session = Depends(get_session)):
    if (redirect := require_auth(request)) is not None:
        return redirect
    form = await request.form()
    company = get_company(session)
    company.company_name = form.get("company_name", company.company_name)
    company.owner_name = form.get("owner_name", "")
    company.address = form.get("address", "")
    company.tax_id = form.get("tax_id", "")
    company.phone = form.get("phone", "")
    company.email = form.get("email", "")
    company.bank_details = form.get("bank_details", "")
    company.currency = form.get("currency", "UAH")
    company.tax_rate = float(form.get("tax_rate") or 0)
    company.invoice_prefix = form.get("invoice_prefix", "INV-")
    company.proposal_prefix = form.get("proposal_prefix", "КП-")
    company.language = form.get("language", "ru")
    company.accent_color = form.get("accent_color", "#4f7cff")
    session.add(company)
    session.commit()
    return templates.TemplateResponse("settings.html", context(request, session, saved=True))


@app.get("/lang/{code}")
def set_language(code: str, session: Session = Depends(get_session)):
    company = get_company(session)
    if code in ("ru", "uk", "en"):
        company.language = code
        session.add(company)
        session.commit()
    return RedirectResponse("/", status_code=302)


@app.get("/healthz")
def healthz(session: Session = Depends(get_session)):
    info = load_license()
    return {"ok": True, "version": __version__, "plan": info.plan, "pro": info.is_pro}


def _seen_datetime() -> str:
    return datetime.utcnow().isoformat()
