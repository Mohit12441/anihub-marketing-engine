import re
from typing import Dict, Any, Optional
from ..config import Config

def clean_slug(title: str) -> str:
    """Converts anime title into an SEO-friendly URL slug for anihubstream.com."""
    cleaned = re.sub(r"[^\w\s-]", "", title).strip().lower()
    return re.sub(r"[-\s]+", "-", cleaned)

class ContentCopywriter:
    """Generates engaging social copy tailored for Instagram and Twitter."""

    @staticmethod
    def generate_copy(anime: Dict[str, Any], post_type: str = "trending") -> Dict[str, str]:
        title = anime["title"]
        slug = clean_slug(title)
        site_url = Config.SITE_BASE_URL
        watch_url = f"{site_url}/watch/{slug}?utm_source=social&utm_medium=auto_promo"
        score = anime.get("score")
        score_text = f"⭐ Rated {score}/100" if score else "🔥 Trending Now"
        genres = anime.get("genres", [])
        genre_tags = " ".join([f"#{g.replace(' ', '').replace('-', '')}" for g in genres[:4]]) if genres else "#Anime"

        # 1. Twitter Copy (Must fit comfortably under 280 chars)
        twitter_text = (
            f"⚡ Trending Alert: {title}\n"
            f"{score_text}\n\n"
            f"Stream full episodes in 1080p HD Sub/Dub with zero lag on {Config.SITE_NAME}!\n\n"
            f"🍿 Watch Now: {watch_url}\n"
            f"#Anime {genre_tags}"
        )
        if len(twitter_text) > 275:
            # Shorten if long title
            twitter_text = (
                f"⚡ Trending: {title[:40]}...\n"
                f"Stream 1080p Sub/Dub free on {Config.SITE_NAME}!\n\n"
                f"🍿 {watch_url}\n"
                f"#Anime #Otaku"
            )

        # 2. Instagram Copy (Rich formatting, line breaks, bio CTA & hashtags)
        ig_text = (
            f"🚨 MUST-WATCH ANIME SPOTLIGHT: {title} 🚨\n\n"
            f"Looking for your next obsession? {title} is currently dominating the charts! ({score_text})\n\n"
            f"✨ Why stream on {Config.SITE_NAME}?\n"
            f"✔️ Crystal-clear 1080p Ultra HD\n"
            f"✔️ Fast English Sub & Dub streams\n"
            f"✔️ Smooth playback & zero intrusive popups\n\n"
            f"🔗 DIRECT LINK IN BIO or visit:\n"
            f"👉 {watch_url}\n\n"
            f"---\n"
            f"Drop a comment if you've already started watching this! 👇\n\n"
            f"#anime #{slug.replace('-', '')} #animerecommendation #anihubstream "
            f"#animestreaming #otaku #animeedit #animelover {genre_tags}"
        )

        return {
            "title": title,
            "slug": slug,
            "watch_url": watch_url,
            "twitter_text": twitter_text,
            "instagram_text": ig_text
        }
