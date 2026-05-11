from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.routes.summarize import router as summarize_router


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luminote")

app = FastAPI(
    title="Luminote - YouTube AI Summarizer",
    description="A production-ready YouTube transcript summarizer using free tools.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include routers
app.include_router(summarize_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": "Invalid request body.",
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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Luminote server...")
    # Services will initialize lazily when first used


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", settings.port))
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=port,
        reload=settings.debug,
        log_level="info",
    )
