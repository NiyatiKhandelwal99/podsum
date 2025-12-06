"""Main FastAPI application."""

import logging
from fastapi import FastAPI

from config import settings
from routers import health, generate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API for podcast summarization",
    version="0.1.0"
)

# Include routers
app.include_router(health.router)
app.include_router(generate.router)


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(f"Starting {settings.app_name} in {settings.env} environment")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

