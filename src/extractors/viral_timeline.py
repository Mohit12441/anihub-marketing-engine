import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Canonical climax timestamps (seconds into the episode) for top viral anime
# Sourced from high-engagement fight peaks (Domain Expansion, Boss fights, Awakenings)
ICONIC_CLIMAX_REGISTRY: Dict[str, Dict[str, Any]] = {
    "jujutsu-kaisen": {
        "start_sec": 1050,  # 17:30 - Sukuna vs Megumi / Curse climax battle
        "duration": 15,
        "hook": "BRO REALLY THOUGHT HE COULD BEAT HIM",
        "subtitles": [
            {"start": 0.0, "end": 2.5, "text": "Nobody expected this sudden power-up"},
            {"start": 2.5, "end": 5.5, "text": "The animation reached absolute peak cinema"},
            {"start": 5.5, "end": 9.0, "text": "He completely unleashed his domain expansion"},
            {"start": 9.0, "end": 12.0, "text": "Watch this full fight in 1080p Ultra HD"},
            {"start": 12.0, "end": 15.0, "text": "Link in bio to stream free on AniHub"}
        ]
    },
    "solo-leveling": {
        "start_sec": 980,   # 16:20 - Jinwoo Blood-Red Commander Igris Climax
        "duration": 15,
        "hook": "THE EXACT MOMENT HE BECAME THE MONARCH",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "Arise... the shadows have awoken"},
            {"start": 3.0, "end": 6.5, "text": "He single-handedly cleared the S-rank dungeon"},
            {"start": 6.5, "end": 10.0, "text": "From E-rank weakling to unstoppable god"},
            {"start": 10.0, "end": 13.0, "text": "Stream every episode free on AniHub Stream"},
            {"start": 13.0, "end": 15.0, "text": "Tap the link in bio right now"}
        ]
    },
    "demon-slayer-kimetsu-no-yaiba": {
        "start_sec": 1120,  # 18:40 - Hinokami Kagura Dance climax
        "duration": 15,
        "hook": "THIS FIGHT BROKE THE INTERNET WORLDWIDE",
        "subtitles": [
            {"start": 0.0, "end": 3.2, "text": "Ufotable spent the entire budget on this scene"},
            {"start": 3.2, "end": 6.8, "text": "Hinokami Kagura unleashed against Rui"},
            {"start": 6.8, "end": 10.5, "text": "The sound design gave everyone literal chills"},
            {"start": 10.5, "end": 13.0, "text": "Watch the complete series in 1080p HD"},
            {"start": 13.0, "end": 15.0, "text": "Available now free on AniHubStream"}
        ]
    },
    "chainsaw-man": {
        "start_sec": 1020,  # 17:00 - Denji Chainsaw rampage
        "duration": 15,
        "hook": "MAPPA WENT COMPLETELY UNHINGED HERE",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "He revved the engine and showed zero mercy"},
            {"start": 3.0, "end": 6.5, "text": "The bloodiest battle in modern anime history"},
            {"start": 6.5, "end": 10.0, "text": "Uncensored ultra quality animation"},
            {"start": 10.0, "end": 13.0, "text": "Stream full episodes free without ads"},
            {"start": 13.0, "end": 15.0, "text": "Click the link in bio to watch now"}
        ]
    }
}

class ViralTimelineDetector:
    """
    Intelligently identifies the most viral fight/climax scene timestamps
    for an anime instead of taking arbitrary slow dialogue intros.
    """

    @classmethod
    def find_viral_segment(cls, slug: str, mal_id: Optional[int] = None, duration: int = 15) -> Dict[str, Any]:
        """
        Returns optimal start_sec, duration, hook, and subtitle cues for maximum viral retention.
        """
        # 1. Check iconic registry first
        clean_slug = slug.lower().strip()
        for key, config in ICONIC_CLIMAX_REGISTRY.items():
            if key in clean_slug or clean_slug in key:
                logger.info(f"⚡ Matched curated viral climax for '{slug}' at {config['start_sec']}s (Act 3 Boss Climax)")
                return {
                    "start_sec": config["start_sec"],
                    "duration": duration or config["duration"],
                    "hook": config["hook"],
                    "subtitles": config["subtitles"]
                }

        # 2. AniSkip API: Skip opening recap/song and go directly to Act 3
        op_end = 120  # default 2:00
        if mal_id:
            try:
                url = f"https://api.aniskip.com/v2/skip-times/{mal_id}/1?types=op&types=recap"
                res = requests.get(url, timeout=3)
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    for r in results:
                        if r.get("skipType") == "op":
                            interval = r.get("interval", {})
                            op_end = int(interval.get("endTime", 120))
                            logger.info(f"AniSkip detected OP song ends at {op_end}s.")
                            break
            except Exception as e:
                logger.warning(f"AniSkip lookup skipped: {e}")

        # In standard 24-minute anime, the battle climax occurs between 14:00 (840s) and 18:30 (1110s)
        # Default to 960s (16:00), guaranteed deep into the action
        climax_start = max(op_end + 300, 960)
        logger.info(f"Targeting Act 3 Battle Climax at {climax_start}s for '{slug}'")

        generic_subtitles = [
            {"start": 0.0, "end": 3.0, "text": "Wait until you see how this scene concludes"},
            {"start": 3.0, "end": 6.5, "text": "The animation quality completely peaked right here"},
            {"start": 6.5, "end": 10.0, "text": "Nobody expected this insane level of sakuga"},
            {"start": 10.0, "end": 13.0, "text": "Watch the full 1080p episode in Sub & Dub"},
            {"start": 13.0, "end": 15.0, "text": "Stream free on AniHubStream • Link in Bio"}
        ]

        return {
            "start_sec": climax_start,
            "duration": duration,
            "hook": "THE ANIMATION REACHED ABSOLUTE PEAK HERE",
            "subtitles": generic_subtitles
        }
