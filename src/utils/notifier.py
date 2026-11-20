import logging
import requests
from typing import Optional
from ..config import Config

logger = logging.getLogger(__name__)

def send_notification(message: str, success: bool = True, details: Optional[str] = None):
    """Sends webhook notification to Discord channel for monitoring."""
    webhook_url = Config.DISCORD_WEBHOOK_URL
    if not webhook_url:
        logger.debug("No DISCORD_WEBHOOK_URL configured, skipping notification.")
        return

    icon = "✅" if success else "🚨"
    title = f"{icon} AniHub Marketing Engine Alert"
    
    payload = {
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": 3066993 if success else 15158332,
                "fields": [
                    {"name": "Details", "value": details[:1000] if details else "None"}
                ] if details else []
            }
        ]
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=8)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to deliver Discord webhook: {e}")
