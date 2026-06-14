import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.session_cleanup import sweep_stale_sessions
from core.config import SESSION_SWEEP_INTERVAL_MINUTES, SESSION_TTL_HOURS

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def _session_sweep_loop() -> None:
    """Periodically delete abandoned sessions (files + vectors + BM25)."""
    interval_seconds = max(SESSION_SWEEP_INTERVAL_MINUTES, 1) * 60
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await asyncio.to_thread(sweep_stale_sessions, SESSION_TTL_HOURS)
        except Exception:
            logger.exception("Session sweep failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    sweep_task = asyncio.create_task(_session_sweep_loop())
    try:
        yield
    finally:
        sweep_task.cancel()


app = FastAPI(lifespan=lifespan)

default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
configured_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(default_cors_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
