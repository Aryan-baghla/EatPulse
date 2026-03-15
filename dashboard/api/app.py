from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from core.settings import settings
from database.connection import close_pool, create_pool
from integrations.openai_client import init_client
from scheduler.weekly_report_job import register_jobs

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting EatPulse (env=%s, mode=%s)", settings.environment, settings.bot_mode)

    # Database pool
    db_pool = await create_pool()
    app.state.db = db_pool

    # OpenAI client
    openai_client = init_client()
    app.state.openai = openai_client

    # Telegram bot application
    from bot.main import create_application
    tg_app = await create_application(db_pool, openai_client)
    await tg_app.initialize()
    if settings.bot_mode == "webhook":
        await tg_app.start()
    app.state.tg_app = tg_app

    # Scheduler
    scheduler = AsyncIOScheduler()
    register_jobs(scheduler, tg_app.bot, db_pool)
    scheduler.start()
    app.state.scheduler = scheduler

    # Register webhook with Telegram if in production
    if settings.bot_mode == "webhook" and settings.is_production:
        webhook_url = f"{settings.webhook_base_url}/bot/webhook"
        try:
            await tg_app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query"],
            )
            logger.info("Webhook set: %s", webhook_url)
        except Exception as e:
            logger.error("Failed to set webhook: %s", e)

    logger.info("EatPulse started successfully")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down EatPulse...")
    scheduler.shutdown(wait=False)
    if settings.bot_mode == "webhook":
        await tg_app.stop()
    await tg_app.shutdown()
    await close_pool()
    logger.info("EatPulse stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="EatPulse Dashboard API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://dashboard.eatpulse.in"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check (no auth required — used by ALB and CodeDeploy)
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    # Import and include routers
    from dashboard.api.routes.webhook import router as webhook_router
    from dashboard.api.routes.users import router as users_router
    from dashboard.api.routes.food_logs import router as food_logs_router
    from dashboard.api.routes.calories import router as calories_router

    app.include_router(webhook_router)
    app.include_router(users_router)
    app.include_router(food_logs_router)
    app.include_router(calories_router)

    # Serve frontend static files last (catch-all)
    try:
        app.mount(
            "/",
            StaticFiles(directory="dashboard/frontend", html=True),
            name="frontend",
        )
    except Exception as e:
        logger.warning("Could not mount frontend static files: %s", e)

    return app
