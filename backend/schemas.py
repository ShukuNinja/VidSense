from typing import Optional

from pydantic import BaseModel


class AuthRequest(BaseModel):
    email: str
    password: str


class OTPVerifyRequest(BaseModel):
    email: str
    otp_code: str


class OTPResendRequest(BaseModel):
    email: str


class ChatCreate(BaseModel):
    url: str
    start_time: str
    end_time: str
    title: Optional[str] = None


class ChatRename(BaseModel):
    title: str


class MessageCreate(BaseModel):
    content: str
