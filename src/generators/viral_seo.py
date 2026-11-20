import re
from typing import Dict, Any, List
from ..config import Config

class ViralSEOGenerator:
    """Generates viral social media hooks, SEO descriptions, hashtags, and deep links."""

    HOOK_TEMPLATES = [
        "Wait for the animation to peak at the end 😱",
        "Bro really thought he had a chance against him 💀",
        "This fight broke the internet for a reason 🔥",
        "The studio went completely unhinged on this scene ⚡",
        "Top 1 anime moments that gave everyone chills 🥶",
        "Nobody was prepared for this sudden power-up 👑"
    ]

    @classmethod
    def generate_seo_package(cls, anime_title: str) -> Dict[str, Any]:
        slug = re.sub(r"[^\w\s-]", "", anime_title).strip().lower()
        slug = re.sub(r"[-\s]+", "-", slug)
        watch_url = f"{Config.SITE_BASE_URL}/watch/{slug}?utm_source=viral_shorts&utm_medium=video_clip"

        hook = cls.HOOK_TEMPLATES[hash(anime_title) % len(cls.HOOK_TEMPLATES)]

        # 1. High-CTR Titles
        title_a = f"{hook} | {anime_title} #shorts"
        title_b = f"This scene in {anime_title} is absolute peak cinema 🔥 #anime"
        title_c = f"Did he really just do that?! 😱 | {anime_title} Fight Scene"

        # 2. Rich Social Media Caption
        caption = (
            f"🎬 Anime: {anime_title}\n"
            f"🔥 Scene: Uncensored Peak Action Highlight\n\n"
            f"{hook}\n\n"
            f"Want to watch the entire series with zero ads & ultra-fast playback?\n"
            f"🍿 Stream in 1080p Ultra HD English Sub & Dub on {Config.SITE_NAME}:\n"
            f"👉 {watch_url}\n\n"
            f"🔗 Link is also in our bio for direct mobile access!\n\n"
            f"👇 Who is your favorite character in this anime? Drop a comment below!\n\n"
            f"#anime #animetiktok #animereels #animemoments #{slug.replace('-', '')} "
            f"#animescene #animefight #otaku #animeedit #anihubstream #foryou #fyp"
        )

        # 3. 25+ High Ranking SEO Tags
        tags = [
            anime_title,
            f"{anime_title} episode 1",
            f"{anime_title} full fight",
            f"{anime_title} season 2",
            f"{anime_title} english dub",
            f"{anime_title} english sub",
            f"{anime_title} best moments",
            f"{anime_title} 4k 60fps",
            "anime shorts",
            "viral anime clips",
            "anime fight scene",
            "top anime 2026",
            "anime edit tiktok",
            "anihub stream",
            "watch anime online free 1080p",
            "anitok",
            "best anime fights",
            "anime reaction"
        ]

        # 4. Pinned Comment Template
        pinned_comment = (
            f"🍿 Watch {anime_title} & 5,000+ anime in 1080p HD Sub/Dub completely free on {Config.SITE_NAME}!\n"
            f"👉 Link in bio or visit: {watch_url}"
        )

        return {
            "hook": hook,
            "title_primary": title_a,
            "title_alt_1": title_b,
            "title_alt_2": title_c,
            "caption": caption,
            "tags": ", ".join(tags),
            "pinned_comment": pinned_comment,
            "watch_url": watch_url,
            "slug": slug
        }
