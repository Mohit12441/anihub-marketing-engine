import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"

AIRING_SCHEDULE_QUERY = """
query ($airingAtGreater: Int, $airingAtLesser: Int) {
  Page(page: 1, perPage: 15) {
    airingSchedules(airingAt_greater: $airingAtGreater, airingAt_lesser: $airingAtLesser, sort: TIME) {
      id
      episode
      airingAt
      media {
        id
        title {
          romaji
          english
        }
        coverImage {
          extraLarge
          large
        }
        genres
        averageScore
      }
    }
  }
}
"""

def fetch_today_airing_anilist() -> List[Dict[str, Any]]:
    """Fetches anime airing today using AniList's ultra-reliable GraphQL CDN."""
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    start_of_day = now - (now % 86400)
    end_of_day = start_of_day + 86400

    logger.info("Querying AniList GraphQL API for today's airing schedule...")
    try:
        response = requests.post(
            ANILIST_GRAPHQL_URL,
            json={
                "query": AIRING_SCHEDULE_QUERY,
                "variables": {"airingAtGreater": start_of_day, "airingAtLesser": end_of_day}
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        schedules = data.get("data", {}).get("Page", {}).get("airingSchedules", [])

        results = []
        for item in schedules:
            media = item.get("media", {})
            title_dict = media.get("title", {})
            title = title_dict.get("english") or title_dict.get("romaji") or "Unknown Anime"
            cover = media.get("coverImage", {}).get("extraLarge") or media.get("coverImage", {}).get("large")

            results.append({
                "id": str(media.get("id")),
                "title": title,
                "score": media.get("averageScore", 0),
                "genres": media.get("genres", []),
                "cover_url": cover,
                "next_episode": item.get("episode"),
                "status": "RELEASING"
            })
        logger.info(f"Successfully fetched {len(results)} today-airing anime records from AniList.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch AniList airing schedule: {e}")
        return []

TRENDING_QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(type: ANIME, sort: TRENDING_DESC, status_in: [RELEASING, NOT_YET_RELEASED]) {
      id
      title {
        romaji
        english
        native
      }
      coverImage {
        extraLarge
        large
      }
      bannerImage
      genres
      averageScore
      popularity
      status
      nextAiringEpisode {
        episode
        timeUntilAiring
      }
    }
  }
}
"""

def fetch_trending_anime(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches top trending anime currently releasing on AniList."""
    variables = {
        "page": 1,
        "perPage": limit
    }
    logger.info(f"Querying AniList GraphQL API for top {limit} trending anime...")
    try:
        response = requests.post(
            ANILIST_GRAPHQL_URL,
            json={"query": TRENDING_QUERY, "variables": variables},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        raw_items = data.get("data", {}).get("Page", {}).get("media", [])
        
        results = []
        for item in raw_items:
            title_dict = item.get("title", {})
            title = title_dict.get("english") or title_dict.get("romaji") or title_dict.get("native") or "Unknown Anime"
            cover = item.get("coverImage", {}).get("extraLarge") or item.get("coverImage", {}).get("large")
            
            next_ep = item.get("nextAiringEpisode")
            ep_num = next_ep.get("episode") if next_ep else None
            
            results.append({
                "id": str(item.get("id")),
                "title": title,
                "score": item.get("averageScore", 0),
                "genres": item.get("genres", []),
                "cover_url": cover,
                "next_episode": ep_num,
                "status": item.get("status")
            })
            
        logger.info(f"Successfully fetched {len(results)} trending anime records from AniList.")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch AniList trending data: {e}")
        return []
