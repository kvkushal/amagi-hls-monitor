import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    # Health alerts
    HEALTH_DEGRADED = "health_degraded"
    HEALTH_CRITICAL = "health_critical"
    
    # Error alerts
    HIGH_ERROR_RATE = "high_error_rate"
    CONTINUITY_ERRORS = "continuity_errors"
    SYNC_ERRORS = "sync_errors"
    TRANSPORT_ERRORS = "transport_errors"
    
    # Performance alerts
    SLOW_DOWNLOAD = "slow_download"
    HIGH_TTFB = "high_ttfb"
    SEGMENT_TIMEOUT = "segment_timeout"
    
    # Manifest alerts
    MANIFEST_ERROR = "manifest_error"
    VARIANT_LOST = "variant_lost"
    
    # Stream alerts
    STREAM_OFFLINE = "stream_offline"
    SCTE35_DETECTED = "scte35_detected"


@dataclass
class Alert:
    """Represents a stream alert."""
    alert_id: str
    stream_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "stream_id": self.stream_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class AlertThresholds:
    """Configurable alert thresholds."""
    
    # Health score thresholds
    HEALTH_WARNING = 60  # Below this = yellow
    HEALTH_CRITICAL = 40  # Below this = red
    
    # Error rate thresholds (percentage)
    ERROR_RATE_WARNING = 1.0
    ERROR_RATE_CRITICAL = 5.0
    
    # Continuity error thresholds (count per minute)
    CONTINUITY_WARNING = 5
    CONTINUITY_CRITICAL = 20
    
    # TTFB thresholds (milliseconds)
    TTFB_WARNING = 500
    TTFB_CRITICAL = 1000
    
    # Download speed ratio (actual vs expected)
    DOWNLOAD_RATIO_WARNING = 0.8
    DOWNLOAD_RATIO_CRITICAL = 0.5


