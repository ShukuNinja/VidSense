import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "vidsense.db")

# check_same_thread=False: ingestion runs in a worker thread and SSE generators
# run in Starlette's threadpool, each with its own Session.
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def ensure_user_otp_columns():
    with engine.begin() as conn:
        table_info = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        existing_columns = {row[1] for row in table_info}

        if "is_verified" not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT 0"))
        if "otp_code" not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN otp_code VARCHAR"))
        if "otp_expires_at" not in existing_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN otp_expires_at DATETIME"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
