import asyncio
import aiohttp
import time
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from urllib.parse import urljoin
from app.config import settings
from app.models import StreamConfig, SegmentMetrics, VariantStream, StreamEvent, EventType, LoudnessData
from app.services.thumbnail_generator import thumbnail_generator
from app.services.sprite_generator import sprite_generator
from app.services.loudness_analyzer import loudness_analyzer
from app.services.ad_detector import ad_detector
from app.services.metrics_calculator import metrics_calculator
from app.services.logger_service import log_service
from app.services.websocket_manager import ws_manager
from app.services.ts_analyzer import ts_analyzer
from app.services.alert_service import alert_service
from app.models import (
    StreamConfig, SegmentMetrics, VariantStream, StreamEvent, EventType, 
    LoudnessData, StreamHealth, TR101290Metrics, ManifestError, StreamStatus,
    HealthScore, AudioMetrics, VideoMetrics, AlertModel
)

logger = logging.getLogger(__name__)


class StreamMonitor:
    """Core HLS stream monitoring engine."""
    
    def __init__(self):
        self.active_streams: Dict[str, StreamConfig] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.seen_segments: Dict[str, Set[str]] = {}  # stream_id -> set of segment URIs
        self.stream_metrics: Dict[str, SegmentMetrics] = {}
        self.segment_counter: Dict[str, int] = {}  # stream_id -> segment count
        self.thumbnails_buffer: Dict[str, List] = {}  # stream_id -> [(path, timestamp), ...]
        self.stream_health: Dict[str, StreamHealth] = {} # stream_id -> StreamHealth
        self.last_manifest_state: Dict[str, dict] = {} # stream_id -> {variant_count: int, ...}
        
        # New tracking for health computation
        self.metrics_history: Dict[str, List[SegmentMetrics]] = {}  # stream_id -> recent metrics
        self.audio_metrics: Dict[str, AudioMetrics] = {}  # stream_id -> latest audio metrics
        self.video_metrics: Dict[str, VideoMetrics] = {}  # stream_id -> latest video metrics
        self.error_counts: Dict[str, Dict[str, int]] = {}  # stream_id -> {error_type: count}
        self.last_sequence: Dict[str, int] = {}  # stream_id -> last seen sequence number
        self.segment_gaps: Dict[str, int] = {}  # stream_id -> count of sequence gaps
        self.scte35_counts: Dict[str, int] = {}  # stream_id -> SCTE-35 marker count
        self.scte35_events: Dict[str, List[dict]] = {}  # stream_id -> list of SCTE-35 events
        self.loudness_history: Dict[str, List[dict]] = {}  # stream_id -> recent loudness data
        self.recording_enabled: Dict[str, bool] = {}  # stream_id -> recording flag
        
        self.segments_dir = Path(settings.SEGMENTS_DIR)
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def start(self):
        """Initialize the monitor."""
        self.session = aiohttp.ClientSession()
        logger.info("StreamMonitor started")
    
    async def stop(self):
        """Cleanup the monitor."""
        # Stop all monitoring tasks
        for task in self.monitoring_tasks.values():
            task.cancel()
        
        if self.session:
            await self.session.close()
        
        logger.info("StreamMonitor stopped")
    
    async def add_stream(self, stream_config: StreamConfig):
        """Add a stream to monitor."""
        if stream_config.id in self.active_streams:
            logger.warning(f"Stream {stream_config.id} already being monitored")
            return
        
        self.active_streams[stream_config.id] = stream_config
        self.seen_segments[stream_config.id] = set()
        self.segment_counter[stream_config.id] = 0
        self.thumbnails_buffer[stream_config.id] = []
        self.stream_health[stream_config.id] = StreamHealth(status=StreamStatus.STARTING)
        self.last_manifest_state[stream_config.id] = {}
        
        # Initialize new tracking fields
        self.metrics_history[stream_config.id] = []
        self.error_counts[stream_config.id] = {"segment": 0, "manifest": 0, "download": 0}
        self.last_sequence[stream_config.id] = -1
        self.segment_gaps[stream_config.id] = 0
        self.scte35_counts[stream_config.id] = 0
        self.scte35_events[stream_config.id] = []
        self.loudness_history[stream_config.id] = []
        self.recording_enabled[stream_config.id] = False
        
        # Start monitoring task
        task = asyncio.create_task(self._monitor_stream(stream_config))
        self.monitoring_tasks[stream_config.id] = task
        
        logger.info(f"Started monitoring stream: {stream_config.name} ({stream_config.id})")
        
        # Log event (fire and forget - don't block)
        asyncio.create_task(log_service.write_stream_event(
            stream_config.id,
            "stream_added",
            f"Started monitoring stream: {stream_config.name}",
            severity="info",
            metadata={"manifest_url": stream_config.manifest_url}
        ))
    
    async def remove_stream(self, stream_id: str):
        """Remove a stream from monitoring."""
        if stream_id not in self.active_streams:
            return
        
        # Cancel monitoring task - don't wait, just cancel
        if stream_id in self.monitoring_tasks:
            try:
                self.monitoring_tasks[stream_id].cancel()
            except Exception:
                pass
            del self.monitoring_tasks[stream_id]
        
        # Cleanup dictionaries - wrap in try/except to prevent any blocking
        try:
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            if stream_id in self.seen_segments:
                del self.seen_segments[stream_id]
            if stream_id in self.segment_counter:
                del self.segment_counter[stream_id]
            if stream_id in self.thumbnails_buffer:
                del self.thumbnails_buffer[stream_id]
            if stream_id in self.stream_health:
                del self.stream_health[stream_id]
            if stream_id in self.last_manifest_state:
                del self.last_manifest_state[stream_id]
            if stream_id in self.metrics_history:
                del self.metrics_history[stream_id]
            if stream_id in self.audio_metrics:
                del self.audio_metrics[stream_id]
            if stream_id in self.video_metrics:
                del self.video_metrics[stream_id]
            if stream_id in self.error_counts:
                del self.error_counts[stream_id]
            if stream_id in self.last_sequence:
                del self.last_sequence[stream_id]
            if stream_id in self.segment_gaps:
                del self.segment_gaps[stream_id]
            if stream_id in self.scte35_counts:
                del self.scte35_counts[stream_id]
            if stream_id in self.scte35_events:
                del self.scte35_events[stream_id]
            if stream_id in self.loudness_history:
                del self.loudness_history[stream_id]
            if stream_id in self.recording_enabled:
                del self.recording_enabled[stream_id]
        except Exception as e:
            logger.error(f"Error cleaning up stream data: {e}")
        
        # Cleanup services - fire and forget
        try:
            alert_service.cleanup_stream(stream_id)
            thumbnail_generator.cleanup_stream_thumbnails(stream_id)
        except Exception as e:
            logger.error(f"Error in service cleanup: {e}")
        
        logger.info(f"Stopped monitoring stream: {stream_id}")
        
        # Fire and forget - don't await, just create task
        asyncio.create_task(log_service.write_stream_event(
            stream_id,
            "stream_removed",
            f"Stopped monitoring stream",
            severity="info"
        ))
    
    async def _monitor_stream(self, stream_config: StreamConfig):
        """Main monitoring loop for a stream."""
        stream_id = stream_config.id
        current_url = stream_config.manifest_url
        
        while True:
            try:
                # Fetch manifest
                manifest_content = await self._fetch_manifest(current_url)
                
                if manifest_content:
                    # Update status
                    if stream_id in self.stream_health:
                        self.stream_health[stream_id].status = StreamStatus.ONLINE

                    # Parse manifest
                    variant_streams, segments = self._parse_manifest(manifest_content, current_url)
                    
                    # Handle Master Playlist
                    if not segments and variant_streams:
                        # Select highest bandwidth variant
                        best_variant = max(variant_streams, key=lambda x: x.bandwidth)
                        logger.info(f"Found Master Playlist for {stream_id}. Switching to variant: {best_variant.resolution} ({best_variant.bandwidth} bps)")
                        
                        # Update URL to monitor the variant
                        current_url = best_variant.uri
                        
                        # Log event (fire and forget)
                        asyncio.create_task(log_service.write_event({
                            "event_type": "variant_selected",
                            "stream_id": stream_id,
                            "variant_info": best_variant.dict()
                        }))
                        
                        # Immediately continue to fetch the variant manifest
                        continue

                    # Detect ads
                    ad_markers = ad_detector.parse_manifest(manifest_content)
                    for marker in ad_markers:
                        await self._broadcast_event(stream_id, "ad_detected", {
                            "type": marker.type,
                            "timestamp": marker.timestamp.isoformat(),
                            "duration": marker.duration,
                            "metadata": marker.metadata
                        })
                    
                    # Process new segments
                    for segment_url in segments:
                        if segment_url not in self.seen_segments[stream_id]:
                            self.seen_segments[stream_id].add(segment_url)
                            
                            # Process segment in background
                            asyncio.create_task(self._process_segment(stream_id, segment_url))
                    
                    # Broadcast manifest update
                    await self._broadcast_event(stream_id, "manifest_updated", {
                        "variant_count": len(variant_streams),
                        "segment_count": len(segments)
                    })

                    # Manifest Analysis
                    await self._analyze_manifest_changes(stream_id, variant_streams, segments)
                
                # Wait before next poll
                await asyncio.sleep(settings.MANIFEST_POLL_INTERVAL)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                if stream_id in self.stream_health:
                    self.stream_health[stream_id].status = StreamStatus.ERROR
                
                logger.error(f"Error monitoring stream {stream_id}: {e}")
                await self._broadcast_event(stream_id, "error", {
                    "message": str(e)
                })
                await asyncio.sleep(settings.MANIFEST_POLL_INTERVAL)
    
    async def _fetch_manifest(self, url: str) -> Optional[str]:
        """Fetch HLS manifest."""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Failed to fetch manifest: {response.status} for URL: {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching manifest {url}: {e}")
            return None
    
    def _parse_manifest(self, content: str, base_url: str) -> tuple:
        """Parse HLS manifest to extract variant streams and segments."""
        lines = content.split('\n')
        variant_streams = []
        segments = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Variant stream
            if line.startswith('#EXT-X-STREAM-INF:'):
                info = self._parse_stream_inf(line)
                if i + 1 < len(lines):
                    uri = lines[i + 1].strip()
                    if uri and not uri.startswith('#'):
                        info['uri'] = urljoin(base_url, uri)
                        variant_streams.append(VariantStream(**info))
                i += 1
            
            # Media segment
            elif line.startswith('#EXTINF:'):
                if i + 1 < len(lines):
                    uri = lines[i + 1].strip()
                    if uri and not uri.startswith('#'):
                        segments.append(urljoin(base_url, uri))
                i += 1
            
            i += 1
        
        return variant_streams, segments
    
    def _parse_stream_inf(self, line: str) -> dict:
        """Parse #EXT-X-STREAM-INF attributes."""
        info = {}
        
        # BANDWIDTH
        bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
        if bandwidth_match:
            info['bandwidth'] = int(bandwidth_match.group(1))
        
        # RESOLUTION
        resolution_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
        if resolution_match:
            info['resolution'] = resolution_match.group(1)
        
        # CODECS
        codecs_match = re.search(r'CODECS="([^"]+)"', line)
        if codecs_match:
            info['codecs'] = codecs_match.group(1)
        
        # FRAME-RATE
        fps_match = re.search(r'FRAME-RATE=([0-9.]+)', line)
        if fps_match:
            info['frame_rate'] = float(fps_match.group(1))
        
        return info
    
    async def _process_segment(self, stream_id: str, segment_url: str):
        """Download and process a segment."""
        try:
            # Download segment with metrics
            segment_data = await self._download_segment(segment_url)
            
            if not segment_data:
                return
            
            # Save segment to disk
            segment_filename = f"{stream_id}_{self.segment_counter[stream_id]}.ts"
            segment_path = self.segments_dir / segment_filename
            
            # Use content from metrics download
            with open(segment_path, 'wb') as f:
                f.write(segment_data['content'])
            
            # Get segment duration (probe)
            duration = await self._probe_duration(str(segment_path))
            if not duration:
                duration = 6.0  # Default fallback
            
            # Calculate metrics
            metrics_data = {
                'segment_size_bytes': segment_data['size'],
                'segment_duration': duration,
                'download_time': segment_data['download_time'],
                'ttfb': segment_data['ttfb']
            }
            
            calculated_metrics = metrics_calculator.calculate_all_metrics(metrics_data)
            
            # Create segment metrics
            metrics = SegmentMetrics(
                uri=segment_url,
                filename=segment_filename,
                actual_bitrate=calculated_metrics['actual_bitrate'],
                download_speed=calculated_metrics['download_speed'],
                segment_duration=duration,
                ttfb=calculated_metrics['ttfb'],
                download_time=calculated_metrics['download_time'],
                segment_size_bytes=calculated_metrics['segment_size_bytes'],
                segment_size_mb=calculated_metrics['segment_size_mb'],
                timestamp=datetime.utcnow(),
                sequence_number=self.segment_counter[stream_id]
            )

            # Update current metrics
            self.stream_metrics[stream_id] = metrics
            
            # Add to metrics history (keep last 500)
            if stream_id in self.metrics_history:
                self.metrics_history[stream_id].append(metrics)
                if len(self.metrics_history[stream_id]) > 500:
                    self.metrics_history[stream_id] = self.metrics_history[stream_id][-500:]
            
            # Update health score
            self._update_health_score(stream_id)
            
            # Generate thumbnail
            thumbnail_path = await thumbnail_generator.generate_thumbnail_for_segment(
                stream_id, segment_url, str(segment_path), self.segment_counter[stream_id]
            )
            
            if thumbnail_path:
                self.thumbnails_buffer[stream_id].append((thumbnail_path, metrics.timestamp))
                
                # Convert to relative URL for frontend
                relative_path = f"/data/thumbnails/{Path(thumbnail_path).name}"
                
                await self._broadcast_event(stream_id, "thumbnail_generated", {
                    "thumbnail_path": relative_path,
                    "sequence": self.segment_counter[stream_id]
                })
            
            # Generate sprite if buffer is full
            if len(self.thumbnails_buffer[stream_id]) >= settings.SPRITE_SEGMENT_COUNT:
                await self._generate_sprite(stream_id)
            
            # Analyze loudness (async, don't wait)
            asyncio.create_task(self._analyze_loudness(stream_id, str(segment_path), metrics.timestamp))

            # Analyze TS (async)
            asyncio.create_task(self._analyze_ts(stream_id, str(segment_path)))
            
            # Increment counter
            self.segment_counter[stream_id] += 1
            
            # Broadcast segment event
            # Use json() to ensure datetime is serialized to ISO format, then load back to dict
            import json
            await self._broadcast_event(stream_id, "segment_downloaded", json.loads(metrics.json()))
            
            # Log event
            await log_service.write_event({
                "event_type": "segment_downloaded",
                "stream_id": stream_id,
                "segment_url": segment_url,
                "metrics": json.loads(metrics.json())
            })
        
        except Exception as e:
            logger.error(f"Error processing segment {segment_url}: {e}")
            await self._broadcast_event(stream_id, "error", {
                "message": f"Failed to process segment: {str(e)}",
                "segment_url": segment_url
            })
    
    async def _download_segment(self, url: str) -> Optional[dict]:
        """Download a segment and measure TTFB and download time."""
        try:
            ttfb_start = time.time()
            download_start = None
            size = 0
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=settings.DOWNLOAD_TIMEOUT)) as response:
                if response.status != 200:
                    return None
                
                # TTFB: time to first byte
                ttfb = (time.time() - ttfb_start) * 1000  # milliseconds
                download_start = time.time()
                
                # Read content
                content = await response.read()
                size = len(content)
                
                download_time = (time.time() - download_start) * 1000  # milliseconds
                
                return {
                    'ttfb': ttfb,
                    'download_time': download_time,
                    'size': size,
                    'content': content
                }
        
        except Exception as e:
            logger.error(f"Error downloading segment {url}: {e}")
            return None
    
    async def _probe_duration(self, file_path: str) -> Optional[float]:
        """Use ffprobe to get segment duration."""
        try:
            process = await asyncio.create_subprocess_exec(
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Add timeout to prevent hangs
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5.0)
            
            if process.returncode == 0:
                return float(stdout.decode().strip())
            return None
        except:
            return None
    
    async def _analyze_loudness(self, stream_id: str, segment_path: str, timestamp: datetime):
        """Analyze segment loudness and broadcast results."""
        try:
            loudness_data = await loudness_analyzer.analyze_segment(segment_path)
            
            if loudness_data:
                loudness = LoudnessData(
                    timestamp=timestamp,
                    **loudness_data
                )
                
                import json
                loudness_dict = json.loads(loudness.json())
                
                # Store in memory for quick access
                if stream_id in self.loudness_history:
                    self.loudness_history[stream_id].append(loudness_dict)
                    # Keep last 200 entries
                    if len(self.loudness_history[stream_id]) > 200:
                        self.loudness_history[stream_id] = self.loudness_history[stream_id][-200:]
                
                await self._broadcast_event(stream_id, "loudness_data", loudness_dict)
                
                await log_service.write_stream_event(
                    stream_id,
                    "loudness_analyzed",
                    "Loudness analysis complete",
                    severity="info",
                    metadata={"loudness": loudness_dict}
                )
        except Exception as e:
            logger.error(f"Error analyzing loudness: {e}")
    
    async def _generate_sprite(self, stream_id: str):
        """Generate sprite from buffered thumbnails."""
        try:
            buffer = self.thumbnails_buffer[stream_id]
            if not buffer:
                return
            
            thumbnail_paths = [item[0] for item in buffer]
            timestamps = [item[1] for item in buffer]
            
            sprite_info = sprite_generator.generate_sprite(stream_id, thumbnail_paths, timestamps)
            
            # Clear buffer
            self.thumbnails_buffer[stream_id] = []
            
            await self._broadcast_event(stream_id, "sprite_generated", {
                "sprite_id": sprite_info.sprite_id,
                "sprite_path": sprite_info.sprite_path,
                "thumbnail_count": sprite_info.thumbnail_count
            })
            
            await log_service.write_event({
                "event_type": "sprite_generated",
                "stream_id": stream_id,
                "sprite_info": sprite_info.dict()
            })
        
        except Exception as e:
            logger.error(f"Error generating sprite: {e}")
    
    async def _analyze_ts(self, stream_id: str, segment_path: str):
        """Analyze MPEG-TS structure."""
        try:
            # Run analysis in thread pool to avoid blocking
            metrics = await asyncio.to_thread(ts_analyzer.analyze_segment, segment_path)
            
            if stream_id in self.stream_health:
                health = self.stream_health[stream_id]
                
                # Update metrics
                health.tr101290_metrics.sync_byte_errors += metrics.sync_byte_errors
                health.tr101290_metrics.continuity_errors += metrics.continuity_errors
                health.tr101290_metrics.transport_errors += metrics.transport_errors
                health.tr101290_metrics.last_updated = datetime.utcnow()
                
                # Check for alarms
                if metrics.sync_byte_errors > 0:
                    await self._raise_alarm(stream_id, "sync_byte_error", "Sync byte errors detected")
                if metrics.continuity_errors > 0:
                    await self._raise_alarm(stream_id, "continuity_error", "Continuity counter errors detected")
                
                # Store SCTE-35 events if detected
                if metrics.scte35_messages > 0:
                    event = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "event_type": "scte35_marker",
                        "segment_sequence": self.segment_counter.get(stream_id, 0),
                        "message_count": metrics.scte35_messages,
                        "pids": metrics.scte35_pids
                    }
                    
                    if stream_id not in self.scte35_events:
                        self.scte35_events[stream_id] = []
                    self.scte35_events[stream_id].append(event)
                    
                    # Keep only last 100 events
                    if len(self.scte35_events[stream_id]) > 100:
                        self.scte35_events[stream_id] = self.scte35_events[stream_id][-100:]
                    
                    # Update count
                    if stream_id in self.scte35_counts:
                        self.scte35_counts[stream_id] += metrics.scte35_messages
                    
                    # Broadcast SCTE-35 event
                    await self._broadcast_event(stream_id, "scte35_detected", event)
                    
                    logger.info(f"SCTE-35 detected in stream {stream_id}: {metrics.scte35_messages} messages")
                
                # Broadcast update
                await self._broadcast_event(stream_id, "health_update", health.dict())
                
        except Exception as e:
            logger.error(f"Error in TS analysis: {e}")

    async def _analyze_manifest_changes(self, stream_id: str, variants: List[VariantStream], segments: List[str]):
        """Analyze manifest for changes and errors."""
        try:
            last_state = self.last_manifest_state.get(stream_id, {})
            
            # Check Variant Count
            if "variant_count" in last_state:
                if last_state["variant_count"] != len(variants):
                    await self._raise_alarm(stream_id, "variant_count_changed", 
                        f"Variant count changed from {last_state['variant_count']} to {len(variants)}")
            
            # Update state
            self.last_manifest_state[stream_id] = {
                "variant_count": len(variants),
                "last_check": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error in manifest analysis: {e}")

    async def _raise_alarm(self, stream_id: str, alarm_type: str, description: str):
        """Raise a stream alarm."""
        # Implementation for raising alarms (simplified)
        await self._broadcast_event(stream_id, "alarm", {
            "type": alarm_type,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _broadcast_event(self, stream_id: str, event_type: str, data: dict):
        """Broadcast event via WebSocket."""
        message = {
            "type": event_type,
            "stream_id": stream_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await ws_manager.broadcast(stream_id, message)
    
    def _update_health_score(self, stream_id: str):
        """Compute and update the health score for a stream."""
        if stream_id not in self.stream_health:
            return
        
        health = self.stream_health[stream_id]
        
        # Get TR 101 290 metrics
        tr_metrics = health.tr101290_metrics
        
        # Calculate average TTFB from recent metrics
        ttfb_avg = 0.0
        download_ratio = 1.0
        if stream_id in self.metrics_history and self.metrics_history[stream_id]:
            recent = self.metrics_history[stream_id][-20:]  # Last 20 segments
            if recent:
                ttfb_avg = sum(m.ttfb for m in recent) / len(recent)
                # download_speed is in Mbps, compare with actual_bitrate
                avg_download = sum(m.download_speed for m in recent) / len(recent)
                avg_bitrate = sum(m.actual_bitrate for m in recent) / len(recent)
                if avg_bitrate > 0:
                    download_ratio = avg_download / avg_bitrate
        
        # Get error rate
        error_rate = health.error_rate_last_hour
        
        # Compute health score
        health_score = HealthScore.compute(
            error_rate=error_rate,
            continuity_errors=tr_metrics.continuity_errors,
            sync_errors=tr_metrics.sync_byte_errors,
            transport_errors=tr_metrics.transport_errors,
            ttfb_avg=ttfb_avg,
            download_ratio=min(download_ratio, 2.0),  # Cap at 2x
            manifest_errors=len(health.manifest_errors)
        )
        
        # Update health
        health.health_score = health_score
        health.last_updated = datetime.utcnow()
        
        # Add audio/video metrics if available
        if stream_id in self.audio_metrics:
            health.audio_metrics = self.audio_metrics[stream_id]
        if stream_id in self.video_metrics:
            video_metrics = self.video_metrics[stream_id]
            # Add SCTE-35 stats
            if stream_id in self.scte35_counts:
                video_metrics.scte35_count = self.scte35_counts[stream_id]
                video_metrics.scte35_detected = self.scte35_counts[stream_id] > 0
            health.video_metrics = video_metrics
        
        # Check thresholds and raise/resolve alerts
        alert_service.check_health_thresholds(
            stream_id=stream_id,
            health_score=health_score.score,
            error_rate=error_rate,
            continuity_errors=tr_metrics.continuity_errors,
            ttfb_avg=ttfb_avg,
            download_ratio=download_ratio
        )
        
        # Get active alerts for health status
        active_alerts = alert_service.get_active_alerts(stream_id)
        health.active_alerts = [
            AlertModel(
                alert_id=a.alert_id,
                stream_id=a.stream_id,
                alert_type=a.alert_type.value,
                severity=a.severity.value,
                message=a.message,
                timestamp=a.timestamp,
                metadata=a.metadata,
                acknowledged=a.acknowledged,
                resolved=a.resolved,
                resolved_at=a.resolved_at
            ) for a in active_alerts
        ]
    
    def get_stream_health(self, stream_id: str) -> Optional[StreamHealth]:
        """Get the current health status for a stream."""
        if stream_id not in self.stream_health:
            return None
        
        # Update health score before returning
        self._update_health_score(stream_id)
        return self.stream_health[stream_id]
    
    def get_metrics_history(self, stream_id: str, limit: int = 100) -> List[SegmentMetrics]:
        """Get recent metrics history for a stream."""
        if stream_id not in self.metrics_history:
            return []
        return self.metrics_history[stream_id][-limit:]
    
    def get_latest_thumbnail_path(self, stream_id: str) -> Optional[str]:
        """Get the path to the latest thumbnail for a stream."""
        return thumbnail_generator.get_cached_thumbnail(stream_id)


# Global instance
stream_monitor = StreamMonitor()

stream_monitor = StreamMonitor()
