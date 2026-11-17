import hashlib
import secrets

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def fingerprint(source_code: str, report_id: str) -> str:
    return hashlib.sha256(f"{source_code}\x00{report_id}".encode()).hexdigest()


def csrf_token() -> str:
    return secrets.token_urlsafe(32)
