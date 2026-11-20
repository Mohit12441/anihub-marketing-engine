import re
from typing import Dict, Any, List
from ..config import Config

class ViralSEOGenerator:
    """Generates viral social media hooks, SEO descriptions, hashtags, and deep links."""

    VIRAL_HOOKS = [
        "Bro really thought he could win 💀🔥",
        "Wait for the animation to peak at the end 😱",
        "This is why this anime is dominating 2026 👑",
        "He didn't have to violate him like that 😭",
        "Top 1 anime moments of the season 🔥",
        "Nobody expected this power-up ⚡"
    ]

    @classmethod
    def generate_seo_package(cls, anime_title: str, scene_type: str = "hype") -> Dict[str, Any]:
        slug = re.sub(r"[^\w\s-]", "", anime_title).strip().lower()
        slug = re.sub(r"[-\s]+", "-", slug)
        watch_url = f"{Config.SITE_BASE_URL}/watch/{slug}?utm_source=viral_shorts&utm_medium=video_clip"

        hook = cls.VIRAL_HOOKS[hash(anime_title) % len(cls.VIRAL_HOOKS)]

        # YouTube Shorts & TikTok Title (<75 characters)
        yt_title = f"{hook} | {anime_title} #shorts"
        if len(yt_title) > 95:
            yt_title = f"{hook[:45]}... | {anime_title[:25]} #shorts"

        # TikTok & Reels Caption
        caption = (
            f"{hook}\n\n"
            f"Anime: {anime_title}\n"
            f"🍿 Watch the full episode in 1080p Ultra HD (English Sub & Dub) on {Config.SITE_NAME}!\n\n"
            f"🔗 Link in bio to stream free: {watch_url}\n\n"
            f"#anime #animemoments #{slug.replace('-', '')} #animereels #animetiktok "
            f"#animescene #otaku #animefight #anihubstream #animeedit"
        )

        # YouTube Tags (Comma separated)
        tags = [
            anime_title,
            f"{anime_title} clip",
            f"{anime_title} fight",
            f"{anime_title} best moments",
            f"{anime_title} episode 1",
            "anime shorts",
            "viral anime",
            "anime edit 4k",
            "anihub stream",
            "watch anime free",
            "top anime 2026"
        ]

        return {
            "title": yt_title,
            "hook": hook,
            "caption": caption,
            "tags": ", ".join(tags),
            "watch_url": watch_url,
            "slug": slug
        }
