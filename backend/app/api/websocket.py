from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/streams/{stream_id}")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    """WebSocket endpoint for real-time stream updates."""
    await ws_manager.connect(websocket, stream_id)
    
    try:
        # Send initial connection confirmation
        await ws_manager.send_personal(websocket, {
            "type": "connected",
            "stream_id": stream_id,
            "message": "Connected to stream updates"
        })
        
        # Keep connection alive and listen for messages
        while True:
            # Receive messages (for potential client commands)
            data = await websocket.receive_text()
            logger.debug(f"Received from client: {data}")
            
            # Echo back for keep-alive
            await ws_manager.send_personal(websocket, {
                "type": "pong",
                "stream_id": stream_id
            })
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, stream_id)
        logger.info(f"Client disconnected from stream {stream_id}")
    except Exception as e:
        logger.error(f"WebSocket error for stream {stream_id}: {e}")
        await ws_manager.disconnect(websocket, stream_id)
