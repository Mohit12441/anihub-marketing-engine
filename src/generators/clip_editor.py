import os
import re
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
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

def _clean_text_for_draw(text: str) -> str:
    """Strip emojis and non-printable characters that cause missing glyph boxes [] in TTF rendering."""
    cleaned = re.sub(r'[^\x20-\x7E]+', ' ', text)
    return re.sub(r'\s+', ' ', cleaned).strip()

def _get_font(size: int, bold: bool = False):
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    ]
    win_fonts = Path("C:/Windows/Fonts")
    for name in font_names:
        p = win_fonts / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

class ClipEditor:
    """
    Transforms widescreen anime clips into viral 9:16 vertical video reels (1080x1920)
    with ambient motion blur background, crystal-clear audio, and high-conversion branding.
    """

    WIDTH = 1080
    HEIGHT = 1920

    @classmethod
    def create_graphic_overlay(cls, anime_title: str, hook_text: str) -> Path:
        """Creates a professional 1080x1920 transparent PNG overlay without Fontconfig bugs."""
        overlay = Image.new("RGBA", (cls.WIDTH, cls.HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        font_hook = _get_font(36, bold=True)
        font_title = _get_font(48, bold=True)
        font_cta = _get_font(34, bold=True)
        font_badge = _get_font(26, bold=True)
        font_sub = _get_font(26, bold=False)

        # 1. Top Header Banner
        draw.rectangle([(0, 0), (cls.WIDTH, 320)], fill=(10, 12, 18, 230))
        draw.line([(0, 320), (cls.WIDTH, 320)], fill=(255, 62, 62, 255), width=3)

        # Top pill badge
        badge_text = "TRENDING ANIME MOMENT"
        badge_w = int(draw.textlength(badge_text, font=font_badge))
        badge_box = [((cls.WIDTH - badge_w) // 2 - 25, 45), ((cls.WIDTH + badge_w) // 2 + 25, 95)]
        draw.rounded_rectangle(badge_box, radius=20, fill=(255, 62, 62, 255))
        draw.text(((cls.WIDTH - badge_w) // 2, 56), badge_text, font=font_badge, fill=(255, 255, 255))

        # Hook text (Yellow high-visibility)
        hook_clean = _clean_text_for_draw(hook_text).upper()[:50]
        hook_w = int(draw.textlength(hook_clean, font=font_hook))
        draw.text(((cls.WIDTH - hook_w) // 2, 130), hook_clean, font=font_hook, fill=(255, 220, 80))

        # Anime Title
        title_clean = _clean_text_for_draw(anime_title).upper()[:35]
        title_w = int(draw.textlength(title_clean, font=font_title))
        draw.text(((cls.WIDTH - title_w) // 2, 210), title_clean, font=font_title, fill=(255, 255, 255))

        # 2. Bottom CTA Banner
        draw.rectangle([(0, 1600), (cls.WIDTH, cls.HEIGHT)], fill=(10, 12, 18, 240))
        draw.line([(0, 1600), (cls.WIDTH, 1600)], fill=(255, 62, 62, 255), width=3)

        cta_sub = "STREAM FULL EPISODES IN 1080P SUB / DUB"
        sub_w = int(draw.textlength(cta_sub, font=font_sub))
        draw.text(((cls.WIDTH - sub_w) // 2, 1650), cta_sub, font=font_sub, fill=(200, 210, 230))

        # Main Red Button CTA
        draw.rounded_rectangle([(120, 1720), (960, 1815)], radius=18, fill=(255, 62, 62, 255))
        site_cta = f"WATCH FREE ON {Config.SITE_NAME.upper()}"
        btn_w = int(draw.textlength(site_cta, font=font_cta))
        draw.text(((cls.WIDTH - btn_w) // 2, 1748), site_cta, font=font_cta, fill=(255, 255, 255))

        link_sub = "LINK IN BIO • NO POPUP ADS"
        link_w = int(draw.textlength(link_sub, font=font_sub))
        draw.text(((cls.WIDTH - link_w) // 2, 1845), link_sub, font=font_sub, fill=(255, 220, 80))

        overlay_path = Config.OUTPUT_DIR / "temp_overlay.png"
        overlay.save(overlay_path, "PNG")
        return overlay_path

    @classmethod
    def process_vertical_clip(
        cls,
        raw_clip_path: Path,
        anime_title: str,
        hook_text: str = "Wait for the animation to peak at the end 😱",
        output_filename: Optional[str] = None
    ) -> Path:
        if not raw_clip_path.exists():
            raise FileNotFoundError(f"Input video clip not found at: {raw_clip_path}")

        if not output_filename:
            safe_title = "".join(c for c in anime_title if c.isalnum() or c in ("-", "_")).lower()[:18]
            output_filename = f"viral_short_{safe_title}.mp4"

        out_path = Config.OUTPUT_DIR / output_filename
        overlay_png = cls.create_graphic_overlay(anime_title, hook_text)
        ffmpeg_bin = _get_ffmpeg_path()

        # FFmpeg filter:
        # [0:v] blurred ambient 1080x1920 background
        # [0:v] scaled 1080 width foreground in center
        # [1:v] clean Pillow overlay
        # -map "[outv]" -map "0:a" keeps original sound!
        filter_complex = (
            f"[0:v]scale={cls.WIDTH}:{cls.HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={cls.WIDTH}:{cls.HEIGHT},boxblur=25:5,eq=brightness=-0.15[bg]; "
            f"[0:v]scale={cls.WIDTH}:-1[fg]; "
            f"[bg][fg]overlay=0:(1920-h)/2[stacked]; "
            f"[stacked][1:v]overlay=0:0[outv]"
        )

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(raw_clip_path),
            "-i", str(overlay_png),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_path)
        ]

        logger.info(f"Compositing 9:16 vertical reel with real audio for '{anime_title}'...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"Clip compositing failed: {res.stderr}")
            raise RuntimeError(f"FFmpeg compositing error: {res.stderr[:250]}")

        # Clean up temporary overlay PNG
        if overlay_png.exists():
            overlay_png.unlink()

        logger.info(f"Successfully generated pro vertical reel with audio at: {out_path}")
        return out_path