class AlertService:
    """
    Alert service for monitoring stream health and raising alerts.
    
    Features:
    - Threshold-based alert generation
    - Alert deduplication
    - Auto-resolution of transient alerts
    - Alert history tracking
    """
    
    def __init__(self):
        # Active alerts per stream: stream_id -> {alert_type: Alert}
        self._active_alerts: Dict[str, Dict[AlertType, Alert]] = {}
        
        # Alert history (all alerts)
        self._alert_history: List[Alert] = []
        
        # Alert counter for generating IDs
        self._alert_counter = 0
        
        # Last check timestamps per stream
        self._last_checks: Dict[str, datetime] = {}
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        self._alert_counter += 1
        return f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{self._alert_counter}"
    
    def raise_alert(
        self,
        stream_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        metadata: Optional[Dict] = None
    ) -> Optional[Alert]:
        """
        Raise an alert for a stream.
        
        Deduplicates alerts of the same type for the same stream.
        """
        # Initialize stream's alert dict if needed
        if stream_id not in self._active_alerts:
            self._active_alerts[stream_id] = {}
        
        # Check for existing alert of same type
        if alert_type in self._active_alerts[stream_id]:
            existing = self._active_alerts[stream_id][alert_type]
            if not existing.resolved:
                # Update existing alert's timestamp and metadata
                existing.timestamp = datetime.utcnow()
                if metadata:
                    existing.metadata.update(metadata)
                return None  # Deduplicated
        
        # Create new alert
        alert = Alert(
            alert_id=self._generate_alert_id(),
            stream_id=stream_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata or {}
        )
        
        self._active_alerts[stream_id][alert_type] = alert
        self._alert_history.append(alert)
        
        logger.warning(f"Alert raised: [{severity.value}] {stream_id} - {message}")
        
        # Send webhook notification (async, don't await)
        try:
            from app.services.webhook_service import webhook_service
            import asyncio
            asyncio.create_task(webhook_service.send_alert(alert.to_dict()))
        except Exception as e:
            logger.debug(f"Could not send webhook: {e}")
        
        return alert
    
    def resolve_alert(self, stream_id: str, alert_type: AlertType) -> bool:
        """
        Resolve an active alert.
        
        Returns True if alert was found and resolved.
        """
        if stream_id not in self._active_alerts:
            return False
        
        if alert_type not in self._active_alerts[stream_id]:
            return False
        
        alert = self._active_alerts[stream_id][alert_type]
        if not alert.resolved:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Alert resolved: {stream_id} - {alert_type.value}")
            return True
        
        return False
    
    def acknowledge_alert(self, stream_id: str, alert_id: str) -> bool:
        """Acknowledge an alert by ID."""
        if stream_id not in self._active_alerts:
            return False
        
        for alert in self._active_alerts[stream_id].values():
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        
        return False
    
    def get_active_alerts(self, stream_id: str) -> List[Alert]:
        """Get all active (unresolved) alerts for a stream."""
        if stream_id not in self._active_alerts:
            return []
        
        return [
            alert for alert in self._active_alerts[stream_id].values()
            if not alert.resolved
        ]
    
    def get_all_active_alerts(self) -> List[Alert]:
        """Get all active alerts across all streams."""
        alerts = []
        for stream_alerts in self._active_alerts.values():
            alerts.extend([a for a in stream_alerts.values() if not a.resolved])
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_history(
        self,
        stream_id: Optional[str] = None,
        limit: int = 100,
        include_resolved: bool = True
    ) -> List[Alert]:
        """Get alert history, optionally filtered by stream."""
        alerts = self._alert_history
        
        if stream_id:
            alerts = [a for a in alerts if a.stream_id == stream_id]
        
        if not include_resolved:
            alerts = [a for a in alerts if not a.resolved]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_alerts(
        self,
        stream_id: str,
        include_resolved: bool = False
    ) -> List[Alert]:
        """Get alerts for a stream (for export API)."""
        return self.get_alert_history(stream_id, limit=1000, include_resolved=include_resolved)
    
    def check_health_thresholds(
        self,
        stream_id: str,
        health_score: int,
        error_rate: float,
        continuity_errors: int,
        ttfb_avg: float,
        download_ratio: float
    ):
        """
        Check health metrics against thresholds and raise/resolve alerts.
        
        Args:
            stream_id: Stream identifier
            health_score: Current health score (0-100)
            error_rate: Error rate percentage
            continuity_errors: Count of continuity errors
            ttfb_avg: Average TTFB in milliseconds
            download_ratio: Download speed / bitrate ratio
        """
        # Health score alerts
        if health_score < AlertThresholds.HEALTH_CRITICAL:
            self.raise_alert(
                stream_id,
                AlertType.HEALTH_CRITICAL,
                AlertSeverity.CRITICAL,
                f"Health score critical: {health_score}%",
                {"health_score": health_score}
            )
        elif health_score < AlertThresholds.HEALTH_WARNING:
            self.resolve_alert(stream_id, AlertType.HEALTH_CRITICAL)
            self.raise_alert(
                stream_id,
                AlertType.HEALTH_DEGRADED,
                AlertSeverity.WARNING,
                f"Health score degraded: {health_score}%",
                {"health_score": health_score}
            )
        else:
            self.resolve_alert(stream_id, AlertType.HEALTH_CRITICAL)
            self.resolve_alert(stream_id, AlertType.HEALTH_DEGRADED)
        
        # Error rate alerts
        if error_rate >= AlertThresholds.ERROR_RATE_CRITICAL:
            self.raise_alert(
                stream_id,
                AlertType.HIGH_ERROR_RATE,
                AlertSeverity.ERROR,
                f"High error rate: {error_rate:.2f}%",
                {"error_rate": error_rate}
            )
        elif error_rate >= AlertThresholds.ERROR_RATE_WARNING:
            self.raise_alert(
                stream_id,
                AlertType.HIGH_ERROR_RATE,
                AlertSeverity.WARNING,
                f"Elevated error rate: {error_rate:.2f}%",
                {"error_rate": error_rate}
            )
        else:
            self.resolve_alert(stream_id, AlertType.HIGH_ERROR_RATE)
        
        # Continuity error alerts
        if continuity_errors >= AlertThresholds.CONTINUITY_CRITICAL:
            self.raise_alert(
                stream_id,
                AlertType.CONTINUITY_ERRORS,
                AlertSeverity.ERROR,
                f"High continuity errors: {continuity_errors}",
                {"count": continuity_errors}
            )
        elif continuity_errors >= AlertThresholds.CONTINUITY_WARNING:
            self.raise_alert(
                stream_id,
                AlertType.CONTINUITY_ERRORS,
                AlertSeverity.WARNING,
                f"Continuity errors detected: {continuity_errors}",
                {"count": continuity_errors}
            )
        else:
            self.resolve_alert(stream_id, AlertType.CONTINUITY_ERRORS)
        
        # TTFB alerts
        if ttfb_avg >= AlertThresholds.TTFB_CRITICAL:
            self.raise_alert(
                stream_id,
                AlertType.HIGH_TTFB,
                AlertSeverity.ERROR,
                f"Very high TTFB: {ttfb_avg:.0f}ms",
                {"ttfb_ms": ttfb_avg}
            )
        elif ttfb_avg >= AlertThresholds.TTFB_WARNING:
            self.raise_alert(
                stream_id,
                AlertType.HIGH_TTFB,
                AlertSeverity.WARNING,
                f"High TTFB: {ttfb_avg:.0f}ms",
                {"ttfb_ms": ttfb_avg}
            )
        else:
            self.resolve_alert(stream_id, AlertType.HIGH_TTFB)
        
        # Download speed alerts
        if download_ratio <= AlertThresholds.DOWNLOAD_RATIO_CRITICAL:
            self.raise_alert(
                stream_id,
                AlertType.SLOW_DOWNLOAD,
                AlertSeverity.ERROR,
                f"Slow download: {download_ratio:.2f}x realtime",
                {"ratio": download_ratio}
            )
        elif download_ratio <= AlertThresholds.DOWNLOAD_RATIO_WARNING:
            self.raise_alert(
                stream_id,
                AlertType.SLOW_DOWNLOAD,
                AlertSeverity.WARNING,
                f"Download speed degraded: {download_ratio:.2f}x realtime",
                {"ratio": download_ratio}
            )
        else:
            self.resolve_alert(stream_id, AlertType.SLOW_DOWNLOAD)
    
    def cleanup_stream(self, stream_id: str):
        """Remove all alerts for a stream (call when stream is removed)."""
        if stream_id in self._active_alerts:
            del self._active_alerts[stream_id]
        
        if stream_id in self._last_checks:
            del self._last_checks[stream_id]
        
        logger.info(f"Cleaned up alerts for stream: {stream_id}")
    
    def cleanup_old_alerts(self, max_age_hours: int = 24):
        """Remove old resolved alerts from history."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        self._alert_history = [
            a for a in self._alert_history
            if not a.resolved or (a.resolved_at and a.resolved_at > cutoff)
        ]


# Global instance
alert_service = AlertService()
