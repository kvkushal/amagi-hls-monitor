from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class StreamStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    STARTING = "starting"


class TimeRange(str, Enum):
    THREE_MIN = "3min"
    THIRTY_MIN = "30min"
    THREE_HOUR = "3h"
    EIGHT_HOUR = "8h"
    TWO_DAY = "2d"
    FOUR_DAY = "4d"


class EventType(str, Enum):
    SEGMENT_DOWNLOADED = "segment_downloaded"
    MANIFEST_UPDATED = "manifest_updated"
    THUMBNAIL_GENERATED = "thumbnail_generated"
    SPRITE_GENERATED = "sprite_generated"
    ERROR = "error"
    WARNING = "warning"
    AD_DETECTED = "ad_detected"
    SPLICE_DETECTED = "splice_detected"
    BANDWIDTH_RESERVATION = "bandwidth_reservation"


class AlarmType(str, Enum):
    TS_SYNC_LOST = "ts_sync_lost"
    PAT_ERROR = "pat_error"
    PMT_ERROR = "pmt_error"
    PID_ERROR = "pid_error"
    CONTINUITY_COUNT = "continuity_count"
    PCR_ERROR = "pcr_error"
    PCR_ACCURACY_ERROR = "pcr_accuracy_error"
    PTS_REPETITION_ERROR = "pts_repetition_error"
    CAT_ERROR = "cat_error"
    TRANSPORT_ERROR = "transport_error"
    CRC_ERROR = "crc_error"
    PCR_DISCONTINUITY = "pcr_discontinuity"
    UNREFERENCED_PID = "unreferenced_pid"
    SI_REPETITION_ERROR = "si_repetition_error"
    BUFFER_ERROR = "buffer_error"
    NIT_ERROR = "nit_error"
    EIT_ERROR = "eit_error"


class StreamConfig(BaseModel):
    id: str
    name: str
    manifest_url: str
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SegmentMetrics(BaseModel):
    uri: str
    filename: str
    resolution: Optional[str] = None
    bandwidth: Optional[int] = None
    actual_bitrate: float  # Mbps
    download_speed: float  # Mbps
    segment_duration: float  # seconds
    ttfb: float  # milliseconds
    download_time: float  # milliseconds
    segment_size_bytes: int
    segment_size_mb: float
    timestamp: datetime
    sequence_number: Optional[int] = None


class VariantStream(BaseModel):
    uri: str
    resolution: Optional[str] = None
    bandwidth: Optional[int] = None
    codecs: Optional[str] = None
    frame_rate: Optional[float] = None


class ThumbnailInfo(BaseModel):
    segment_uri: str
    timestamp: datetime
    thumbnail_path: str
    width: int
    height: int
    is_error: bool = False  # Gray placeholder


class SpriteInfo(BaseModel):
    sprite_id: str
    sprite_path: str
    sprite_map_path: str
    start_timestamp: datetime
    end_timestamp: datetime
    thumbnail_count: int
    grid_width: int
    grid_height: int
    created_at: datetime


class SpriteMap(BaseModel):
    sprite_id: str
    sprite_url: str
    thumbnails: List[Dict[str, Any]]  # [{"timestamp": ..., "x": ..., "y": ..., "w": ..., "h": ...}]


class LoudnessData(BaseModel):
    timestamp: datetime
    momentary_lufs: Optional[float] = None
    shortterm_lufs: Optional[float] = None
    integrated_lufs: Optional[float] = None
    rms_db: Optional[float] = None  # Fallback
    is_approximation: bool = False


class AdMarker(BaseModel):
    timestamp: datetime
    type: str  # "ad_insertion", "splice_null", "bandwidth_reservation"
    duration: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamEvent(BaseModel):
    event_id: str
    stream_id: str
    event_type: EventType
    timestamp: datetime
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"  # info, warning, error


class StreamAlarm(BaseModel):
    alarm_id: str
    stream_id: str
    alarm_type: AlarmType
    timestamp: datetime
    description: str
    count: int = 1
    resolved: bool = False


class KPIData(BaseModel):
    task_count: int = 0
    bs_errors: int = 0
    mlt_warnings: int = 0
    mls_warnings: int = 0
    alarm_count: int = 0
    kpi_errors: int = 0


class TR101290Metrics(BaseModel):
    sync_byte_errors: int = 0
    continuity_errors: int = 0
    transport_errors: int = 0
    pid_errors: int = 0
    pcr_errors: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ManifestError(BaseModel):
    error_type: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = "error"


