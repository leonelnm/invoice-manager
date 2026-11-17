import argparse

from sqlalchemy import select

from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import InvoiceSequence, SourceSystem, User
from .security import hash_password


def init_db() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for index, name in enumerate(get_settings().configured_sources, start=1):
            code = f"system-{index}"
            if not db.scalar(select(SourceSystem).where(SourceSystem.code == code)):
                db.add(SourceSystem(code=code, name=name))
        if not db.scalar(select(InvoiceSequence).where(InvoiceSequence.series == "FAC", InvoiceSequence.fiscal_year.is_(None))):
            db.add(InvoiceSequence(series="FAC", fiscal_year=None, last_number=0))
        db.commit()


def create_admin(username: str, display_name: str, password: str) -> None:
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres")
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username.lower())):
            raise SystemExit("El usuario ya existe")
        db.add(User(username=username.lower(), display_name=display_name, password_hash=hash_password(password), is_admin=True))
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    admin = sub.add_parser("create-admin")
    admin.add_argument("username")
    admin.add_argument("display_name")
    admin.add_argument("password")
    args = parser.parse_args()
    if args.command == "init-db": init_db()
    else: create_admin(args.username, args.display_name, args.password)
