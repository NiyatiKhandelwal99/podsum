"""Main FastAPI application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import health, generate, youtube, search

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(generate.router)
app.include_router(youtube.router)
app.include_router(search.router)


@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(f"Starting {settings.app_name} in {settings.env} environment")
    # Verify API key is loaded
    if settings.tadata_api_key:
        logger.info("Tadata API key loaded successfully")
    else:
        logger.error("WARNING: Tadata API key is empty! Check your .env file.")


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
