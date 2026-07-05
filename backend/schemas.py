from typing import Optional

from pydantic import BaseModel


class ChatCreate(BaseModel):
    url: str
    start_time: str
    end_time: str
    title: Optional[str] = None


class ChatRename(BaseModel):
    title: str


class MessageCreate(BaseModel):
    content: str
