import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TSMetrics:
    """MPEG-TS analysis metrics following TR 101 290 standards."""
    packet_count: int = 0
    sync_byte_errors: int = 0
    continuity_errors: int = 0
    transport_errors: int = 0
    pid_counts: Dict[int, int] = field(default_factory=dict)
    pcr_count: int = 0
    pcr_discontinuities: int = 0
    pat_errors: int = 0
    pmt_errors: int = 0
    null_packet_count: int = 0
    
    # Audio/Video specific
    video_pid: Optional[int] = None
    audio_pids: List[int] = field(default_factory=list)
    
    # SCTE-35 markers detected
    scte35_pids: List[int] = field(default_factory=list)
    scte35_messages: int = 0


@dataclass 
class ContinuityTracker:
    """Track continuity counter state per PID."""
    last_cc: int = -1
    error_count: int = 0
    packet_count: int = 0


class TSAnalyzer:
    """
    Enhanced MPEG-TS Analyzer for TR 101 290 compliance.
    
    Priority 1 Indicators:
    - TS_sync_loss: Sync byte (0x47) errors
    - Sync_byte_error: Invalid sync byte
    - Continuity_count_error: CC discontinuities
    
    Priority 2 Indicators:
    - Transport_error: TEI flag set
    - PCR_discontinuity_indicator_error
    """
    
    # Known PID types
    PID_PAT = 0x0000
    PID_CAT = 0x0001
    PID_TSDT = 0x0002
    PID_NULL = 0x1FFF
    
    # SCTE-35 stream type
    SCTE35_STREAM_TYPE = 0x86
    
    def __init__(self):
        # Per-PID continuity tracking: PID -> ContinuityTracker
        self.cc_trackers: Dict[int, ContinuityTracker] = {}
        
        # PCR tracking
        self.last_pcr: Dict[int, int] = {}  # PID -> last PCR value
        self.last_pcr_packet: Dict[int, int] = {}  # PID -> packet number at last PCR
    
    def reset(self):
        """Reset analyzer state for new stream."""
        self.cc_trackers.clear()
        self.last_pcr.clear()
        self.last_pcr_packet.clear()
    
    def analyze_segment(self, file_path: str) -> TSMetrics:
        """
        Analyze an MPEG-TS segment file.
        
        Args:
            file_path: Path to the .ts segment file
            
        Returns:
            TSMetrics with analysis results
        """
        metrics = TSMetrics()
        
        try:
            with open(file_path, 'rb') as f:
                packet_num = 0
                
                while True:
                    chunk = f.read(188)
                    if len(chunk) < 188:
                        break
                    
                    packet_num += 1
                    metrics.packet_count += 1
                    
                    # 1. Sync Byte Check (Priority 1)
                    if chunk[0] != 0x47:
                        metrics.sync_byte_errors += 1
                        continue
                    
                    # Parse TS Header (4 bytes)
                    header = self._parse_header(chunk)
                    
                    # 2. Transport Error Indicator Check (Priority 1)
                    if header['tei']:
                        metrics.transport_errors += 1
                    
                    # Track PID statistics
                    pid = header['pid']
                    metrics.pid_counts[pid] = metrics.pid_counts.get(pid, 0) + 1
                    
                    # Handle null packets
                    if pid == self.PID_NULL:
                        metrics.null_packet_count += 1
                        continue
                    
                    # 3. Continuity Counter Check (Priority 1)
                    if header['has_payload']:
                        cc_error = self._check_continuity(pid, header['cc'])
                        if cc_error:
                            metrics.continuity_errors += 1
                    
                    # 4. PAT Check (Priority 2)
                    if pid == self.PID_PAT:
                        if not self._validate_pat(chunk):
                            metrics.pat_errors += 1
                    
                    # 5. Check for adaptation field with PCR
                    if header['has_adaptation']:
                        pcr_result = self._check_pcr(chunk, pid, packet_num)
                        if pcr_result == 'pcr_found':
                            metrics.pcr_count += 1
                        elif pcr_result == 'pcr_discontinuity':
                            metrics.pcr_count += 1
                            metrics.pcr_discontinuities += 1
                    
                    # 6. Detect SCTE-35 PIDs
                    if self._is_scte35_packet(chunk, pid):
                        if pid not in metrics.scte35_pids:
                            metrics.scte35_pids.append(pid)
                        metrics.scte35_messages += 1
                    
        except Exception as e:
            logger.error(f"Error analyzing TS segment {file_path}: {e}")
        
        return metrics
    
    def _parse_header(self, packet: bytes) -> Dict:
        """Parse the 4-byte TS packet header."""
        byte1 = packet[1]
        byte2 = packet[2]
        byte3 = packet[3]
        
        return {
            'sync': packet[0],
            'tei': bool(byte1 & 0x80),  # Transport Error Indicator
            'pusi': bool(byte1 & 0x40),  # Payload Unit Start Indicator
            'priority': bool(byte1 & 0x20),  # Transport Priority
            'pid': ((byte1 & 0x1F) << 8) | byte2,  # 13-bit PID
            'scrambling': (byte3 & 0xC0) >> 6,  # Scrambling control
            'has_adaptation': bool(byte3 & 0x20),  # Adaptation field flag
            'has_payload': bool(byte3 & 0x10),  # Payload flag
            'cc': byte3 & 0x0F,  # 4-bit continuity counter
        }
    
    def _check_continuity(self, pid: int, cc: int) -> bool:
        """
        Check continuity counter for errors.
        
        Returns True if there's a continuity error.
        """
        if pid not in self.cc_trackers:
            self.cc_trackers[pid] = ContinuityTracker(last_cc=cc)
            return False
        
        tracker = self.cc_trackers[pid]
        tracker.packet_count += 1
        
        expected_cc = (tracker.last_cc + 1) % 16
        
        if cc != expected_cc:
            # Check for duplicate (same CC is allowed)
            if cc != tracker.last_cc:
                tracker.error_count += 1
                tracker.last_cc = cc
                return True
        
        tracker.last_cc = cc
        return False
    
    def _validate_pat(self, packet: bytes) -> bool:
        """Basic PAT validation."""
        try:
            # Check if PUSI is set (required for PAT)
            if not (packet[1] & 0x40):
                return True  # Not a start of PAT, ok
            
            # Find pointer field
            adaptation_length = 0
            if packet[3] & 0x20:  # Has adaptation field
                adaptation_length = packet[4] + 1
            
            payload_start = 4 + adaptation_length
            if payload_start >= 188:
                return False
            
            pointer = packet[payload_start]
            section_start = payload_start + 1 + pointer
            
            if section_start >= 188:
                return False
            
            # Check table ID (should be 0x00 for PAT)
            table_id = packet[section_start]
            return table_id == 0x00
            
        except Exception:
            return False
    
    def _check_pcr(self, packet: bytes, pid: int, packet_num: int) -> str:
        """
        Check for PCR in adaptation field.
        
        Returns:
            'no_pcr': No PCR found
            'pcr_found': PCR found, no discontinuity
            'pcr_discontinuity': PCR found with discontinuity
        """
        try:
            if not (packet[3] & 0x20):  # No adaptation field
                return 'no_pcr'
            
            adaptation_length = packet[4]
            if adaptation_length < 1:
                return 'no_pcr'
            
            adaptation_flags = packet[5]
            
            # Check PCR flag (bit 4)
            if not (adaptation_flags & 0x10):
                return 'no_pcr'
            
            # Extract PCR (6 bytes starting at packet[6])
            if adaptation_length < 7:
                return 'no_pcr'
            
            pcr_base = (
                (packet[6] << 25) |
                (packet[7] << 17) |
                (packet[8] << 9) |
                (packet[9] << 1) |
                ((packet[10] & 0x80) >> 7)
            )
            
            # Check for discontinuity
            is_discontinuity = False
            if pid in self.last_pcr:
                last_pcr = self.last_pcr[pid]
                last_packet = self.last_pcr_packet[pid]
                
                # PCR should increase by approximately 27MHz * segment_time
                # Check for large jump (> 2 seconds) or backwards
                pcr_diff = pcr_base - last_pcr
                packet_diff = packet_num - last_packet
                
                # Expected PCR increment per packet (roughly)
                # At 27MHz, 188 bytes, typical bitrate
                if pcr_diff < 0 or pcr_diff > 27000000 * 2:  # > 2 seconds
                    is_discontinuity = True
            
            self.last_pcr[pid] = pcr_base
            self.last_pcr_packet[pid] = packet_num
            
            return 'pcr_discontinuity' if is_discontinuity else 'pcr_found'
            
        except Exception:
            return 'no_pcr'
    
    def _is_scte35_packet(self, packet: bytes, pid: int) -> bool:
        """
        Basic SCTE-35 detection.
        
        SCTE-35 messages have specific patterns in payload.
        """
        try:
            # SCTE-35 packets start with specific table IDs
            # Check for splice_info_section (table_id = 0xFC)
            
            if not (packet[1] & 0x40):  # Not a start
                return False
            
            adaptation_length = 0
            if packet[3] & 0x20:
                adaptation_length = packet[4] + 1
            
            payload_start = 4 + adaptation_length
            if payload_start >= 187:
                return False
            
            pointer = packet[payload_start]
            section_start = payload_start + 1 + pointer
            
            if section_start >= 187:
                return False
            
            table_id = packet[section_start]
            
            # SCTE-35 table IDs
            return table_id == 0xFC
            
        except Exception:
            return False
    
    def get_continuity_summary(self) -> Dict[int, Dict]:
        """Get summary of continuity errors per PID."""
        summary = {}
        for pid, tracker in self.cc_trackers.items():
            summary[pid] = {
                'packets': tracker.packet_count,
                'errors': tracker.error_count,
                'error_rate': tracker.error_count / max(tracker.packet_count, 1) * 100
            }
        return summary


# Global instance
ts_analyzer = TSAnalyzer()
