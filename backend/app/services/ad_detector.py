import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.models import AdMarker

logger = logging.getLogger(__name__)


class AdDetector:
    """Detect ad insertion markers in HLS manifests."""
    
    def parse_manifest(self, manifest_content: str) -> List[AdMarker]:
        """
        Parse HLS manifest for ad markers.
        
        Looks for:
        - #EXT-X-DATERANGE (ad insertion)
        - #EXT-X-CUE-OUT / #EXT-X-CUE-IN (splice points)
        - Custom tags for bandwidth reservation
        """
        markers = []
        lines = manifest_content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Ad insertion via DATERANGE
            if line.startswith('#EXT-X-DATERANGE'):
                marker = self._parse_daterange(line)
                if marker:
                    markers.append(marker)
            
            # Splice out (ad break start)
            elif line.startswith('#EXT-X-CUE-OUT'):
                marker = self._parse_cue_out(line, i, lines)
                if marker:
                    markers.append(marker)
            
            # Splice in (ad break end)
            elif line.startswith('#EXT-X-CUE-IN'):
                marker = self._parse_cue_in(line, i, lines)
                if marker:
                    markers.append(marker)
            
            # Bandwidth reservation (custom detection)
            elif 'BANDWIDTH-RESERVATION' in line.upper():
                marker = AdMarker(
                    timestamp=datetime.utcnow(),
                    type="bandwidth_reservation",
                    duration=None,
                    metadata={"line": line}
                )
                markers.append(marker)
        
        return markers
    
    def _parse_daterange(self, line: str) -> AdMarker:
        """Parse #EXT-X-DATERANGE tag."""
        try:
            metadata = {}
            
            # Extract ID
            id_match = re.search(r'ID="([^"]+)"', line)
            if id_match:
                metadata['id'] = id_match.group(1)
            
            # Extract CLASS
            class_match = re.search(r'CLASS="([^"]+)"', line)
            if class_match:
                metadata['class'] = class_match.group(1)
            
            # Extract START-DATE
            start_match = re.search(r'START-DATE="([^"]+)"', line)
            timestamp = datetime.utcnow()
            if start_match:
                try:
                    timestamp = datetime.fromisoformat(start_match.group(1).replace('Z', '+00:00'))
                except:
                    pass
            
            # Extract DURATION
            duration = None
            duration_match = re.search(r'DURATION=([0-9.]+)', line)
            if duration_match:
                duration = float(duration_match.group(1))
            
            # Check if it's an ad
            marker_type = "ad_insertion"
            if metadata.get('class', '').upper() in ['AD', 'ADVERTISEMENT']:
                marker_type = "ad_insertion"
            
            return AdMarker(
                timestamp=timestamp,
                type=marker_type,
                duration=duration,
                metadata=metadata
            )
        
        except Exception as e:
            logger.error(f"Error parsing DATERANGE: {e}")
            return None
    
    def _parse_cue_out(self, line: str, index: int, lines: List[str]) -> AdMarker:
        """Parse #EXT-X-CUE-OUT tag."""
        try:
            duration = None
            
            # Try to extract duration
            duration_match = re.search(r'DURATION=([0-9.]+)', line)
            if duration_match:
                duration = float(duration_match.group(1))
            else:
                # Sometimes it's just a number after CUE-OUT:
                colon_match = re.search(r'CUE-OUT:([0-9.]+)', line)
                if colon_match:
                    duration = float(colon_match.group(1))
            
            return AdMarker(
                timestamp=datetime.utcnow(),
                type="splice_null",
                duration=duration,
                metadata={"direction": "out", "line": line}
            )
        
        except Exception as e:
            logger.error(f"Error parsing CUE-OUT: {e}")
            return None
    
    def _parse_cue_in(self, line: str, index: int, lines: List[str]) -> AdMarker:
        """Parse #EXT-X-CUE-IN tag."""
        try:
            return AdMarker(
                timestamp=datetime.utcnow(),
                type="splice_null",
                duration=None,
                metadata={"direction": "in", "line": line}
            )
        
        except Exception as e:
            logger.error(f"Error parsing CUE-IN: {e}")
            return None


# Global instance
ad_detector = AdDetector()
