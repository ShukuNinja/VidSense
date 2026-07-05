from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import AuthRequest
from backend.auth import hash_password, verify_password, create_token, get_current_user
from backend.ratelimit import auth_rate_limit

router = APIRouter()


def _user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email}


def _auth_response(user: User) -> dict:
    return {
        "access_token": create_token(user.id),
        "token_type": "bearer",
        "user": _user_out(user),
    }


@router.post("/auth/register")
def register(
    body: AuthRequest,
    db: Session = Depends(get_db),
    _: None = Depends(auth_rate_limit),
):
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Enter a valid email address.")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with that email already exists.")

    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.post("/auth/login")
def login(
    body: AuthRequest,
    db: Session = Depends(get_db),
    _: None = Depends(auth_rate_limit),
):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password.")
    return _auth_response(user)


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
