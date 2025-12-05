"""Webhooks API for managing webhook configurations."""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.services.webhook_service import webhook_service, WebhookConfig

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookCreate(BaseModel):
    """Create webhook request."""
    name: str
    url: str
    enabled: bool = True
    events: Optional[List[str]] = None
    headers: Optional[dict] = None


class WebhookUpdate(BaseModel):
    """Update webhook request."""
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    events: Optional[List[str]] = None
    headers: Optional[dict] = None


class WebhookResponse(BaseModel):
    """Webhook response."""
    id: str
    name: str
    url: str
    enabled: bool
    events: List[str]
    headers: dict
    created_at: str


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks():
    """List all webhook configurations."""
    webhooks = webhook_service.get_webhooks()
    return [
        WebhookResponse(
            id=wh.id,
            name=wh.name,
            url=wh.url,
            enabled=wh.enabled,
            events=wh.events or [],
            headers=wh.headers or {},
            created_at=wh.created_at
        )
        for wh in webhooks
    ]


@router.post("", response_model=WebhookResponse)
async def create_webhook(webhook: WebhookCreate):
    """Create a new webhook configuration."""
    config = WebhookConfig(
        id=str(uuid.uuid4())[:8],
        name=webhook.name,
        url=webhook.url,
        enabled=webhook.enabled,
        events=webhook.events,
        headers=webhook.headers,
        created_at=datetime.utcnow().isoformat()
    )
    
    created = webhook_service.add_webhook(config)
    
    return WebhookResponse(
        id=created.id,
        name=created.name,
        url=created.url,
        enabled=created.enabled,
        events=created.events or [],
        headers=created.headers or {},
        created_at=created.created_at
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: str):
    """Get a specific webhook configuration."""
    webhook = webhook_service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        enabled=webhook.enabled,
        events=webhook.events or [],
        headers=webhook.headers or {},
        created_at=webhook.created_at
    )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(webhook_id: str, updates: WebhookUpdate):
    """Update a webhook configuration."""
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    updated = webhook_service.update_webhook(webhook_id, update_dict)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return WebhookResponse(
        id=updated.id,
        name=updated.name,
        url=updated.url,
        enabled=updated.enabled,
        events=updated.events or [],
        headers=updated.headers or {},
        created_at=updated.created_at
    )


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook configuration."""
    if not webhook_service.delete_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Send a test event to a webhook."""
    webhook = webhook_service.get_webhook(webhook_id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Send test event
    await webhook_service._send_to_webhook(webhook, "test", {
        "message": "This is a test webhook from HLS Monitor",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"status": "test_sent"}
