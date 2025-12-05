from typing import Dict, Any
from datetime import datetime


class MetricsCalculator:
    """Calculate various metrics for segments."""
    
    @staticmethod
    def calculate_bitrate(segment_size_bytes: int, segment_duration_seconds: float) -> float:
        """
        Calculate actual bitrate in Mbps.
        
        bitrate = (size_in_bytes * 8) / duration_in_seconds / 1_000_000
        """
        if segment_duration_seconds <= 0:
            return 0.0
        
        bits = segment_size_bytes * 8
        bitrate_bps = bits / segment_duration_seconds
        bitrate_mbps = bitrate_bps / 1_000_000
        
        return round(bitrate_mbps, 3)
    
    @staticmethod
    def calculate_download_speed(segment_size_bytes: int, download_time_seconds: float) -> float:
        """
        Calculate download speed in Mbps.
        
        speed = (size_in_bytes * 8) / download_time_seconds / 1_000_000
        """
        if download_time_seconds <= 0:
            return 0.0
        
        bits = segment_size_bytes * 8
        speed_bps = bits / download_time_seconds
        speed_mbps = speed_bps / 1_000_000
        
        return round(speed_mbps, 3)
    
    @staticmethod
    def bytes_to_mb(size_bytes: int) -> float:
        """Convert bytes to megabytes."""
        return round(size_bytes / (1024 * 1024), 3)
    
    @staticmethod
    def calculate_all_metrics(segment_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all metrics for a segment.
        
        Input should have:
        - segment_size_bytes
        - segment_duration (seconds)
        - download_time (seconds)
        - ttfb (milliseconds)
        """
        size_bytes = segment_info.get('segment_size_bytes', 0)
        duration = segment_info.get('segment_duration', 0)
        download_time = segment_info.get('download_time', 0)
        ttfb = segment_info.get('ttfb', 0)
        
        return {
            'actual_bitrate': MetricsCalculator.calculate_bitrate(size_bytes, duration),
            'download_speed': MetricsCalculator.calculate_download_speed(size_bytes, download_time / 1000),  # Convert ms to s
            'segment_size_mb': MetricsCalculator.bytes_to_mb(size_bytes),
            'segment_size_bytes': size_bytes,
            'segment_duration': duration,
            'download_time': download_time,
            'ttfb': ttfb
        }


# Singleton instance
metrics_calculator = MetricsCalculator()
