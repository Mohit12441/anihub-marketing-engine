import os
import shutil
import logging
import subprocess
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..config import Config

logger = logging.getLogger(__name__)

def _get_ffmpeg_path() -> str:
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def _get_js_runtime_args() -> List[str]:
    """Detect available JS runtime (deno, node) for yt-dlp signature challenge resolution."""
    if shutil.which("deno"):
        return ["--js-runtimes", "deno"]
    if shutil.which("node"):
        return ["--js-runtimes", "node"]
    return []

class StreamRecorder:
    """
    Extracts real anime video clips with full audio and sound effects
    directly from stream sources, official trailers, or scene footage.
    """

    @staticmethod
    def _parse_seconds(time_str: str) -> int:
        try:
            parts = [int(p) for p in str(time_str).split(":")]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:
                return parts[0] * 60 + parts[1]
            elif len(parts) == 1:
                return parts[0]
            return 15
        except Exception:
            return 15

    @classmethod
    def fetch_anime_details(cls, anime_title: str) -> Dict[str, Any]:
        """Queries AniList GraphQL for the official title, 4K cover art, and trailer URL."""
        query = """
        query ($search: String) {
          Media(search: $search, type: ANIME) {
            id
            title { english romaji }
            coverImage { extraLarge large }
            bannerImage
            genres
            averageScore
            trailer { id site }
          }
        }
        """
        try:
            r = requests.post(
                "https://graphql.anilist.co",
                json={"query": query, "variables": {"search": anime_title}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=8
            )
            if r.status_code == 200:
                data = r.json().get("data", {}).get("Media", {})
                if data:
                    title_dict = data.get("title", {})
                    disp_title = title_dict.get("english") or title_dict.get("romaji") or anime_title
                    cover = data.get("coverImage", {}).get("extraLarge") or data.get("coverImage", {}).get("large")
                    trailer = data.get("trailer", {})
                    trailer_url = None
                    if trailer and trailer.get("site") == "youtube" and trailer.get("id"):
                        trailer_url = f"https://www.youtube.com/watch?v={trailer['id']}"
                    return {
                        "title": disp_title,
                        "cover_url": cover,
                        "score": data.get("averageScore", 88),
                        "genres": data.get("genres", ["Action", "Fantasy"]),
                        "trailer_url": trailer_url
                    }
        except Exception as e:
            logger.warning(f"AniList metadata lookup failed for '{anime_title}': {e}")

        return {
            "title": anime_title,
            "cover_url": None,
            "score": 90,
            "genres": ["Action", "Fantasy"],
            "trailer_url": None
        }

    @classmethod
    def get_real_anime_clip(
        cls,
        anime_title: str,
        stream_source: Optional[str] = None,
        start_time: str = "00:00:15",
        duration: int = 15,
        output_filename: Optional[str] = None
    ) -> Path:
        safe_title = "".join(c for c in anime_title if c.isalnum() or c in ("-", "_")).lower()[:18]
        if not output_filename:
            output_filename = f"raw_video_{safe_title}.mp4"
        out_path = Config.OUTPUT_DIR / output_filename

        ffmpeg_bin = _get_ffmpeg_path()
        js_args = _get_js_runtime_args()

        start_sec = cls._parse_seconds(start_time)
        end_sec = start_sec + duration
        section_str = f"*{start_sec}-{end_sec}"

        anime_details = cls.fetch_anime_details(anime_title)
        official_trailer = anime_details.get("trailer_url")

        # Base yt-dlp arguments
        base_dlp_opts = [
            "yt-dlp",
            "--download-sections", section_str,
            "-f", "bv*[height<=1080]+ba/b[height<=1080]/best",
            "--ffmpeg-location", ffmpeg_bin,
            "--extractor-args", "youtube:player_client=android,web",
            "--force-keyframes-at-cuts",
            "--no-check-certificates",
            *js_args
        ]

        # Priority 1: User-supplied stream source
        if stream_source:
            logger.info(f"Extracting live stream slice ({start_time} to +{duration}s) from: {stream_source}")
            cmd = [*base_dlp_opts, "-o", str(out_path), stream_source]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 10000:
                logger.info(f"Successfully sliced stream clip: {out_path}")
                return out_path
            logger.warning(f"Stream cut failed: {res.stderr[:200]}. Falling back...")

        # Priority 2: Official AniList trailer URL
        if official_trailer:
            logger.info(f"Downloading official video footage from AniList trailer: {official_trailer}")
            cmd = [*base_dlp_opts, "-o", str(out_path), official_trailer]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if out_path.exists() and out_path.stat().st_size > 10000:
                logger.info(f"Successfully downloaded official anime video: {out_path}")
                return out_path
            webm = Path(str(out_path) + ".webm")
            if webm.exists() and webm.stat().st_size > 10000:
                return webm
            logger.warning(f"Trailer download returned {res.returncode}: {res.stderr[:200]}. Trying search query...")

        # Priority 3: Search query
        search_query = f"ytsearch1:{anime_title} best fight scene"
        logger.info(f"Searching and downloading scene footage for '{anime_title}' with audio...")
        cmd = [*base_dlp_opts, "-o", str(out_path), search_query]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if out_path.exists() and out_path.stat().st_size > 10000:
            return out_path
        webm_fallback = Path(str(out_path) + ".webm")
        if webm_fallback.exists() and webm_fallback.stat().st_size > 10000:
            return webm_fallback

        matches = list(Config.OUTPUT_DIR.glob(f"raw_video_{safe_title}*"))
        if matches and matches[0].stat().st_size > 10000:
            return matches[0]

        # Priority 4: Cloud Runner Resilient Fallback (Never Crashes, Guaranteed Video + Audio)
        logger.warning(f"External video fetch restricted on this runner. Generating animated 9:16 reel with real audio...")
        from ..generators.video_builder import ReelVideoBuilder
        fallback_clip = ReelVideoBuilder.generate_reel(
            anime=anime_details,
            badge_text="TRENDING ANIME MOMENT",
            duration=duration,
            filename=output_filename
        )
        return fallback_clip
