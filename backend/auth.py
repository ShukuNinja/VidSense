import datetime
import json
import os
import secrets
import string
import time
import urllib.error
import urllib.request

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User

# Change this in production (set VIDSENSE_SECRET). Tokens are invalidated when
# the secret changes. Default is a >=32-byte dev placeholder — NOT for prod.
SECRET = os.getenv("VIDSENSE_SECRET", "dev-insecure-secret-change-me-in-production-0000")
ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days
# Read-only module defaults — note: send_otp_email reads the live environment
# at call time so updates to env (or .env reloading) are picked up without
# requiring a module re-import in dev.
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "no-reply@vidsense.local")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "VidSense")
OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "10"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_token(user_id: int) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def generate_otp_code(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _normalize_datetime(value: datetime.datetime | None) -> datetime.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def create_or_refresh_otp(user: User) -> str:
    otp_code = generate_otp_code()
    user.otp_code = otp_code
    user.otp_expires_at = _utc_now() + datetime.timedelta(minutes=OTP_TTL_MINUTES)
    return otp_code

import requests

def send_otp_email(to_email: str, otp_code: str) -> bool:
    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "").strip()
    sender_name = os.getenv("BREVO_SENDER_NAME", "VidSense").strip()

    print("=" * 60)
    print("API KEY:", repr(api_key))
    print("SENDER :", repr(sender_email))    
    print("=" * 60)

    if not api_key or not sender_email:
        print("Brevo credentials are missing.")
        return True

    payload = {
    "sender": {
        "name": sender_name,
        "email": sender_email,
    },
    "to": [
        {
            "email": to_email,
        }
    ],
    "subject": "Verify your VidSense account",
    "htmlContent": (
        f"<p>Your VidSense verification code is "
        f"<strong>{otp_code}</strong>.</p>"
        f"<p>This code expires in {OTP_TTL_MINUTES} minutes.</p>"
    ),
    "textContent": (
        f"Your VidSense verification code is {otp_code}. "
        f"This code expires in {OTP_TTL_MINUTES} minutes."
    ),
}


    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    print("=" * 60)
    print("BREVO DEBUG")
    print("API Key Prefix:", api_key[:15] + "...")
    print("Sender:", sender_email)
    print("Recipient:", to_email)
    print("=" * 60)

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers=headers,
        json=payload,
        timeout=10,
    )

    print("Status:", response.status_code)
    print("Body:", response.text)

    response.raise_for_status()

    return True

def verify_otp(user: User, otp_code: str) -> bool:
    if not user.otp_code or not user.otp_expires_at:
        return False
    expires_at = _normalize_datetime(user.otp_expires_at)
    if expires_at is None or expires_at < _utc_now():
        return False
    if user.otp_code != otp_code:
        return False
    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    return True


def get_current_user(
    authorization: str = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not authenticated.")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired session.")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(401, "Account no longer exists.")
    return user
