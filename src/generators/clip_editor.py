import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
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

class ClipEditor:
    """
    Transforms 16:9 widescreen anime clips into viral 9:16 vertical video reels
    (1080x1920) with ambient blurred background, hook header, and AniHub branding CTA.
    """

    WIDTH = 1080
    HEIGHT = 1920

    @classmethod
    def process_vertical_clip(
        cls,
        raw_clip_path: Path,
        anime_title: str,
        hook_text: str = "WAIT FOR THE END... 😱",
        output_filename: Optional[str] = None
    ) -> Path:
        if not raw_clip_path.exists():
            raise FileNotFoundError(f"Input clip not found: {raw_clip_path}")

        if not output_filename:
            safe_title = "".join(c for c in anime_title if c.isalnum() or c in ("-", "_")).lower()[:18]
            output_filename = f"viral_clip_{safe_title}.mp4"

        out_path = Config.OUTPUT_DIR / output_filename
        ffmpeg_bin = _get_ffmpeg_path()

        # Sanitize text for FFmpeg drawtext filter
        clean_hook = hook_text.replace("'", "").replace(":", "-").upper()
        clean_title = anime_title.replace("'", "").replace(":", "-").upper()
        cta_text = f"STREAM FULL EPISODE ON {Config.SITE_NAME.upper()}"
        bio_text = "LINK IN BIO • 1080P FREE"

        # FFmpeg filter complex:
        # 1. [bg]: Scale input to fill 1080x1920, crop, apply strong gaussian boxblur and slight darkening
        # 2. [fg]: Scale input to 1080 width maintaining 16:9 ratio (1080x608)
        # 3. Overlay [fg] in center of [bg]
        # 4. Top hook box & header text
        # 5. Bottom branded CTA box with website link
        filter_complex = (
            f"[0:v]scale={cls.WIDTH}:{cls.HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={cls.WIDTH}:{cls.HEIGHT},boxblur=25:5,eq=brightness=-0.15[bg]; "
            f"[0:v]scale={cls.WIDTH}:-1[fg]; "
            f"[bg][fg]overlay=0:(1920-h)/2[stacked]; "
            f"[stacked]drawbox=x=0:y=160:w={cls.WIDTH}:h=160:color=black@0.65:t=fill, "
            f"drawtext=text='{clean_hook}':fontcolor=yellow:fontsize=44:x=(w-text_w)/2:y=190, "
            f"drawtext=text='{clean_title}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=255, "
            f"drawbox=x=0:y=1680:w={cls.WIDTH}:h=240:color=black@0.85:t=fill, "
            f"drawtext=text='{cta_text}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=1730, "
            f"drawtext=text='{bio_text}':fontcolor=0xFF4B4B:fontsize=32:x=(w-text_w)/2:y=1795"
        )

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(raw_clip_path),
            "-filter_complex", filter_complex,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_path)
        ]

        logger.info(f"Rendering 9:16 vertical reframe for anime '{anime_title}'...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"Clip reframing failed: {res.stderr}")
            raise RuntimeError(f"FFmpeg error: {res.stderr[:250]}")

        logger.info(f"Viral 9:16 vertical clip generated at: {out_path}")
        return out_path
