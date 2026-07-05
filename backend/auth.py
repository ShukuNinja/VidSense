import os
import time

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
