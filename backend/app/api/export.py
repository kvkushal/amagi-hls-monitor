"""Export API for CSV downloads of metrics, alerts, and events."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from typing import Optional
import csv
import io

from app.services.stream_monitor import stream_monitor
from app.services.alert_service import alert_service
from app.models import TimeRange

router = APIRouter(prefix="/api/export", tags=["export"])


def time_range_to_timedelta(range_str: str) -> timedelta:
    """Convert time range string to timedelta."""
    ranges = {
        "3m": timedelta(minutes=3),
        "30m": timedelta(minutes=30),
        "3h": timedelta(hours=3),
        "8h": timedelta(hours=8),
        "2d": timedelta(days=2),
        "4d": timedelta(days=4)
    }
    return ranges.get(range_str, timedelta(hours=24))


@router.get("/{stream_id}/metrics.csv")
async def export_metrics_csv(stream_id: str, range: str = "3h"):
    """Export metrics history as CSV."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Get metrics history
    metrics = stream_monitor.metrics_history.get(stream_id, [])
    
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics data available")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "timestamp", "sequence_number", "segment_duration", "segment_size_mb",
        "actual_bitrate", "declared_bitrate", "download_time", "download_speed",
        "ttfb", "resolution", "filename"
    ])
    
    # Data rows
    for m in metrics:
        writer.writerow([
            m.timestamp.isoformat(),
            m.sequence_number,
            m.segment_duration,
            m.segment_size_mb,
            m.actual_bitrate,
            m.declared_bitrate,
            m.download_time,
            m.download_speed,
            m.ttfb,
            m.resolution,
            m.filename
        ])
    
    output.seek(0)
    
    stream_name = stream_monitor.active_streams[stream_id].name
    filename = f"{stream_name}_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{stream_id}/alerts.csv")
async def export_alerts_csv(stream_id: str):
    """Export alerts history as CSV."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Get alerts from alert service
    alerts = alert_service.get_alerts(stream_id, include_resolved=True)
    
    if not alerts:
        raise HTTPException(status_code=404, detail="No alerts data available")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "id", "timestamp", "alert_type", "severity", "message",
        "threshold_value", "actual_value", "resolved", "resolved_at", "acknowledged"
    ])
    
    # Data rows
    for a in alerts:
        writer.writerow([
            a.alert_id,
            a.timestamp.isoformat(),
            a.alert_type.value if hasattr(a.alert_type, 'value') else a.alert_type,
            a.severity.value if hasattr(a.severity, 'value') else a.severity,
            a.message,
            a.metadata.get("threshold_value", ""),
            a.metadata.get("actual_value", ""),
            a.resolved,
            a.resolved_at.isoformat() if a.resolved_at else "",
            a.acknowledged
        ])
    
    output.seek(0)
    
    stream_name = stream_monitor.active_streams[stream_id].name
    filename = f"{stream_name}_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{stream_id}/scte35.csv")
async def export_scte35_csv(stream_id: str):
    """Export SCTE-35 markers as CSV."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    events = stream_monitor.scte35_events.get(stream_id, [])
    
    if not events:
        raise HTTPException(status_code=404, detail="No SCTE-35 events detected")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "timestamp", "event_type", "segment_sequence", "duration", "splice_command_type"
    ])
    
    # Data rows
    for e in events:
        writer.writerow([
            e.get("timestamp", ""),
            e.get("event_type", ""),
            e.get("segment_sequence", ""),
            e.get("duration", ""),
            e.get("splice_command_type", "")
        ])
    
    output.seek(0)
    
    stream_name = stream_monitor.active_streams[stream_id].name
    filename = f"{stream_name}_scte35_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{stream_id}/loudness.csv")
async def export_loudness_csv(stream_id: str):
    """Export loudness history as CSV."""
    if stream_id not in stream_monitor.active_streams:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    data = stream_monitor.loudness_history.get(stream_id, [])
    
    if not data:
        raise HTTPException(status_code=404, detail="No loudness data available")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "timestamp", "momentary_lufs", "shortterm_lufs", "integrated_lufs", "rms_db", "is_approximation"
    ])
    
    # Data rows
    for d in data:
        writer.writerow([
            d.get("timestamp", ""),
            d.get("momentary_lufs", ""),
            d.get("shortterm_lufs", ""),
            d.get("integrated_lufs", ""),
            d.get("rms_db", ""),
            d.get("is_approximation", False)
        ])
    
    output.seek(0)
    
    stream_name = stream_monitor.active_streams[stream_id].name
    filename = f"{stream_name}_loudness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
