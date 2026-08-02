from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import AuthRequest, OTPResendRequest, OTPVerifyRequest
from backend.auth import (
    create_or_refresh_otp,
    create_token,
    get_current_user,
    hash_password,
    send_otp_email,
    verify_password,
    verify_otp,
)
from backend.ratelimit import auth_rate_limit

router = APIRouter()


def _user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "is_verified": user.is_verified}


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

    existing = db.query(User).filter(User.email == email).first()
    if existing and existing.is_verified:
        raise HTTPException(409, "An account with that email already exists.")

    if existing is None:
        user = User(email=email, password_hash=hash_password(body.password), is_verified=False)
        db.add(user)
        db.flush()
    else:
        user = existing
        user.password_hash = hash_password(body.password)
        user.is_verified = False
        db.flush()

    otp_code = create_or_refresh_otp(user)
    try:
        send_otp_email(email, otp_code)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc

    db.commit()
    db.refresh(user)
    return {
        "message": "A verification code has been sent to your email.",
        "email": email,
        "requires_verification": True,
        "user": _user_out(user),
    }


@router.post("/auth/verify-otp")
def verify_account(
    body: OTPVerifyRequest,
    db: Session = Depends(get_db),
):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(404, "Account not found.")
    if user.is_verified:
        return {
            "message": "Account already verified.",
            **_auth_response(user),
        }

    if not verify_otp(user, body.otp_code):
        raise HTTPException(400, "Invalid or expired verification code.")

    db.commit()
    return {
        "message": "Account verified successfully.",
        **_auth_response(user),
    }


@router.post("/auth/resend-otp")
def resend_otp(
    body: OTPResendRequest,
    db: Session = Depends(get_db),
    _: None = Depends(auth_rate_limit),
):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(404, "Account not found.")
    if user.is_verified:
        raise HTTPException(400, "Account already verified.")

    otp_code = create_or_refresh_otp(user)
    try:
        send_otp_email(email, otp_code)
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc

    db.commit()
    return {
        "message": "A new verification code has been sent to your email.",
        "email": email,
        "requires_verification": True,
    }


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
    if not user.is_verified:
        raise HTTPException(403, "Please verify your email address before logging in.")
    return _auth_response(user)


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
