# backend/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

_ssl_args = (
    {} if "localhost" in (DATABASE_URL or "")
    else {
        "sslmode": "require",
        "keepalives": 1,
        "keepalives_idle": 60,      # send first keepalive after 60s idle
        "keepalives_interval": 10,  # retry every 10s
        "keepalives_count": 5,      # drop after 5 failed retries
    }
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=_ssl_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()