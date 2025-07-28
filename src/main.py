"""Main FastAPI application for the Agricultural AI Agent system."""

import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager

from src.config import settings
from src.database import init_database
from src.api.webhook import webhook_router


# Initialize LangSmith tracing if enabled
def init_langsmith():
    """Initialize LangSmith tracing configuration."""
    from src.utils.langsmith_config import init_langsmith_environment
    init_langsmith_environment()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize LangSmith
init_langsmith()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Agricultural AI Agent system...")
    await init_database()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agricultural AI Agent system...")


# Create FastAPI application
app = FastAPI(
    title="Agricultural AI Agent",
    description="LangGraph-based multi-agent system for agricultural management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Agricultural AI Agent is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": "development" if settings.debug else "production"
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )