from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from ..models import User
from ..security import hash_password
from ..templates import templates
from .common import AdminUser, Db, ensure_csrf, session_context

router = APIRouter(prefix="/admin")


@router.get("/users", response_class=HTMLResponse)
def users(request: Request, user: AdminUser, db: Db):
    return templates.TemplateResponse(request, "users.html", session_context(request) | {"users": db.scalars(select(User).order_by(User.username)).all(), "error": None, "user_id": user.id})


@router.post("/users")
def create_user(request: Request, user: AdminUser, db: Db, username: str = Form(), display_name: str = Form(), password: str = Form(), is_admin: bool = Form(False), csrf: str = Form()):
    ensure_csrf(request, csrf)
    username = username.strip().lower()
    if len(password) < 12 or not username or not display_name.strip():
        return templates.TemplateResponse(request, "users.html", session_context(request) | {"users": db.scalars(select(User).order_by(User.username)).all(), "error": "Usuario válido, nombre y contraseña de 12 caracteres son obligatorios", "user_id": user.id}, status_code=422)
    db.add(User(username=username, display_name=display_name.strip(), password_hash=hash_password(password), is_admin=is_admin))
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: int, request: Request, user: AdminUser, db: Db, csrf: str = Form()):
    ensure_csrf(request, csrf)
    target = db.get(User, user_id)
    if target and target.id != user.id:
        target.is_active = False
        db.commit()
    return RedirectResponse("/admin/users", status_code=303)
