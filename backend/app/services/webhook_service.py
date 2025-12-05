"""Webhook service for sending HTTP notifications on alerts."""
import aiohttp
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

WEBHOOKS_FILE = Path("data/webhooks.json")


@dataclass
class WebhookConfig:
    """Webhook configuration."""
    id: str
    name: str
    url: str
    enabled: bool = True
    events: List[str] = None  # List of event types to send, None = all
    headers: Dict[str, str] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = ["alert_raised", "alert_resolved", "stream_down", "stream_up"]
        if self.headers is None:
            self.headers = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class WebhookService:
    """Service for managing and sending webhooks."""
    
    def __init__(self):
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._load_webhooks()
    
    def _load_webhooks(self):
        """Load webhooks from file."""
        try:
            if WEBHOOKS_FILE.exists():
                with open(WEBHOOKS_FILE, 'r') as f:
                    data = json.load(f)
                    for wh in data.get("webhooks", []):
                        config = WebhookConfig(**wh)
                        self.webhooks[config.id] = config
                logger.info(f"Loaded {len(self.webhooks)} webhooks from persistence")
        except Exception as e:
            logger.error(f"Error loading webhooks: {e}")
    
    def _save_webhooks(self):
        """Save webhooks to file."""
        try:
            WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"webhooks": [asdict(wh) for wh in self.webhooks.values()]}
            with open(WEBHOOKS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving webhooks: {e}")
    
    async def start(self):
        """Initialize the webhook service."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        logger.info("WebhookService started")
    
    async def stop(self):
        """Cleanup the webhook service."""
        if self.session:
            await self.session.close()
        logger.info("WebhookService stopped")
    
    def add_webhook(self, config: WebhookConfig) -> WebhookConfig:
        """Add a new webhook configuration."""
        self.webhooks[config.id] = config
        self._save_webhooks()
        logger.info(f"Added webhook: {config.name} ({config.url})")
        return config
    
    def update_webhook(self, webhook_id: str, updates: Dict[str, Any]) -> Optional[WebhookConfig]:
        """Update an existing webhook."""
        if webhook_id not in self.webhooks:
            return None
        
        current = self.webhooks[webhook_id]
        for key, value in updates.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        self._save_webhooks()
        return current
    
    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook configuration."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            self._save_webhooks()
            logger.info(f"Deleted webhook: {webhook_id}")
            return True
        return False
    
    def get_webhooks(self) -> List[WebhookConfig]:
        """Get all webhook configurations."""
        return list(self.webhooks.values())
    
    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get a specific webhook configuration."""
        return self.webhooks.get(webhook_id)
    
    async def send_event(self, event_type: str, payload: Dict[str, Any]):
        """Send an event to all matching webhooks."""
        if not self.session:
            logger.warning("WebhookService not started, cannot send events")
            return
        
        tasks = []
        for webhook in self.webhooks.values():
            if not webhook.enabled:
                continue
            
            # Check if this webhook should receive this event type
            if webhook.events and event_type not in webhook.events:
                continue
            
            tasks.append(self._send_to_webhook(webhook, event_type, payload))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_webhook(self, webhook: WebhookConfig, event_type: str, payload: Dict[str, Any]):
        """Send payload to a single webhook."""
        try:
            data = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": payload
            }
            
            headers = {
                "Content-Type": "application/json",
                **webhook.headers
            }
            
            async with self.session.post(
                webhook.url,
                json=data,
                headers=headers
            ) as response:
                if response.status >= 400:
                    logger.warning(f"Webhook {webhook.name} returned {response.status}")
                else:
                    logger.debug(f"Webhook {webhook.name} delivered successfully")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Webhook {webhook.name} timed out")
        except Exception as e:
            logger.error(f"Error sending to webhook {webhook.name}: {e}")
    
    async def send_alert(self, alert_data: Dict[str, Any]):
        """Send an alert event to webhooks."""
        await self.send_event("alert_raised", alert_data)
    
    async def send_alert_resolved(self, alert_data: Dict[str, Any]):
        """Send an alert resolved event to webhooks."""
        await self.send_event("alert_resolved", alert_data)
    
    async def send_stream_status(self, stream_id: str, status: str, stream_name: str):
        """Send a stream status change event."""
        event_type = "stream_up" if status == "online" else "stream_down"
        await self.send_event(event_type, {
            "stream_id": stream_id,
            "stream_name": stream_name,
            "status": status
        })


# Global instance
webhook_service = WebhookService()
