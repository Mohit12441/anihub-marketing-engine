import io
import os
import shutil
import logging
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from ..config import Config

logger = logging.getLogger(__name__)

def _get_ffmpeg_path() -> str:
    """Finds system ffmpeg or uses imageio_ffmpeg bundled binary."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

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

class ReelVideoBuilder:
    """
    Builds 1080x1920 (9:16 vertical) viral short-form video reels
    optimized for Instagram Reels, TikTok, and YouTube Shorts.
    """

    WIDTH = 1080
    HEIGHT = 1920

    @classmethod
    def generate_reel(
        cls,
        anime: Dict[str, Any],
        badge_text: str = "TRENDING ON ANIHUB",
        duration: int = 8,
        fps: int = 30,
        filename: Optional[str] = None
    ) -> Path:
        title = anime.get("title", "Must-Watch Anime")
        cover_url = anime.get("cover_url")
        score = anime.get("score")
        genres = anime.get("genres", [])

        # 1. Download cover art
        cover_img = None
        if cover_url:
            try:
                logger.info(f"Downloading cover art for video reel from {cover_url}...")
                resp = requests.get(cover_url, timeout=12)
                resp.raise_for_status()
                cover_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            except Exception as e:
                logger.warning(f"Could not load cover for video: {e}")

        # 2. Build 1080x1920 Canvas
        canvas = Image.new("RGBA", (cls.WIDTH, cls.HEIGHT), (15, 17, 23, 255))

        if cover_img:
            # Background: Heavily blurred & darkened scale of cover image
            bg = cover_img.resize((cls.WIDTH, cls.HEIGHT), Image.Resampling.BILINEAR)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
            # Darken overlay
            darken = Image.new("RGBA", (cls.WIDTH, cls.HEIGHT), (0, 0, 0, 140))
            bg = Image.alpha_composite(bg, darken)
            canvas.paste(bg, (0, 0))

            # Foreground: Crisp centered card with rounded corners
            card_w = 760
            card_h = int(card_w * (cover_img.height / cover_img.width))
            if card_h > 1050:
                card_h = 1050
                card_w = int(card_h * (cover_img.width / cover_img.height))

            fg = cover_img.resize((card_w, card_h), Image.Resampling.LANCZOS)
            fg_x = (cls.WIDTH - card_w) // 2
            fg_y = 380

            # Card drop shadow
            shadow = Image.new("RGBA", (card_w + 40, card_h + 40), (0, 0, 0, 160))
            shadow = shadow.filter(ImageFilter.GaussianBlur(15))
            canvas.paste(shadow, (fg_x - 20, fg_y - 10), shadow)
            canvas.paste(fg, (fg_x, fg_y))

        # Bottom Gradient
        gradient_h = 750
        gradient = Image.new("RGBA", (cls.WIDTH, gradient_h), (0, 0, 0, 0))
        draw_g = ImageDraw.Draw(gradient)
        for y in range(gradient_h):
            ratio = y / gradient_h
            alpha = int(255 * (ratio ** 1.2))
            draw_g.line([(0, y), (cls.WIDTH, y)], fill=(11, 13, 18, alpha))
        canvas.paste(gradient, (0, cls.HEIGHT - gradient_h), gradient)

        draw = ImageDraw.Draw(canvas)

        # 3. Top Floating Badge
        font_badge = _get_font(32, bold=True)
        badge_w = len(badge_text) * 22 + 60
        badge_x = (cls.WIDTH - badge_w) // 2
        draw.rounded_rectangle([(badge_x, 220), (badge_x + badge_w, 290)], radius=35, fill=(255, 62, 62, 255))
        draw.text((badge_x + 30, 238), badge_text.upper(), font=font_badge, fill=(255, 255, 255, 255))

        # 4. Anime Title
        font_title = _get_font(58, bold=True)
        max_title_chars = 24
        title_lines = []
        words = title.split()
        curr = []
        for w in words:
            if len(" ".join(curr + [w])) <= max_title_chars:
                curr.append(w)
            else:
                title_lines.append(" ".join(curr))
                curr = [w]
        if curr:
            title_lines.append(" ".join(curr))

        y_text = 1460
        for line in title_lines[:2]:
            line_w = int(draw.textlength(line, font=font_title))
            x_line = (cls.WIDTH - line_w) // 2
            draw.text((x_line, y_text), line, font=font_title, fill=(255, 255, 255, 255))
            y_text += 70

        # 5. Metadata Tags (Score & Quality)
        meta_parts = []
        if score:
            meta_parts.append(f"⭐ {score}/100")
        if genres:
            meta_parts.append(" • ".join(genres[:2]))
        meta_parts.append("1080p Ultra HD")
        meta_line = " | ".join(meta_parts)
        font_meta = _get_font(28, bold=False)
        meta_w = int(draw.textlength(meta_line, font=font_meta))
        draw.text(((cls.WIDTH - meta_w) // 2, y_text + 15), meta_line, font=font_meta, fill=(200, 210, 225, 255))

        # 6. Bottom Banner / CTA
        banner_top = cls.HEIGHT - 200
        draw.rectangle([(0, banner_top), (cls.WIDTH, cls.HEIGHT)], fill=(18, 22, 30, 255))
        draw.line([(0, banner_top), (cls.WIDTH, banner_top)], fill=(255, 62, 62, 255), width=4)

        font_brand = _get_font(44, bold=True)
        brand_text = f"STREAM FREE ON {Config.SITE_NAME.upper()}"
        brand_w = int(draw.textlength(brand_text, font=font_brand))
        draw.text(((cls.WIDTH - brand_w) // 2, banner_top + 40), brand_text, font=font_brand, fill=(255, 255, 255, 255))

        font_link = _get_font(30, bold=True)
        link_text = "🔗 LINK IN BIO • NO POPUP ADS"
        link_w = int(draw.textlength(link_text, font=font_link))
        draw.text(((cls.WIDTH - link_w) // 2, banner_top + 105), link_text, font=font_link, fill=(255, 62, 62, 255))

        # 7. Save intermediate frame
        safe_title = "".join(c for c in title if c.isalnum() or c in ("-", "_")).lower()[:20]
        temp_frame = Config.OUTPUT_DIR / f"frame_{safe_title}.png"
        canvas.convert("RGB").save(temp_frame, "PNG")

        # 8. Encode MP4 Video with Smooth Ken Burns Zoom Effect
        if not filename:
            filename = f"reel_{safe_title}.mp4"
        out_mp4 = Config.OUTPUT_DIR / filename

        ffmpeg_bin = _get_ffmpeg_path()
        total_frames = duration * fps
        zoom_filter = (
            f"zoompan=z='min(zoom+0.0006,1.08)':d={total_frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={cls.WIDTH}x{cls.HEIGHT}:fps={fps},"
            f"format=yuv420p"
        )

        cmd = [
            ffmpeg_bin,
            "-y",
            "-loop", "1",
            "-i", str(temp_frame),
            "-f", "lavfi",
            "-i", "sine=f=180:beep_factor=4:r=48000",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(duration),
            "-vf", zoom_filter,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-shortest",
            str(out_mp4)
        ]

        logger.info(f"Rendering 9:16 vertical MP4 video reel ({duration}s at {fps}fps)...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg encoding failed: {res.stderr}")
            raise RuntimeError(f"FFmpeg encoding failed: {res.stderr[:200]}")

        # Clean up temporary frame
        if temp_frame.exists():
            temp_frame.unlink()

        logger.info(f"Successfully generated 9:16 viral video reel at: {out_mp4}")
        return out_mp4
