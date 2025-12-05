from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import asyncio
from pathlib import Path

from app.config import settings
from app.api import streams, websocket, health
from app.api import export as export_api
from app.api import webhooks as webhooks_api
from app.services.stream_monitor import stream_monitor
from app.services.logger_service import log_service
from app.services.webhook_service import webhook_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Background task for log rotation
async def log_rotation_worker():
    """Background worker for log rotation."""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            await log_service.rotate_logs()
        except Exception as e:
            logger.error(f"Log rotation error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Start stream monitor
    await stream_monitor.start()
    
    # Start webhook service
    await webhook_service.start()
    
    # Load persisted streams
    from app.api.streams import load_persisted_streams
    await load_persisted_streams()
    
    # Start log rotation worker
    rotation_task = asyncio.create_task(log_rotation_worker())
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Stop stream monitor
    await stream_monitor.stop()
    
    # Stop webhook service
    await webhook_service.stop()
    
    # Cancel rotation task
    rotation_task.cancel()
    
    logger.info("Application shut down")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-grade OTT Stream Monitoring System",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for serving sprites and thumbnails)
data_dir = Path(settings.DATA_DIR)
data_dir.mkdir(parents=True, exist_ok=True)

app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

# Include routers
app.include_router(streams.router)
app.include_router(websocket.router)
app.include_router(health.router)
app.include_router(export_api.router)
app.include_router(webhooks_api.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
