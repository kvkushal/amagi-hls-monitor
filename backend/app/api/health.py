from fastapi import APIRouter
from datetime import datetime
from app.config import settings
from app.models import HealthStatus
from app.services.stream_monitor import stream_monitor

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """System health check endpoint."""
    workers_active = len(stream_monitor.monitoring_tasks) > 0
    
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
        workers_active=workers_active,
        log_rotation_active=True,
        storage_available=True,
        version=settings.APP_VERSION
    )
