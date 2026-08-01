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


def send_otp_email(to_email: str, otp_code: str) -> bool:
    if not BREVO_API_KEY or BREVO_SENDER_EMAIL == "no-reply@vidsense.local":
        print(
            "BREVO_API_KEY or BREVO_SENDER_EMAIL is not configured; skipping OTP email delivery."
        )
        return True

    payload = {
        "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Verify your VidSense account",
        "htmlContent": (
            f"<p>Your VidSense verification code is <strong>{otp_code}</strong>.</p>"
            f"<p>This code expires in {OTP_TTL_MINUTES} minutes.</p>"
        ),
        "textContent": (
            f"Your VidSense verification code is {otp_code}. "
            f"This code expires in {OTP_TTL_MINUTES} minutes."
        ),
    }

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "api-key": BREVO_API_KEY,
        },
        method="POST",
    )

    # Debug prints for development diagnosis. These avoid printing secrets but
    # make it straightforward to see whether the HTTP call was attempted and
    # what the outcome was.
    print("Brevo: sending email request to API endpoint...")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            try:
                print(f"Brevo API response status: {response.status}")
            except Exception:
                pass
            return response.status < 400
    except urllib.error.URLError as exc:
        # Print the error message to server logs to help diagnose account/sender problems
        try:
            print(f"Brevo API error: {exc}")
        except Exception:
            pass
        raise RuntimeError(f"Brevo email delivery failed: {exc}") from exc


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
