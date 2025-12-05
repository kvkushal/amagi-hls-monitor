import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
from PIL import Image, ImageDraw, ImageFont
from app.config import settings

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """
    Thumbnail generator with caching support.
    
    Features:
    - FFmpeg-based thumbnail extraction
    - 30-60 second cache TTL
    - Error placeholder generation
    - Automatic cleanup of old thumbnails
    """
    
    # Cache TTL in seconds
    CACHE_TTL = 45  # 30-60 second range, use 45 as middle
    
    def __init__(self):
        self.thumbnails_dir = Path(settings.THUMBNAILS_DIR)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self.width = settings.THUMBNAIL_WIDTH
        self.height = settings.THUMBNAIL_HEIGHT
        
        # Cache: stream_id -> (thumbnail_path, timestamp, sequence)
        self._cache: Dict[str, Tuple[str, float, int]] = {}
        
        # Track all generated thumbnails for cleanup
        self._thumbnail_registry: Dict[str, Dict[int, Tuple[str, float]]] = {}  # stream_id -> {seq: (path, time)}
    
    def get_cached_thumbnail(self, stream_id: str) -> Optional[str]:
        """
        Get cached thumbnail for a stream if still valid.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            Path to cached thumbnail or None if cache expired/missing
        """
        if stream_id not in self._cache:
            return None
        
        path, cached_time, _ = self._cache[stream_id]
        
        # Check if cache is still valid
        if time.time() - cached_time < self.CACHE_TTL:
            if Path(path).exists():
                return path
        
        return None
    
    def get_latest_thumbnail_info(self, stream_id: str) -> Optional[Dict]:
        """
        Get information about the latest cached thumbnail.
        
        Returns:
            Dict with path, timestamp, sequence_number, or None
        """
        if stream_id not in self._cache:
            return None
        
        path, cached_time, sequence = self._cache[stream_id]
        
        if not Path(path).exists():
            return None
        
        return {
            "path": path,
            "cached_at": cached_time,
            "sequence_number": sequence,
            "expires_in": max(0, self.CACHE_TTL - (time.time() - cached_time)),
            "is_fresh": time.time() - cached_time < self.CACHE_TTL
        }
    
    async def extract_thumbnail(self, segment_path: str, output_path: str, 
                                timestamp: float = None) -> bool:
        """
        Extract a thumbnail from a segment file using FFmpeg.
        
        Args:
            segment_path: Path to the segment file
            output_path: Path where thumbnail should be saved
            timestamp: Timestamp in seconds (uses mid-point if None)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # If no timestamp, extract from middle
            if timestamp is None:
                # Get duration first
                duration = await self._get_duration(segment_path)
                if duration:
                    timestamp = duration / 2
                else:
                    timestamp = 0
            
            # FFmpeg command to extract frame
            command = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', segment_path,
                '-vframes', '1',
                '-vf', f'scale={self.width}:{self.height}',
                '-strict', 'unofficial',  # Allow non-standard YUV
                '-y',  # Overwrite
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.debug(f"Thumbnail generated: {output_path}")
                return True
            else:
                logger.warning(f"FFmpeg error for {segment_path}: {stderr.decode()[:200]}")
                return False
        
        except Exception as e:
            logger.error(f"Error extracting thumbnail: {e}")
            return False
    
    async def _get_duration(self, segment_path: str) -> Optional[float]:
        """Get duration of a video file using FFprobe."""
        try:
            command = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                segment_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode().strip()
                if not output or output == 'N/A':
                    return None
                return float(output)
            return None
        
        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return None
    
    def generate_error_thumbnail(self, output_path: str, error_message: str = "Decode Error"):
        """Generate a gray error placeholder thumbnail."""
        try:
            # Create gray image
            img = Image.new('RGB', (self.width, self.height), color='#4a5568')
            draw = ImageDraw.Draw(img)
            
            # Try to use a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Draw error icon (X)
            center_x, center_y = self.width // 2, self.height // 2
            draw.line([(center_x - 10, center_y - 10), (center_x + 10, center_y + 10)], 
                     fill='#e53e3e', width=3)
            draw.line([(center_x - 10, center_y + 10), (center_x + 10, center_y - 10)], 
                     fill='#e53e3e', width=3)
            
            # Draw text
            text_bbox = draw.textbbox((0, 0), error_message, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_x = (self.width - text_width) // 2
            draw.text((text_x, center_y + 20), error_message, fill='#ffffff', font=font)
            
            # Save
            img.save(output_path)
            logger.info(f"Error thumbnail generated: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error generating error thumbnail: {e}")
            return False
    
    async def generate_thumbnail_for_segment(self, stream_id: str, segment_uri: str, 
                                              segment_path: str, sequence: int) -> Optional[str]:
        """
        Generate thumbnail for a segment and return the path.
        Updates the cache with the new thumbnail.
        
        Args:
            stream_id: Stream identifier
            segment_uri: URI of the segment
            segment_path: Local path to downloaded segment
            sequence: Sequence number
        
        Returns:
            Path to thumbnail or None if failed
        """
        # Generate output filename
        filename = f"{stream_id}_{sequence}.jpg"
        output_path = str(self.thumbnails_dir / filename)
        
        # Try to extract thumbnail
        success = await self.extract_thumbnail(segment_path, output_path)
        
        if not success:
            # Generate error thumbnail
            self.generate_error_thumbnail(output_path, "No Video")
        
        # Update cache
        current_time = time.time()
        self._cache[stream_id] = (output_path, current_time, sequence)
        
        # Register thumbnail
        if stream_id not in self._thumbnail_registry:
            self._thumbnail_registry[stream_id] = {}
        self._thumbnail_registry[stream_id][sequence] = (output_path, current_time)
        
        # Cleanup old thumbnails for this stream (keep last 50)
        await self._cleanup_old_thumbnails(stream_id)
        
        return output_path
    
    async def _cleanup_old_thumbnails(self, stream_id: str, keep_count: int = 50):
        """Remove old thumbnails for a stream, keeping only the most recent ones."""
        if stream_id not in self._thumbnail_registry:
            return
        
        registry = self._thumbnail_registry[stream_id]
        
        if len(registry) <= keep_count:
            return
        
        # Sort by sequence number
        sorted_sequences = sorted(registry.keys())
        
        # Remove oldest thumbnails
        to_remove = sorted_sequences[:-keep_count]
        
        for seq in to_remove:
            path, _ = registry.pop(seq)
            try:
                file_path = Path(path)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Cleaned up old thumbnail: {path}")
            except Exception as e:
                logger.error(f"Error removing old thumbnail {path}: {e}")
    
    def cleanup_stream_thumbnails(self, stream_id: str):
        """Remove all thumbnails for a stream (call when stream is removed)."""
        try:
            # Remove from cache
            if stream_id in self._cache:
                del self._cache[stream_id]
            
            # Remove registered thumbnails
            if stream_id in self._thumbnail_registry:
                for seq, (path, _) in self._thumbnail_registry[stream_id].items():
                    try:
                        file_path = Path(path)
                        if file_path.exists():
                            file_path.unlink()
                    except:
                        pass
                del self._thumbnail_registry[stream_id]
            
            # Also scan directory for any matching files
            pattern = f"{stream_id}_*.jpg"
            for thumb_file in self.thumbnails_dir.glob(pattern):
                try:
                    thumb_file.unlink()
                except:
                    pass
            
            logger.info(f"Cleaned up all thumbnails for stream: {stream_id}")
        except Exception as e:
            logger.error(f"Error cleaning up thumbnails for {stream_id}: {e}")
    
    def get_thumbnail_url(self, stream_id: str, sequence: int) -> str:
        """Get the URL path for a thumbnail."""
        return f"/data/thumbnails/{stream_id}_{sequence}.jpg"


# Global instance
thumbnail_generator = ThumbnailGenerator()
