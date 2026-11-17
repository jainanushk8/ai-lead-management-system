"""
app/main.py
FastAPI application entry point.

HOW IT WORKS:
- Uses the lifespan context manager (FastAPI 0.100+ pattern) to run
  database initialization on startup and cleanup on shutdown.
- Mounts both routers: /api/leads (lead CRUD) and /api/agent (Hermes agent).
- Adds CORS middleware configured to allow all origins during development.
  In production, this would be locked to specific frontend domains.
- Provides a health check endpoint at GET / that returns the application
  name and status.

STARTUP SEQUENCE:
1. Python interpreter loads this module.
2. FastAPI creates the app with the lifespan context manager.
3. On first request (or uvicorn startup), the lifespan enters:
   a. init_db() creates all SQLite tables and indexes.
   b. A log message confirms startup.
4. The app is now ready to serve requests.
5. On shutdown, the lifespan exits and logs the shutdown event.

INTERVIEW NOTES:
- The lifespan pattern replaces the deprecated @app.on_event("startup")
  and @app.on_event("shutdown") decorators.
- CORS is wide open (allow_origins=["*"]) because n8n running locally
  needs to call the API, and the browser-based n8n UI may send
  preflight OPTIONS requests. For production, restrict this.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import leads, agent

# Configure logging for the application.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Code before 'yield' runs on startup; code after 'yield' runs on shutdown.
    """
    # --- Startup ---
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully.")
    logger.info(
        "%s is starting on %s:%s",
        settings.APP_NAME,
        settings.HOST,
        settings.PORT,
    )

    yield  # Application is running and serving requests here.

    # --- Shutdown ---
    logger.info("Application shutting down.")


# Create the FastAPI application instance.
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "AI-Powered Lead Management & Automation System. "
        "Receives leads, classifies them using a local LLM (Hermes 3 on Ollama), "
        "and processes them through an AI agent with tool-calling capabilities."
    ),
    lifespan=lifespan,
)

# Add CORS middleware for n8n and development tools.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers.
app.include_router(leads.router)
app.include_router(agent.router)


@app.get("/", tags=["Health"])
async def health_check():
    """
    Root endpoint serving as a health check.
    Returns the application name, version, and current status.
    """
    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.APP_ENV,
    }
