"""SQLAlchemy ORM models — used only by Alembic for migration generation.

Runtime queries use raw asyncpg for performance.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Float,
    Integer,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    dietary_preference = Column(String(10), nullable=False)
    timezone = Column(String(50), nullable=False, default="Asia/Kolkata")
    swiggy_phone = Column(String(15))
    swiggy_session_token = Column(Text)
    swiggy_token_expires_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    food_name = Column(String(255), nullable=False)
    calories = Column(Integer, nullable=False)
    is_healthy = Column(Boolean, nullable=False)
    meal_type = Column(String(10), nullable=False)
    input_type = Column(String(5), nullable=False)
    raw_input = Column(Text)
    logged_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)


class SuggestionLog(Base):
    __tablename__ = "suggestions_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    suggestion_text = Column(Text, nullable=False)
    preference_healthy = Column(Boolean)
    preference_cook = Column(Boolean)
    source = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    week_start = Column(Date, nullable=False)
    report_text = Column(Text, nullable=False)
    total_calories = Column(Integer)
    healthy_pct = Column(Numeric(5, 2))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_weekly_report"),)
