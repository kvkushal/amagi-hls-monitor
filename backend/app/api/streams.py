from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import datetime, timedelta
from app.models import (
    StreamConfig, StreamDetails, StreamStatus, SegmentMetrics,
    VariantStream, StreamEvent, TimeRange, KPIData, StreamHealth,
    HealthScore, AudioMetrics, VideoMetrics, AlertModel
)
from app.services.stream_monitor import stream_monitor
from app.services.sprite_generator import sprite_generator
from app.services.logger_service import log_service
from app.services.alert_service import alert_service
from app.services.thumbnail_generator import thumbnail_generator
import uuid

import json
from pathlib import Path
import logging
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streams", tags=["streams"])

# In-memory storage (would be database in production)
streams_db: dict = {}
metrics_db: dict = {}  # stream_id -> list of SegmentMetrics
events_db: dict = {}  # stream_id -> list of events

STREAMS_FILE = Path(settings.DATA_DIR) / "streams.json"

def save_streams():
    """Save streams to JSON file."""
    try:
        data = [s.dict() for s in streams_db.values()]
        with open(STREAMS_FILE, 'w') as f:
            json.dump(data, f, default=str, indent=2)
    except Exception as e:
        logger.error(f"Failed to save streams: {e}")

async def load_persisted_streams():
    """Load streams from JSON file."""
    try:
        if not STREAMS_FILE.exists():
            return
            
        with open(STREAMS_FILE, 'r') as f:
            data = json.load(f)
            
        for item in data:
            config = StreamConfig(**item)
            streams_db[config.id] = config
            metrics_db[config.id] = []
            events_db[config.id] = []
            
            # Start monitoring
            await stream_monitor.add_stream(config)
            
        logger.info(f"Loaded {len(data)} streams from persistence")
    except Exception as e:
        logger.error(f"Failed to load streams: {e}")


@router.get("", response_model=List[StreamDetails])
async def list_streams():
    """Get all monitored streams."""
    result = []
    
    for stream_id, config in stream_monitor.active_streams.items():
        # Get latest metrics
        current_metrics = None
        if stream_id in stream_monitor.stream_metrics:
            current_metrics = stream_monitor.stream_metrics[stream_id]
        elif stream_id in metrics_db and metrics_db[stream_id]:
            current_metrics = metrics_db[stream_id][-1]
        
        # Get health with updated score
        health = stream_monitor.get_stream_health(stream_id)
        status = StreamStatus.OFFLINE
        if health:
            status = health.status

        details = StreamDetails(
            id=stream_id,
            name=config.name,
            status=status,
            version="2.1.9",
            start_time=config.created_at,
            manifest_url=config.manifest_url,
            tags=config.tags,
            variant_streams=[],
            current_metrics=current_metrics,
            health=health if health else StreamHealth(status=status),
            kpi_data=KPIData()
        )
        result.append(details)
    
    return result


@router.get("/{stream_id}", response_model=StreamDetails)
async def get_stream(stream_id: str):
    """Get detailed information about a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    config = stream_monitor.active_streams[stream_id]
    
    current_metrics = None
    if stream_id in stream_monitor.stream_metrics:
        current_metrics = stream_monitor.stream_metrics[stream_id]
    elif stream_id in metrics_db and metrics_db[stream_id]:
        current_metrics = metrics_db[stream_id][-1]
    
    # Get health with updated score
    health = stream_monitor.get_stream_health(stream_id)
    status = health.status if health else StreamStatus.ONLINE
    
    return StreamDetails(
        id=stream_id,
        name=config.name,
        status=status,
        version="2.1.9",
        start_time=config.created_at,
        manifest_url=config.manifest_url,
        service_name="StreamProbeX",
        tags=config.tags,
        variant_streams=[],
        current_metrics=current_metrics,
        health=health if health else StreamHealth(status=status),
        kpi_data=KPIData()
    )


@router.post("", response_model=StreamDetails)
async def create_stream(config: StreamConfig):
    """Add a new stream to monitor."""
    # Generate ID if not provided
    if not config.id:
        config.id = str(uuid.uuid4())
    
    # Add to monitor
    await stream_monitor.add_stream(config)
    
    # Store in DB
    streams_db[config.id] = config
    metrics_db[config.id] = []
    events_db[config.id] = []
    
    save_streams()
    
    return StreamDetails(
        id=config.id,
        name=config.name,
        status=StreamStatus.STARTING,
        version="2.1.9",
        start_time=config.created_at,
        manifest_url=config.manifest_url,
        tags=config.tags,
        variant_streams=[],
        kpi_data=KPIData()
    )


@router.delete("/{stream_id}")
async def delete_stream(stream_id: str):
    """Remove a stream from monitoring."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    await stream_monitor.remove_stream(stream_id)
    
    # Remove from DB
    if stream_id in streams_db:
        del streams_db[stream_id]
    if stream_id in metrics_db:
        del metrics_db[stream_id]
    if stream_id in events_db:
        del events_db[stream_id]
        
    save_streams()
    
    return {"status": "deleted", "stream_id": stream_id}


