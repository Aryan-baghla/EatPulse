from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _load_secrets_manager() -> None:
    """Fetch secrets from AWS Secrets Manager and inject into env vars.

    Only runs when AWS_SECRETS_MANAGER_SECRET_ID is set (i.e. on EC2).
    Populates env vars so Pydantic Settings can read them normally.
    """
    secret_id = os.getenv("AWS_SECRETS_MANAGER_SECRET_ID")
    if not secret_id:
        return

    region = os.getenv("AWS_REGION", "ap-south-1")
    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_id)
        secrets = json.loads(response["SecretString"])
        for key, value in secrets.items():
            os.environ.setdefault(key, str(value))
        logger.info("Loaded %d secrets from Secrets Manager (%s)", len(secrets), secret_id)
    except ClientError as e:
        logger.error("Failed to load secrets from Secrets Manager: %s", e)


# Load secrets before Settings is instantiated
_load_secrets_manager()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Database
    database_url: str = "postgresql://eatpulse:changeme@localhost:5432/eatpulse"
    aurora_direct_url: str = ""  # for Alembic migrations

    # Auth
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Swiggy
    swiggy_mcp_base_url: str = "https://mcp.swiggy.com/food"
    swiggy_mcp_api_key: str = ""

    # App
    environment: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    webhook_base_url: str = "https://dashboard.eatpulse.in"
    bot_mode: Literal["polling", "webhook"] = "polling"

    # AWS
    aws_region: str = "ap-south-1"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def migration_db_url(self) -> str:
        """Returns direct Aurora URL for migrations, falls back to DATABASE_URL."""
        return self.aurora_direct_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
