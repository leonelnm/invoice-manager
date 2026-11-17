from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import csrf_token

Db = Annotated[Session, Depends(get_db)]


def current_user(request: Request, db: Db) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    request.session["is_admin"] = user.is_admin
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def admin_user(user: CurrentUser) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return user


AdminUser = Annotated[User, Depends(admin_user)]


def ensure_csrf(request: Request, token: str) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not token or token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF inválido")


def session_context(request: Request) -> dict:
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = csrf_token()
    return {
        "request": request,
        "user": request.session.get("user_name"),
        "is_admin": request.session.get("is_admin", False),
        "csrf_token": request.session["csrf_token"],
    }