@router.get("/{stream_id}/metrics", response_model=List[SegmentMetrics])
async def get_metrics(
    stream_id: str,
    range: TimeRange = Query(TimeRange.THREE_MIN)
):
    """Get segment metrics for a time range."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if stream_id not in metrics_db:
        return []
    
    # Calculate time threshold
    now = datetime.utcnow()
    time_ranges = {
        TimeRange.THREE_MIN: timedelta(minutes=3),
        TimeRange.THIRTY_MIN: timedelta(minutes=30),
        TimeRange.THREE_HOUR: timedelta(hours=3),
        TimeRange.EIGHT_HOUR: timedelta(hours=8),
        TimeRange.TWO_DAY: timedelta(days=2),
        TimeRange.FOUR_DAY: timedelta(days=4)
    }
    
    threshold = now - time_ranges.get(range, timedelta(minutes=3))
    
    # Filter metrics
    filtered = [
        m for m in metrics_db[stream_id]
        if m.timestamp >= threshold
    ]
    
    return filtered


@router.get("/{stream_id}/sprites")
async def get_sprites(stream_id: str):
    """Get sprite maps for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    sprites = sprite_generator.get_all_sprites(stream_id)
    return {"sprites": sprites}


@router.get("/{stream_id}/segments", response_model=List[SegmentMetrics])
async def get_segments(
    stream_id: str,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get segment list with pagination."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if stream_id not in metrics_db:
        return []
    
    all_metrics = metrics_db[stream_id]
    
    # Newest first
    sorted_metrics = sorted(all_metrics, key=lambda x: x.timestamp, reverse=True)
    
    return sorted_metrics[offset:offset + limit]


@router.get("/{stream_id}/loudness")
async def get_loudness(
    stream_id: str,
    range: TimeRange = Query(TimeRange.THREE_MIN)
):
    """Get loudness data for a time range."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Read from logs
    now = datetime.utcnow()
    time_ranges = {
        TimeRange.THREE_MIN: timedelta(minutes=3),
        TimeRange.THIRTY_MIN: timedelta(minutes=30),
        TimeRange.THREE_HOUR: timedelta(hours=3),
        TimeRange.EIGHT_HOUR: timedelta(hours=8),
        TimeRange.TWO_DAY: timedelta(days=2),
        TimeRange.FOUR_DAY: timedelta(days=4)
    }
    
    start_date = now - time_ranges.get(range, timedelta(minutes=3))
    
    events = await log_service.read_events(
        start_date, now,
        stream_id=stream_id,
        event_type="loudness_analyzed",
        limit=1000
    )
    
    loudness_data = [event.get("loudness", {}) for event in events if "loudness" in event]
    
    return {"loudness_data": loudness_data}


@router.get("/{stream_id}/events")
async def get_events(
    stream_id: str,
    event_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get event log for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if not start_date:
        start_date = datetime.utcnow() - timedelta(hours=24)
    if not end_date:
        end_date = datetime.utcnow()
    
    events = await log_service.read_events(
        start_date, end_date,
        stream_id=stream_id,
        event_type=event_type,
        limit=limit
    )
    
    return {"events": events, "count": len(events)}


@router.get("/{stream_id}/health")
async def get_stream_health(stream_id: str):
    """Get detailed health status for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    health = stream_monitor.get_stream_health(stream_id)
    if not health:
        raise HTTPException(status_code=404, detail="Health data not available")
    
    return health


@router.get("/{stream_id}/video-metrics")
async def get_video_metrics(
    stream_id: str,
    range: TimeRange = Query(TimeRange.THREE_MIN)
):
    """Get video-specific metrics for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Get metrics history
    metrics = stream_monitor.get_metrics_history(stream_id, limit=200)
    
    # Transform to video-specific format
    video_data = []
    for m in metrics:
        video_data.append({
            "timestamp": m.timestamp.isoformat(),
            "bitrate_mbps": m.actual_bitrate,
            "download_speed_mbps": m.download_speed,
            "ttfb_ms": m.ttfb,
            "download_time_ms": m.download_time,
            "segment_duration_s": m.segment_duration,
            "segment_size_mb": m.segment_size_mb,
            "resolution": m.resolution
        })
    
    # Get current video metrics if available
    current = None
    if stream_id in stream_monitor.video_metrics:
        current = stream_monitor.video_metrics[stream_id]
    
    return {
        "history": video_data,
        "current": current
    }


@router.get("/{stream_id}/audio-metrics")
async def get_audio_metrics(
    stream_id: str,
    range: TimeRange = Query(TimeRange.THREE_MIN)
):
    """Get audio-specific metrics for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Get from in-memory history (faster)
    audio_data = stream_monitor.loudness_history.get(stream_id, [])
    
    # Apply time range filter
    now = datetime.utcnow()
    time_ranges = {
        TimeRange.THREE_MIN: timedelta(minutes=3),
        TimeRange.THIRTY_MIN: timedelta(minutes=30),
        TimeRange.THREE_HOUR: timedelta(hours=3),
        TimeRange.EIGHT_HOUR: timedelta(hours=8),
        TimeRange.TWO_DAY: timedelta(days=2),
        TimeRange.FOUR_DAY: timedelta(days=4)
    }
    
    start_date = now - time_ranges.get(range, timedelta(minutes=3))
    
    # Filter by time range
    filtered_data = []
    for item in audio_data:
        try:
            ts = item.get("timestamp")
            if ts:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts.replace(tzinfo=None) >= start_date:
                    filtered_data.append(item)
        except:
            filtered_data.append(item)  # Include if we can't parse timestamp
    
    # Get current audio metrics if available
    current = None
    health = stream_monitor.stream_health.get(stream_id)
    if health and health.audio_metrics:
        current = {
            "bitrate_kbps": health.audio_metrics.bitrate_kbps,
            "sample_rate": health.audio_metrics.sample_rate,
            "channels": health.audio_metrics.channels,
            "codec": health.audio_metrics.codec
        }
    
    return {
        "history": filtered_data,
        "current": current,
        "count": len(filtered_data)
    }


@router.get("/{stream_id}/thumbnail")
async def get_latest_thumbnail(stream_id: str):
    """Get the latest thumbnail for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Try to get cached thumbnail
    thumb_info = thumbnail_generator.get_latest_thumbnail_info(stream_id)
    
    if not thumb_info:
        # Fallback to current metrics
        current_metrics = stream_monitor.stream_metrics.get(stream_id)
        if not current_metrics or current_metrics.sequence_number is None:
            raise HTTPException(status_code=404, detail="No thumbnail available")
        
        thumbnail_path = f"/data/thumbnails/{stream_id}_{current_metrics.sequence_number}.jpg"
        return {
            "thumbnail_url": thumbnail_path,
            "sequence_number": current_metrics.sequence_number,
            "timestamp": current_metrics.timestamp.isoformat(),
            "cached": False
        }
    
    return {
        "thumbnail_url": f"/data/thumbnails/{Path(thumb_info['path']).name}",
        "sequence_number": thumb_info["sequence_number"],
        "expires_in": thumb_info["expires_in"],
        "is_fresh": thumb_info["is_fresh"],
        "cached": True
    }


@router.get("/{stream_id}/thumbnail/file")
async def get_thumbnail_file(stream_id: str):
    """Get the thumbnail file directly with proper caching headers."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Get cached thumbnail path
    thumb_path = stream_monitor.get_latest_thumbnail_path(stream_id)
    
    if not thumb_path or not Path(thumb_path).exists():
        raise HTTPException(status_code=404, detail="No thumbnail available")
    
    return FileResponse(
        thumb_path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=30",  # Cache for 30 seconds
            "X-Sequence": str(thumbnail_generator._cache.get(stream_id, [None, None, 0])[2])
        }
    )


