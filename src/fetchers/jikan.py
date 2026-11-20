import logging
import requests
from typing import List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

JIKAN_BASE_URL = "https://api.jikan.moe/v4"

def fetch_today_airing_schedule() -> List[Dict[str, Any]]:
    """Fetches anime scheduled to air today based on current day of week."""
    day_name = datetime.now(timezone.utc).strftime("%A").lower()
    url = f"{JIKAN_BASE_URL}/schedules?filter={day_name}"
    
    logger.info(f"Querying Jikan API for schedule: {day_name.capitalize()}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        raw_items = data.get("data", [])
        
        results = []
        for item in raw_items:
            mal_id = item.get("mal_id")
            title = item.get("title_english") or item.get("title") or "Unknown"
            images = item.get("images", {}).get("jpg", {})
            cover = images.get("large_image_url") or images.get("image_url")
            score = item.get("score")
            broadcast = item.get("broadcast", {}).get("string", "Broadcasting today")
            
            results.append({
                "id": f"mal_{mal_id}",
                "title": title,
                "score": score,
                "cover_url": cover,
                "broadcast": broadcast,
                "genres": [g.get("name") for g in item.get("genres", [])]
            })
            
        logger.info(f"Successfully fetched {len(results)} scheduled anime from Jikan for {day_name}.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch Jikan schedule: {e}")
        return []