class HealthColor(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class HealthScore(BaseModel):
    """Composite health score for a stream."""
    score: int = Field(default=100, ge=0, le=100)  # 0-100
    color: HealthColor = HealthColor.GREEN
    factors: Dict[str, Any] = Field(default_factory=dict)
    
    @staticmethod
    def compute(
        error_rate: float = 0.0,
        continuity_errors: int = 0,
        sync_errors: int = 0,
        transport_errors: int = 0,
        ttfb_avg: float = 0.0,
        download_ratio: float = 1.0,
        manifest_errors: int = 0
    ) -> "HealthScore":
        """Compute health score from various factors."""
        score = 100
        factors = {}
        
        # Error rate impact (max -30 points)
        if error_rate > 0:
            error_penalty = min(30, int(error_rate * 10))
            score -= error_penalty
            factors["error_rate"] = f"-{error_penalty} (rate: {error_rate:.1f}%)"
        
        # Continuity errors impact (max -20 points)
        if continuity_errors > 0:
            cc_penalty = min(20, continuity_errors * 2)
            score -= cc_penalty
            factors["continuity_errors"] = f"-{cc_penalty} (count: {continuity_errors})"
        
        # Sync errors impact (max -25 points, critical)
        if sync_errors > 0:
            sync_penalty = min(25, sync_errors * 5)
            score -= sync_penalty
            factors["sync_errors"] = f"-{sync_penalty} (count: {sync_errors})"
        
        # Transport errors impact (max -15 points)
        if transport_errors > 0:
            transport_penalty = min(15, transport_errors * 3)
            score -= transport_penalty
            factors["transport_errors"] = f"-{transport_penalty} (count: {transport_errors})"
        
        # TTFB impact (max -10 points if > 500ms)
        if ttfb_avg > 500:
            ttfb_penalty = min(10, int((ttfb_avg - 500) / 100))
            score -= ttfb_penalty
            factors["high_ttfb"] = f"-{ttfb_penalty} (avg: {ttfb_avg:.0f}ms)"
        
        # Download ratio impact (slow downloads)
        if download_ratio < 1.0:
            ratio_penalty = min(15, int((1.0 - download_ratio) * 30))
            score -= ratio_penalty
            factors["slow_download"] = f"-{ratio_penalty} (ratio: {download_ratio:.2f}x)"
        
        # Manifest errors impact
        if manifest_errors > 0:
            manifest_penalty = min(10, manifest_errors * 5)
            score -= manifest_penalty
            factors["manifest_errors"] = f"-{manifest_penalty} (count: {manifest_errors})"
        
        score = max(0, score)
        
        # Determine color
        if score >= 80:
            color = HealthColor.GREEN
        elif score >= 50:
            color = HealthColor.YELLOW
        else:
            color = HealthColor.RED
        
        return HealthScore(score=score, color=color, factors=factors)


class AudioMetrics(BaseModel):
    """Audio-specific metrics for a stream."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    bitrate_kbps: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: Optional[str] = None
    packet_loss_percent: float = 0.0
    jitter_ms: float = 0.0
    peak_level_db: Optional[float] = None
    average_level_db: Optional[float] = None
    silence_detected: bool = False
    clipping_detected: bool = False
    loudness_lufs: Optional[float] = None
    loudness_range: Optional[float] = None


class VideoMetrics(BaseModel):
    """Video-specific metrics for a stream."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    bitrate_kbps: Optional[float] = None
    resolution: Optional[str] = None
    frame_rate: Optional[float] = None
    codec: Optional[str] = None
    gop_size: Optional[int] = None
    keyframe_interval: Optional[float] = None
    dropped_frames: int = 0
    black_frames_detected: bool = False
    freeze_detected: bool = False
    # SCTE-35 markers
    scte35_detected: bool = False
    scte35_count: int = 0


class AlertModel(BaseModel):
    """Alert model for threshold-based notifications."""
    alert_id: str
    stream_id: str
    alert_type: str
    severity: str  # info, warning, error, critical
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class StreamHealth(BaseModel):
    status: StreamStatus
    health_score: HealthScore = Field(default_factory=HealthScore)
    uptime_percentage: float = 100.0
    error_rate_last_hour: float = 0.0
    active_alarms: List[StreamAlarm] = []
    active_alerts: List[AlertModel] = []
    tr101290_metrics: TR101290Metrics = Field(default_factory=TR101290Metrics)
    manifest_errors: List[ManifestError] = []
    audio_metrics: Optional[AudioMetrics] = None
    video_metrics: Optional[VideoMetrics] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class StreamDetails(BaseModel):
    id: str
    name: str
    status: StreamStatus
    version: str
    start_time: datetime
    manifest_url: str
    service_name: Optional[str] = None
    tags: List[str]
    variant_streams: List[VariantStream]
    current_metrics: Optional[SegmentMetrics] = None
    health: StreamHealth = Field(default_factory=lambda: StreamHealth(status=StreamStatus.STARTING))
    kpi_data: KPIData
    thumbnail_url: Optional[str] = None




class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    workers_active: bool
    log_rotation_active: bool
    storage_available: bool
    version: str


# WebSocket message models
class WSMessage(BaseModel):
    type: str
    stream_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

