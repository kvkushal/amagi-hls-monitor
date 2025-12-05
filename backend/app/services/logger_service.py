import logging
import json
import gzip
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import asyncio
import aiofiles
from app.config import settings

logger = logging.getLogger(__name__)


class LoggerService:
    """
    Per-stream daily logging service with midnight rotation.
    
    Features:
    - Separate log files per stream
    - Daily rotation at midnight local time
    - Automatic compression of old logs
    - Clean, readable JSON formatting
    """
    
    def __init__(self):
        self.logs_dir = Path(settings.LOGS_DIR)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._file_locks: Dict[str, asyncio.Lock] = {}
        self._last_rotation_check = None
        self._local_tz = datetime.now().astimezone().tzinfo
    
    def _get_stream_log_dir(self, stream_id: str) -> Path:
        """Get log directory for a specific stream."""
        stream_dir = self.logs_dir / stream_id
        stream_dir.mkdir(parents=True, exist_ok=True)
        return stream_dir
    
    def _get_log_filename(self, date: datetime, stream_id: Optional[str] = None) -> Path:
        """Get log filename for a specific date and optionally a stream."""
        if stream_id:
            return self._get_stream_log_dir(stream_id) / f"{date.strftime('%Y-%m-%d')}.log"
        return self.logs_dir / f"{date.strftime('%Y-%m-%d')}.log"
    
    def _get_file_lock(self, filepath: str) -> asyncio.Lock:
        """Get or create a lock for a specific file."""
        if filepath not in self._file_locks:
            self._file_locks[filepath] = asyncio.Lock()
        return self._file_locks[filepath]
    
    async def write_event(self, event_data: Dict[str, Any], stream_id: Optional[str] = None):
        """
        Write an event to the appropriate log file.
        
        Args:
            event_data: Event data to log
            stream_id: Optional stream ID for per-stream logging
        """
        now = datetime.now(self._local_tz)
        
        # Add timestamp if not present (in ISO format with timezone)
        if "timestamp" not in event_data:
            event_data["timestamp"] = now.isoformat()
        
        # Add stream_id to event if provided
        if stream_id and "stream_id" not in event_data:
            event_data["stream_id"] = stream_id
        
        # Determine log file (per-stream or global)
        if stream_id:
            log_file = self._get_log_filename(now, stream_id)
        else:
            log_file = self._get_log_filename(now)
        
        # Format as clean JSON line
        log_line = json.dumps(event_data, default=str, ensure_ascii=False) + "\n"
        
        # Get lock for this file
        lock = self._get_file_lock(str(log_file))
        
        async with lock:
            try:
                async with aiofiles.open(log_file, mode='a', encoding='utf-8') as f:
                    await f.write(log_line)
            except Exception as e:
                logger.error(f"Failed to write to log file {log_file}: {e}")
        
        # Also write to global log for aggregated view
        if stream_id:
            await self._write_to_global_log(event_data, now)
    
    async def _write_to_global_log(self, event_data: Dict[str, Any], now: datetime):
        """Write event to global log file (for aggregated view)."""
        log_file = self._get_log_filename(now)
        log_line = json.dumps(event_data, default=str, ensure_ascii=False) + "\n"
        
        lock = self._get_file_lock(str(log_file))
        
        async with lock:
            try:
                async with aiofiles.open(log_file, mode='a', encoding='utf-8') as f:
                    await f.write(log_line)
            except Exception as e:
                logger.error(f"Failed to write to global log file {log_file}: {e}")
    
    async def write_stream_event(self, stream_id: str, event_type: str, message: str, 
                                  severity: str = "info", metadata: Optional[Dict] = None):
        """
        Convenience method to write a structured stream event.
        
        Args:
            stream_id: Stream identifier
            event_type: Type of event (e.g., 'segment_downloaded', 'error', 'warning')
            message: Human-readable message
            severity: Event severity (info, warning, error)
            metadata: Additional event metadata
        """
        event = {
            "stream_id": stream_id,
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "metadata": metadata or {}
        }
        await self.write_event(event, stream_id)
    
    async def rotate_logs(self):
        """
        Check and rotate logs if needed.
        Runs at midnight local time.
        """
        now = datetime.now(self._local_tz)
        
        # Compress old logs
        await self._compress_old_logs(now)
        
        # Delete very old logs
        await self._delete_old_logs(now)
        
        logger.info(f"Log rotation completed at {now.isoformat()}")
    
    async def _compress_old_logs(self, now: datetime):
        """Compress logs older than LOG_COMPRESS_DAYS."""
        compress_before = now - timedelta(days=settings.LOG_COMPRESS_DAYS)
        
        # Compress global logs
        for log_file in self.logs_dir.glob("*.log"):
            await self._try_compress_file(log_file, compress_before)
        
        # Compress per-stream logs
        for stream_dir in self.logs_dir.iterdir():
            if stream_dir.is_dir():
                for log_file in stream_dir.glob("*.log"):
                    await self._try_compress_file(log_file, compress_before)
    
    async def _try_compress_file(self, log_file: Path, compress_before: datetime):
        """Try to compress a single log file if it's old enough."""
        try:
            # Parse date from filename
            date_str = log_file.stem
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            file_date = file_date.replace(tzinfo=self._local_tz)
            
            if file_date < compress_before:
                gz_file = log_file.with_suffix('.log.gz')
                if not gz_file.exists():
                    logger.info(f"Compressing log file: {log_file}")
                    async with aiofiles.open(log_file, 'rb') as f_in:
                        content = await f_in.read()
                    
                    with gzip.open(gz_file, 'wb') as f_out:
                        f_out.write(content)
                    
                    # Delete original
                    log_file.unlink()
                    logger.info(f"Compressed and deleted: {log_file}")
        except Exception as e:
            logger.error(f"Error compressing log file {log_file}: {e}")
    
    async def _delete_old_logs(self, now: datetime):
        """Delete logs older than LOG_DELETE_DAYS."""
        delete_before = now - timedelta(days=settings.LOG_DELETE_DAYS)
        
        # Delete global logs
        for log_file in self.logs_dir.glob("*.log*"):
            await self._try_delete_file(log_file, delete_before)
        
        # Delete per-stream logs
        for stream_dir in self.logs_dir.iterdir():
            if stream_dir.is_dir():
                for log_file in stream_dir.glob("*.log*"):
                    await self._try_delete_file(log_file, delete_before)
                
                # Remove empty directories
                try:
                    if not any(stream_dir.iterdir()):
                        stream_dir.rmdir()
                except:
                    pass
    
    async def _try_delete_file(self, log_file: Path, delete_before: datetime):
        """Try to delete a single log file if it's old enough."""
        try:
            # Parse date from filename
            date_str = log_file.stem.replace('.log', '')
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            file_date = file_date.replace(tzinfo=self._local_tz)
            
            if file_date < delete_before:
                logger.info(f"Deleting old log file: {log_file}")
                log_file.unlink()
        except Exception as e:
            logger.error(f"Error deleting log file {log_file}: {e}")
    
    async def read_events(self, start_date: datetime, end_date: datetime, 
                          stream_id: Optional[str] = None, event_type: Optional[str] = None,
                          limit: int = 1000) -> List[Dict]:
        """
        Read events from log files within a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            stream_id: Optional filter by stream ID
            event_type: Optional filter by event type
            limit: Maximum number of events to return
        """
        events = []
        current = start_date
        
        while current <= end_date:
            # Try per-stream log first if stream_id specified
            if stream_id:
                log_file = self._get_log_filename(current, stream_id)
                if log_file.exists():
                    events.extend(await self._read_log_file(log_file, stream_id, event_type, limit - len(events)))
                
                gz_file = log_file.with_suffix('.log.gz')
                if gz_file.exists():
                    events.extend(await self._read_gz_log_file(gz_file, stream_id, event_type, limit - len(events)))
            else:
                # Read from global log
                log_file = self._get_log_filename(current)
                if log_file.exists():
                    events.extend(await self._read_log_file(log_file, stream_id, event_type, limit - len(events)))
                
                gz_file = log_file.with_suffix('.log.gz')
                if gz_file.exists():
                    events.extend(await self._read_gz_log_file(gz_file, stream_id, event_type, limit - len(events)))
            
            if len(events) >= limit:
                break
            
            current += timedelta(days=1)
        
        return events[:limit]
    
    async def read_stream_logs(self, stream_id: str, limit: int = 500) -> List[Dict]:
        """
        Read recent logs for a specific stream.
        
        Args:
            stream_id: Stream identifier
            limit: Maximum number of events
        """
        now = datetime.now(self._local_tz)
        start = now - timedelta(days=7)  # Last 7 days
        return await self.read_events(start, now, stream_id=stream_id, limit=limit)
    
    async def _read_log_file(self, log_file: Path, stream_id: Optional[str], 
                             event_type: Optional[str], limit: int) -> List[Dict]:
        """Read events from a plain log file."""
        events = []
        try:
            async with aiofiles.open(log_file, mode='r', encoding='utf-8') as f:
                async for line in f:
                    if len(events) >= limit:
                        break
                    try:
                        event = json.loads(line.strip())
                        if self._matches_filter(event, stream_id, event_type):
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
        
        return events
    
    async def _read_gz_log_file(self, gz_file: Path, stream_id: Optional[str], 
                                 event_type: Optional[str], limit: int) -> List[Dict]:
        """Read events from a gzipped log file."""
        events = []
        try:
            with gzip.open(gz_file, 'rt', encoding='utf-8') as f:
                for line in f:
                    if len(events) >= limit:
                        break
                    try:
                        event = json.loads(line.strip())
                        if self._matches_filter(event, stream_id, event_type):
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading gz log file {gz_file}: {e}")
        
        return events
    
    def _matches_filter(self, event: dict, stream_id: Optional[str], event_type: Optional[str]) -> bool:
        """Check if event matches filter criteria."""
        if stream_id and event.get("stream_id") != stream_id:
            return False
        if event_type and event.get("event_type") != event_type:
            return False
        return True
    
    def cleanup_stream_logs(self, stream_id: str):
        """Remove all log files for a stream (call when stream is deleted)."""
        try:
            stream_dir = self._get_stream_log_dir(stream_id)
            if stream_dir.exists():
                for log_file in stream_dir.glob("*"):
                    log_file.unlink()
                stream_dir.rmdir()
                logger.info(f"Cleaned up logs for stream: {stream_id}")
        except Exception as e:
            logger.error(f"Error cleaning up logs for stream {stream_id}: {e}")


# Global instance
log_service = LoggerService()
