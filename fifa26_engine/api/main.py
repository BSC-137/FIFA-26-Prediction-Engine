"""FastAPI application entry point (placeholder)."""

from fastapi import FastAPI

from fifa26_engine.utils.logging import configure_logging

configure_logging()

app = FastAPI(
    title="FIFA 26 Prediction Engine",
    description="World Cup 2026 match prediction API",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe for deployments."""
    return {"status": "ok"}
