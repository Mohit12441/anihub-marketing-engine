import os
import re
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
    directly from AniHubStream site streaming providers, direct stream URLs, or official trailers.
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
        clean_name = anime_title
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
                    
                    anilist_id = data.get("id")
                    canonical_slug = re.sub(r'[^a-z0-9]+', '-', disp_title.lower()).strip('-')

                    return {
                        "id": anilist_id,
                        "slug": canonical_slug,
                        "title": disp_title,
                        "cover_url": cover,
                        "score": data.get("averageScore", 88),
                        "genres": data.get("genres", ["Action", "Fantasy"]),
                        "trailer_url": trailer_url
                    }
        except Exception as e:
            logger.warning(f"AniList metadata lookup failed for '{anime_title}': {e}")

        fallback_slug = re.sub(r'[^a-z0-9]+', '-', anime_title.lower()).strip('-')
        return {
            "id": None,
            "slug": fallback_slug,
            "title": anime_title,
            "cover_url": None,
            "score": 90,
            "genres": ["Action", "Fantasy"],
            "trailer_url": None
        }

    @classmethod
    def extract_from_site_provider(
        cls,
        anime_title: str,
        anilist_id: Optional[int],
        slug: Optional[str],
        start_seconds: int = 90,
        duration_seconds: int = 15,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Directly slices real episode video with audio from AniHubStream's
        integrated edge CDN stream provider (AniPM / beta.cno.to).
        Bypasses YouTube bot checks, 429 throttling, and datacenter IP blocks entirely.
        """
        if not anilist_id or not slug:
            return None

        try:
            logger.info(f"Connecting to AniHubStream Provider for '{anime_title}' (ID: {anilist_id}, Slug: {slug})...")
            master_url = f"https://beta.cno.to/hls/{anilist_id}-{slug}/E0001/master.m3u8"
            proxy_url = f"https://anihubstream.com/api/test-proxy?u={master_url}"
            r = requests.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if r.status_code != 200 or "#EXTM3U" not in r.text:
                logger.warning(f"AniHub provider stream not found for {slug} (status: {r.status_code})")
                return None

            lines = r.text.splitlines()

            # 1. Select Video Playlist (prefer 720p or 1080p)
            v_url = None
            for i, line in enumerate(lines):
                if "#EXT-X-STREAM-INF" in line and ("1280x720" in line or "1920x1080" in line):
                    if i + 1 < len(lines):
                        v_url = lines[i + 1].strip()
                        break
            if not v_url:
                for i, line in enumerate(lines):
                    if "#EXT-X-STREAM-INF" in line and i + 1 < len(lines):
                        v_url = lines[i + 1].strip()
                        break

            # 2. Select Audio Playlist (prefer English, fallback to Japanese)
            a_url = None
            for line in lines:
                if '#EXT-X-MEDIA:TYPE=AUDIO' in line and ('en' in line.lower() or 'eng' in line.lower()):
                    match = re.search(r'URI="([^"]+)"', line)
                    if match:
                        a_url = match.group(1)
                        break
            if not a_url:
                for line in lines:
                    if '#EXT-X-MEDIA:TYPE=AUDIO' in line and ('ja' in line.lower() or 'jpn' in line.lower()):
                        match = re.search(r'URI="([^"]+)"', line)
                        if match:
                            a_url = match.group(1)
                            break
            if not a_url:
                for line in lines:
                    if '#EXT-X-MEDIA:TYPE=AUDIO' in line:
                        match = re.search(r'URI="([^"]+)"', line)
                        if match:
                            a_url = match.group(1)
                            break

            if not v_url or not a_url:
                logger.warning("Could not parse video and audio streams from provider master playlist.")
                return None

            # 3. Fetch sub-playlists
            v_m3u8 = requests.get(v_url, timeout=10).text
            a_m3u8 = requests.get(a_url, timeout=10).text

            v_init_match = re.search(r'EXT-X-MAP:URI="([^"]+)"', v_m3u8)
            a_init_match = re.search(r'EXT-X-MAP:URI="([^"]+)"', a_m3u8)
            if not v_init_match or not a_init_match:
                return None

            v_init = v_init_match.group(1)
            a_init = a_init_match.group(1)

            v_segs = [l.strip() for l in v_m3u8.splitlines() if l.startswith('http')]
            a_segs = [l.strip() for l in a_m3u8.splitlines() if l.startswith('http')]

            if not v_segs or not a_segs:
                return None

            # Slicing calculation (~4 seconds per segment)
            start_idx = max(0, min(start_seconds // 4, len(v_segs) - 4))
            num_segs = max(2, min((duration_seconds + 3) // 4, len(v_segs) - start_idx))

            logger.info(f"Downloading {num_segs} real video/audio chunks from AniHub CDN (~{start_idx * 4}s to +{num_segs * 4}s)...")
            v_data = requests.get(v_init, timeout=10).content
            for s in v_segs[start_idx:start_idx + num_segs]:
                v_data += requests.get(s, timeout=10).content

            a_data = requests.get(a_init, timeout=10).content
            for s in a_segs[start_idx:start_idx + num_segs]:
                a_data += requests.get(s, timeout=10).content

            temp_v = Config.OUTPUT_DIR / f"temp_site_v_{anilist_id}.mp4"
            temp_a = Config.OUTPUT_DIR / f"temp_site_a_{anilist_id}.mp4"
            with open(temp_v, "wb") as f:
                f.write(v_data)
            with open(temp_a, "wb") as f:
                f.write(a_data)

            # Mux together
            ffmpeg_bin = _get_ffmpeg_path()
            target_path = output_path or (Config.OUTPUT_DIR / f"raw_video_{slug}.mp4")
            cmd = [
                ffmpeg_bin, "-y",
                "-i", str(temp_v),
                "-i", str(temp_a),
                "-c:v", "copy",
                "-c:a", "aac",
                str(target_path)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Clean up temp chunks
            if temp_v.exists(): temp_v.unlink()
            if temp_a.exists(): temp_a.unlink()

            if res.returncode == 0 and target_path.exists() and target_path.stat().st_size > 50000:
                logger.info(f"✅ Sliced REAL anime episode clip directly from AniHubStream provider: {target_path}")
                return target_path

        except Exception as e:
            logger.warning(f"AniHubStream provider extraction failed: {e}")

        return None

    @classmethod
    def get_real_anime_clip(
        cls,
        anime_title: str,
        stream_source: Optional[str] = None,
        start_time: str = "00:01:30",
        duration: int = 15,
        output_filename: Optional[str] = None
    ) -> Path:
        safe_title = "".join(c for c in anime_title if c.isalnum() or c in ("-", "_")).lower()[:18]
        if not output_filename:
            output_filename = f"raw_video_{safe_title}.mp4"
        out_path = Config.OUTPUT_DIR / output_filename

        start_sec = cls._parse_seconds(start_time)
        end_sec = start_sec + duration
        section_str = f"*{start_sec}-{end_sec}"

        anime_details = cls.fetch_anime_details(anime_title)
        anilist_id = anime_details.get("id")
        slug = anime_details.get("slug") or safe_title

        # PRIORITY 1: Direct slice from your site's streaming provider (AniPM / beta.cno.to)
        site_clip = cls.extract_from_site_provider(
            anime_title=anime_title,
            anilist_id=anilist_id,
            slug=slug,
            start_seconds=start_sec,
            duration_seconds=duration,
            output_path=out_path
        )
        if site_clip and site_clip.exists() and site_clip.stat().st_size > 50000:
            return site_clip

        # PRIORITY 2: User-supplied stream source
        ffmpeg_bin = _get_ffmpeg_path()
        js_args = _get_js_runtime_args()
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

        if stream_source:
            logger.info(f"Extracting live stream slice ({start_time} to +{duration}s) from: {stream_source}")
            cmd = [*base_dlp_opts, "-o", str(out_path), stream_source]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 10000:
                logger.info(f"Successfully sliced stream clip: {out_path}")
                return out_path

        # PRIORITY 3: Official AniList trailer
        official_trailer = anime_details.get("trailer_url")
        if official_trailer:
            logger.info(f"Downloading official video footage from AniList trailer: {official_trailer}")
            cmd = [*base_dlp_opts, "-o", str(out_path), official_trailer]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if out_path.exists() and out_path.stat().st_size > 10000:
                return out_path
            webm = Path(str(out_path) + ".webm")
            if webm.exists() and webm.stat().st_size > 10000:
                return webm

        # PRIORITY 4: External scene search
        search_query = f"ytsearch1:{anime_title} best fight scene"
        logger.info(f"Searching and downloading scene footage for '{anime_title}' with audio...")
        cmd = [*base_dlp_opts, "-o", str(out_path), search_query]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if out_path.exists() and out_path.stat().st_size > 10000:
            return out_path
        webm_fallback = Path(str(out_path) + ".webm")
        if webm_fallback.exists() and webm_fallback.stat().st_size > 10000:
            return webm_fallback

        # PRIORITY 5: Fallback generator with pulsing audio
        logger.warning(f"External video fetch restricted on this runner. Generating animated 9:16 reel with real audio...")
        from ..generators.video_builder import ReelVideoBuilder
        fallback_clip = ReelVideoBuilder.generate_reel(
            anime=anime_details,
            badge_text="TRENDING ANIME MOMENT",
            duration=duration,
            filename=output_filename
        )
        return fallback_clip
