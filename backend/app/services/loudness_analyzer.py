import asyncio
import logging
import subprocess
from typing import Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class LoudnessAnalyzer:
    """Analyze loudness of audio segments using FFmpeg."""
    
    async def analyze_segment(self, segment_path: str) -> dict:
        """
        Analyze loudness of a segment file.
        
        Returns dict with momentary_lufs, shortterm_lufs, integrated_lufs,
        and rms_db (fallback). is_approximation flag indicates if using RMS.
        """
        try:
            # Try FFmpeg with ebur128 filter first
            loudness_data = await self._ffmpeg_ebur128(segment_path)
            
            if loudness_data:
                loudness_data['is_approximation'] = False
                return loudness_data
            
            # Fallback to RMS
            logger.warning("LUFS calculation failed, using RMS approximation")
            rms = await self._ffmpeg_rms(segment_path)
            
            return {
                'momentary_lufs': None,
                'shortterm_lufs': None,
                'integrated_lufs': None,
                'rms_db': rms,
                'is_approximation': True
            }
        
        except Exception as e:
            logger.error(f"Error analyzing loudness: {e}")
            return {
                'momentary_lufs': None,
                'shortterm_lufs': None,
                'integrated_lufs': None,
                'rms_db': None,
                'is_approximation': True
            }
    
    async def _ffmpeg_ebur128(self, segment_path: str) -> Optional[dict]:
        """Use FFmpeg ebur128 filter to get LUFS measurements."""
        try:
            command = [
                'ffmpeg',
                '-i', segment_path,
                '-filter:a', 'ebur128=peak=true',
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return None
            
            # Parse ebur128 output from stderr
            output = stderr.decode()
            
            loudness_data = {
                'momentary_lufs': None,
                'shortterm_lufs': None,
                'integrated_lufs': None
            }
            
            # Extract I (integrated), M (momentary), S (short-term)
            for line in output.split('\n'):
                if 'I:' in line:
                    try:
                        value = line.split('I:')[1].strip().split()[0]
                        loudness_data['integrated_lufs'] = float(value)
                    except:
                        pass
                elif 'M:' in line:
                    try:
                        value = line.split('M:')[1].strip().split()[0]
                        loudness_data['momentary_lufs'] = float(value)
                    except:
                        pass
                elif 'S:' in line:
                    try:
                        value = line.split('S:')[1].strip().split()[0]
                        loudness_data['shortterm_lufs'] = float(value)
                    except:
                        pass
            
            # Only return if we got at least one value
            if any(v is not None for v in loudness_data.values()):
                return loudness_data
            
            return None
        
        except Exception as e:
            logger.error(f"Error running ebur128: {e}")
            return None
    
    async def _ffmpeg_rms(self, segment_path: str) -> Optional[float]:
        """Fallback: Calculate RMS level."""
        try:
            command = [
                'ffmpeg',
                '-i', segment_path,
                '-af', 'volumedetect',
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            output = stderr.decode()
            
            # Parse mean_volume from output
            for line in output.split('\n'):
                if 'mean_volume:' in line:
                    try:
                        value = line.split('mean_volume:')[1].strip().split()[0]
                        return float(value)
                    except:
                        pass
            
            return None
        
        except Exception as e:
            logger.error(f"Error calculating RMS: {e}")
            return None


# Global instance
loudness_analyzer = LoudnessAnalyzer()
