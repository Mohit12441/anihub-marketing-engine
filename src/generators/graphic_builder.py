import io
import os
import logging
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional, Dict, Any
from ..config import Config

logger = logging.getLogger(__name__)

def _get_font(size: int, bold: bool = False):
    """Attempts to find a clean TTF font or falls back to system font."""
    font_names = [
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    ]
    # Check Windows Fonts directory
    win_fonts = Path("C:/Windows/Fonts")
    for name in font_names:
        p = win_fonts / name
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    # Fallback default
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

class PromoGraphicBuilder:
    """Builds professional 1080x1350 social promo posters with AniHub branding."""

    WIDTH = 1080
    HEIGHT = 1350

    @classmethod
    def generate_poster(
        cls,
        anime: Dict[str, Any],
        badge_text: str = "TRENDING ON ANIHUB",
        filename: Optional[str] = None
    ) -> Path:
        title = anime.get("title", "Popular Anime")
        cover_url = anime.get("cover_url")
        score = anime.get("score")
        genres = anime.get("genres", [])

        # 1. Base Canvas
        canvas = Image.new("RGBA", (cls.WIDTH, cls.HEIGHT), (15, 17, 23, 255))
        
        # 2. Fetch and render cover image
        if cover_url:
            try:
                logger.info(f"Downloading cover art from {cover_url}...")
                resp = requests.get(cover_url, timeout=12)
                resp.raise_for_status()
                cover_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")

                # Scale to fit upper 75% while keeping aspect ratio
                target_w = cls.WIDTH
                target_h = int(target_w * (cover_img.height / cover_img.width))
                if target_h < 950:
                    target_h = 950
                    target_w = int(target_h * (cover_img.width / cover_img.height))

                cover_resized = cover_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                paste_x = (cls.WIDTH - target_w) // 2
                canvas.paste(cover_resized, (paste_x, 0))
            except Exception as e:
                logger.warning(f"Could not load cover image: {e}. Using dark background.")

        # 3. Apply smooth dark bottom gradient for readability
        gradient_h = 650
        gradient = Image.new("RGBA", (cls.WIDTH, gradient_h), (0, 0, 0, 0))
        draw_g = ImageDraw.Draw(gradient)
        for y in range(gradient_h):
            ratio = y / gradient_h
            alpha = int(255 * (ratio ** 1.3))
            draw_g.line([(0, y), (cls.WIDTH, y)], fill=(13, 15, 20, alpha))
        canvas.paste(gradient, (0, cls.HEIGHT - gradient_h), gradient)

        draw = ImageDraw.Draw(canvas)

        # 4. Top/Bottom Accent Bars
        draw.rectangle([(0, 0), (cls.WIDTH, 12)], fill=(255, 62, 62, 255))

        # 5. Badge (e.g. "TRENDING NOW" or "AIRING TODAY")
        font_badge = _get_font(26, bold=True)
        badge_box = [(60, 780), (60 + len(badge_text) * 18 + 40, 830)]
        draw.rounded_rectangle(badge_box, radius=8, fill=(255, 62, 62, 255))
        draw.text((80, 792), badge_text.upper(), font=font_badge, fill=(255, 255, 255, 255))

        # 6. Anime Title (Multi-line wrapping)
        font_title = _get_font(52, bold=True)
        max_title_chars = 26
        title_lines = []
        words = title.split()
        current_line = []
        for word in words:
            if len(" ".join(current_line + [word])) <= max_title_chars:
                current_line.append(word)
            else:
                title_lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            title_lines.append(" ".join(current_line))

        # Draw up to 2 lines
        y_text = 860
        for line in title_lines[:2]:
            draw.text((60, y_text), line, font=font_title, fill=(255, 255, 255, 255))
            y_text += 65

        # 7. Genres / Details string
        font_meta = _get_font(28, bold=False)
        meta_items = []
        if score:
            meta_items.append(f"⭐ {score}/100")
        if genres:
            meta_items.append(" • ".join(genres[:3]))
        meta_items.append("1080p Ultra HD")
        draw.text((60, y_text + 15), " | ".join(meta_items), font=font_meta, fill=(180, 190, 205, 255))

        # 8. Prominent AniHub Stream Brand Banner at the base
        banner_top = cls.HEIGHT - 160
        draw.rectangle([(0, banner_top), (cls.WIDTH, cls.HEIGHT)], fill=(20, 24, 33, 255))
        draw.line([(0, banner_top), (cls.WIDTH, banner_top)], fill=(40, 48, 65, 255), width=2)

        font_brand = _get_font(38, bold=True)
        draw.text((60, banner_top + 35), "ANIHUBSTREAM.COM", font=font_brand, fill=(255, 62, 62, 255))

        font_cta = _get_font(28, bold=True)
        draw.text((60, banner_top + 90), "WATCH FULL EPISODES FREE • SUB & DUB", font=font_cta, fill=(255, 255, 255, 255))

        # 9. Save output
        if not filename:
            safe_title = "".join(c for c in title if c.isalnum() or c in ("-", "_")).lower()[:20]
            filename = f"promo_{safe_title}.jpg"

        out_path = Config.OUTPUT_DIR / filename
        canvas.convert("RGB").save(out_path, "JPEG", quality=92, optimize=True)
        logger.info(f"Generated promo graphic saved to: {out_path}")
        return out_path
