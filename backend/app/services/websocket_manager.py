import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # stream_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, stream_id: str):
        """Accept and register a WebSocket connection for a stream."""
        await websocket.accept()
        async with self._lock:
            if stream_id not in self.active_connections:
                self.active_connections[stream_id] = set()
            self.active_connections[stream_id].add(websocket)
        logger.info(f"WebSocket connected to stream {stream_id}. Total: {len(self.active_connections[stream_id])}")
    
    async def disconnect(self, websocket: WebSocket, stream_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if stream_id in self.active_connections:
                self.active_connections[stream_id].discard(websocket)
                if not self.active_connections[stream_id]:
                    del self.active_connections[stream_id]
        logger.info(f"WebSocket disconnected from stream {stream_id}")
    
    async def broadcast(self, stream_id: str, message: dict):
        """Broadcast a message to all connections for a stream."""
        if stream_id not in self.active_connections:
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        message_str = json.dumps(message, default=str)
        
        disconnected = set()
        for connection in self.active_connections[stream_id]:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[stream_id] -= disconnected
                if not self.active_connections[stream_id]:
                    del self.active_connections[stream_id]
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific WebSocket connection."""
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        message_str = json.dumps(message, default=str)
        try:
            await websocket.send_text(message_str)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    def get_connection_count(self, stream_id: str) -> int:
        """Get the number of active connections for a stream."""
        return len(self.active_connections.get(stream_id, set()))
    
    def get_all_stream_ids(self) -> list:
        """Get all stream IDs with active connections."""
        return list(self.active_connections.keys())


# Global instance
ws_manager = WebSocketManager()
