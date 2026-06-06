from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.routes.summarize import router as summarize_router


ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luminote")

CORS_ORIGINS = ["*"]

app = FastAPI(
    title="Luminote - YouTube AI Summarizer",
    description="A production-ready YouTube transcript summarizer using free tools.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(summarize_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "app": "Luminote",
        "status": "running",
    }


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    message = "Invalid request body."
    for error in exc.errors():
        if "url" in error.get("loc", ()):
            message = "Invalid YouTube URL. Paste a youtube.com or youtu.be video URL."
            break

    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": message,
                "errors": exc.errors(),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        payload = {"detail": detail}
    else:
        payload = {"detail": {"message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled backend error")
    return JSONResponse(
        status_code=500,
        content={"detail": {"message": "Internal server error. Check the backend terminal logs."}},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health")
async def api_health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event() -> None:
    """Validate configuration and initialize services on startup."""
    logger.info("Starting Luminote server...")
    logger.info("CORS Origins: %s", CORS_ORIGINS)
    for warning in settings.validate():
        logger.warning("Configuration warning: %s", warning)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
