import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional
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

class StreamRecorder:
    """
    Extracts real anime video clips with full audio and sound effects
    directly from stream sources or searches high-definition scene footage.
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

        start_sec = cls._parse_seconds(start_time)
        end_sec = start_sec + duration
        section_str = f"*{start_sec}-{end_sec}"

        # If a direct stream / HLS m3u8 source URL was provided
        if stream_source:
            logger.info(f"Extracting live stream slice ({start_time} to +{duration}s) from: {stream_source}")
            cmd = [
                "yt-dlp",
                "--download-sections", section_str,
                "-f", "bv*[height<=1080]+ba/b",
                "--ffmpeg-location", ffmpeg_bin,
                "-o", str(out_path),
                "--force-keyframes-at-cuts",
                stream_source
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and out_path.exists():
                logger.info(f"Successfully sliced stream clip: {out_path}")
                return out_path
            logger.warning(f"Stream cut failed: {res.stderr[:200]}. Falling back to clip search...")

        # Automatic search for real high-definition action scene footage with full audio
        search_query = f"ytsearch1:{anime_title} best fight scene 1080p"
        logger.info(f"Searching and downloading real 1080p anime video footage for '{anime_title}' with audio...")

        cmd = [
            "yt-dlp",
            search_query,
            "--download-sections", section_str,
            "-f", "bv*[height<=1080]+ba/b",
            "--ffmpeg-location", ffmpeg_bin,
            "-o", str(out_path),
            "--force-keyframes-at-cuts"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Check if downloaded as .webm or .mp4
        if out_path.exists() and out_path.stat().st_size > 10000:
            return out_path
        
        # yt-dlp might append .webm if webm format was selected
        webm_fallback = Path(str(out_path) + ".webm")
        if webm_fallback.exists() and webm_fallback.stat().st_size > 10000:
            return webm_fallback

        # Check any matching file in output
        matches = list(Config.OUTPUT_DIR.glob(f"raw_video_{safe_title}*"))
        if matches and matches[0].stat().st_size > 10000:
            return matches[0]

        raise RuntimeError(f"Could not download real anime video clip for '{anime_title}': {res.stderr[:300]}")