@router.get("/{stream_id}/alerts")
async def get_stream_alerts(
    stream_id: str,
    include_resolved: bool = Query(False)
):
    """Get alerts for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if include_resolved:
        alerts = alert_service.get_alert_history(stream_id=stream_id, limit=100)
    else:
        alerts = alert_service.get_active_alerts(stream_id)
    
    return {
        "alerts": [a.to_dict() for a in alerts],
        "active_count": len([a for a in alerts if not a.resolved]),
        "total_count": len(alerts)
    }


@router.post("/{stream_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(stream_id: str, alert_id: str):
    """Acknowledge an alert."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    success = alert_service.acknowledge_alert(stream_id, alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "acknowledged", "alert_id": alert_id}


@router.get("/{stream_id}/logs")
async def get_stream_logs(
    stream_id: str,
    limit: int = Query(500, le=1000)
):
    """Get logs for a specific stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    logs = await log_service.read_stream_logs(stream_id, limit=limit)
    
    return {
        "logs": logs,
        "count": len(logs),
        "stream_id": stream_id
    }


@router.get("/{stream_id}/scte35-events")
async def get_scte35_events(stream_id: str):
    """Get SCTE-35 ad marker events for a stream."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    events = stream_monitor.scte35_events.get(stream_id, [])
    count = stream_monitor.scte35_counts.get(stream_id, 0)
    
    return {
        "events": events,
        "total_count": count,
        "stream_id": stream_id
    }
