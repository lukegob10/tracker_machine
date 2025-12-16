from contextlib import asynccontextmanager
import os
import sys
import asyncio
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Avoid touching the on-disk DB during unit tests. Tests create their own in-memory DB
    # and override `get_db`/auth dependencies.
    disable_startup = os.getenv("JIRA_LITE_DISABLE_STARTUP", "").lower() == "true"
    running_tests = "pytest" in sys.modules or bool(os.getenv("PYTEST_CURRENT_TEST"))

    # Starlette/FastAPI run sync endpoints and sync generator dependencies in a threadpool via AnyIO.
    # In some sandboxed/test environments, the AnyIO threadpool can deadlock. We patch it out for tests.
    disable_threadpool = running_tests or os.getenv("JIRA_LITE_DISABLE_THREADPOOL", "").lower() == "true"
    if disable_threadpool:
        import anyio.to_thread

        if not getattr(anyio.to_thread.run_sync, "_jira_lite_patched", False):
            original_run_sync = anyio.to_thread.run_sync

            async def run_sync_no_threadpool(func, *args, abandon_on_cancel=False, limiter=None):  # type: ignore[override]
                return func(*args)

            run_sync_no_threadpool._jira_lite_patched = True  # type: ignore[attr-defined]
            run_sync_no_threadpool._jira_lite_original = original_run_sync  # type: ignore[attr-defined]
            anyio.to_thread.run_sync = run_sync_no_threadpool  # type: ignore[assignment]

    keepalive_task = None
    if running_tests or os.getenv("JIRA_LITE_KEEPALIVE_TASK", "").lower() == "true":
        async def _keepalive() -> None:
            while True:
                await asyncio.sleep(3600)

        keepalive_task = asyncio.create_task(_keepalive())

    if not disable_startup and not running_tests:
        init_db()
    yield
    if keepalive_task:
        keepalive_task.cancel()
        with suppress(asyncio.CancelledError):
            await keepalive_task


app = FastAPI(title="Jira-lite API", version="0.1.0", lifespan=lifespan)

# API under /api to avoid collisions with static frontend
app.include_router(api_router, prefix="/api")

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Serve frontend from repo root /frontend
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
