from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from ..db import SessionLocal
from ..models import User
from ..security import csrf_token, verify_password
from ..templates import templates
from .common import ensure_csrf, session_context

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", session_context(request) | {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(), password: str = Form(), csrf: str = Form()):
    ensure_csrf(request, csrf)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username.strip().lower()))
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(request, "login.html", session_context(request) | {"error": "Usuario o contraseña incorrectos"}, status_code=401)
        request.session.clear()
        request.session.update({"user_id": user.id, "user_name": user.display_name, "is_admin": user.is_admin, "csrf_token": csrf_token()})
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request, csrf: str = Form()):
    ensure_csrf(request, csrf)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
