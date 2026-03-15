"""Initial schema: users, food_logs (partitioned), suggestions_log, weekly_reports

Revision ID: 0001
Revises:
Create Date: 2026-03-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

    # ── users ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id             BIGINT PRIMARY KEY,
            name                    VARCHAR(255) NOT NULL,
            city                    VARCHAR(100) NOT NULL,
            pincode                 VARCHAR(10)  NOT NULL,
            dietary_preference      VARCHAR(10)  NOT NULL
                CHECK (dietary_preference IN ('veg','nonveg','vegan')),
            timezone                VARCHAR(50)  NOT NULL DEFAULT 'Asia/Kolkata',
            swiggy_phone            VARCHAR(15),
            swiggy_session_token    TEXT,
            swiggy_token_expires_at TIMESTAMPTZ,
            created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        );
    """)

    # ── food_logs (partitioned by month on logged_at) ─────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id          BIGSERIAL,
            user_id     BIGINT       NOT NULL REFERENCES users(telegram_id),
            food_name   VARCHAR(255) NOT NULL,
            calories    INTEGER      NOT NULL CHECK (calories >= 0),
            is_healthy  BOOLEAN      NOT NULL,
            meal_type   VARCHAR(10)  NOT NULL
                CHECK (meal_type IN ('breakfast','lunch','snacks','dinner')),
            input_type  VARCHAR(5)   NOT NULL
                CHECK (input_type IN ('text','photo')),
            raw_input   TEXT,
            logged_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, logged_at)
        ) PARTITION BY RANGE (logged_at);
    """)

    # Create monthly partitions for 2025–2027
    months = [
        ("2025_01", "2025-01-01", "2025-02-01"),
        ("2025_02", "2025-02-01", "2025-03-01"),
        ("2025_03", "2025-03-01", "2025-04-01"),
        ("2025_04", "2025-04-01", "2025-05-01"),
        ("2025_05", "2025-05-01", "2025-06-01"),
        ("2025_06", "2025-06-01", "2025-07-01"),
        ("2025_07", "2025-07-01", "2025-08-01"),
        ("2025_08", "2025-08-01", "2025-09-01"),
        ("2025_09", "2025-09-01", "2025-10-01"),
        ("2025_10", "2025-10-01", "2025-11-01"),
        ("2025_11", "2025-11-01", "2025-12-01"),
        ("2025_12", "2025-12-01", "2026-01-01"),
        ("2026_01", "2026-01-01", "2026-02-01"),
        ("2026_02", "2026-02-01", "2026-03-01"),
        ("2026_03", "2026-03-01", "2026-04-01"),
        ("2026_04", "2026-04-01", "2026-05-01"),
        ("2026_05", "2026-05-01", "2026-06-01"),
        ("2026_06", "2026-06-01", "2026-07-01"),
        ("2026_07", "2026-07-01", "2026-08-01"),
        ("2026_08", "2026-08-01", "2026-09-01"),
        ("2026_09", "2026-09-01", "2026-10-01"),
        ("2026_10", "2026-10-01", "2026-11-01"),
        ("2026_11", "2026-11-01", "2026-12-01"),
        ("2026_12", "2026-12-01", "2027-01-01"),
        ("2027_01", "2027-01-01", "2027-02-01"),
        ("2027_02", "2027-02-01", "2027-03-01"),
        ("2027_03", "2027-03-01", "2027-04-01"),
        ("2027_04", "2027-04-01", "2027-05-01"),
        ("2027_05", "2027-05-01", "2027-06-01"),
        ("2027_06", "2027-06-01", "2027-07-01"),
        ("2027_07", "2027-07-01", "2027-08-01"),
        ("2027_08", "2027-08-01", "2027-09-01"),
        ("2027_09", "2027-09-01", "2027-10-01"),
        ("2027_10", "2027-10-01", "2027-11-01"),
        ("2027_11", "2027-11-01", "2027-12-01"),
        ("2027_12", "2027-12-01", "2028-01-01"),
    ]
    for suffix, start, end in months:
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS food_logs_{suffix}
            PARTITION OF food_logs
            FOR VALUES FROM ('{start}') TO ('{end}');
        """)

    # Indexes on food_logs
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_logs_user_logged
        ON food_logs (user_id, logged_at DESC);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_food_logs_user_healthy
        ON food_logs (user_id, is_healthy);
    """)

    # ── suggestions_log ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS suggestions_log (
            id                  BIGSERIAL PRIMARY KEY,
            user_id             BIGINT      NOT NULL REFERENCES users(telegram_id),
            suggestion_text     TEXT        NOT NULL,
            preference_healthy  BOOLEAN,
            preference_cook     BOOLEAN,
            source              VARCHAR(20) NOT NULL
                CHECK (source IN ('gpt','history','swiggy','zomato')),
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_suggestions_log_user
        ON suggestions_log (user_id, created_at DESC);
    """)

    # ── weekly_reports ────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id             BIGSERIAL PRIMARY KEY,
            user_id        BIGINT    NOT NULL REFERENCES users(telegram_id),
            week_start     DATE      NOT NULL,
            report_text    TEXT      NOT NULL,
            total_calories INTEGER,
            healthy_pct    NUMERIC(5,2),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_weekly_report UNIQUE (user_id, week_start)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS weekly_reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS suggestions_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS food_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
