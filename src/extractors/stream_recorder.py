import logging
import subprocess
import shutil
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
    Extracts and slices high-definition video clips from anime stream sources
    (HLS .m3u8, MP4, or web stream URLs) without downloading full episodes.
    """

    @classmethod
    def extract_clip(
        cls,
        stream_source: str,
        start_time: str = "00:05:00",
        duration: int = 30,
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Slices a time-stamped highlight clip from a stream URL using yt-dlp & ffmpeg.
        start_time format: "MM:SS" or "HH:MM:SS"
        """
        if not output_filename:
            output_filename = "raw_clip.mp4"
        out_path = Config.OUTPUT_DIR / output_filename

        ffmpeg_bin = _get_ffmpeg_path()
        logger.info(f"Extracting {duration}s clip starting at {start_time} from stream...")

        # If running in test/dry-run or if yt-dlp is invoked
        try:
            import yt_dlp
            ydl_opts = {
                "format": "best[height<=1080]/best",
                "outtmpl": str(out_path),
                "download_ranges": yt_dlp.utils.download_range_func(None, [(cls._parse_seconds(start_time), cls._parse_seconds(start_time) + duration)]),
                "force_keyframes_at_cuts": True,
                "quiet": True,
                "no_warnings": True,
                "ffmpeg_location": ffmpeg_bin
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([stream_source])

            if out_path.exists() and out_path.stat().st_size > 1000:
                logger.info(f"Clip extracted successfully to: {out_path}")
                return out_path
        except Exception as e:
            logger.warning(f"yt-dlp download failed: {e}. Attempting direct FFmpeg stream cut...")

        # Fallback to direct FFmpeg seek slice
        try:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-ss", start_time,
                "-i", stream_source,
                "-t", str(duration),
                "-c", "copy",
                "-movflags", "+faststart",
                str(out_path)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and out_path.exists():
                logger.info(f"FFmpeg direct stream slice saved to: {out_path}")
                return out_path
        except Exception as e:
            logger.error(f"FFmpeg direct cut failed: {e}")

        raise RuntimeError(f"Could not extract video clip from source: {stream_source}")

    @staticmethod
    def _parse_seconds(time_str: str) -> float:
        parts = time_str.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(time_str)
