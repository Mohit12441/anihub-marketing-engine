import re
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def _format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS timestamp H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

class CaptionAnimator:
    """
    Generates TikTok / Instagram Reels styled dynamic bouncing karaoke captions
    in ASS (Advanced SubStation Alpha) format for direct burning onto video streams.
    Features:
    - Word-by-word reveal with active word scaling and color burst
    - Bold fonts with heavy outline for 100% legibility on high-action scenes
    - Configurable color styles: 'pop' (yellow), 'beast' (neon green), 'fire' (coral/orange)
    """

    STYLES = {
        "pop": {
            "active_color": "&H00D7FF&",    # Vibrant TikTok Yellow
            "inactive_color": "&H00FFFFFF&" # Crisp White
        },
        "beast": {
            "active_color": "&H0055FF00&",  # Neon Slime Green
            "inactive_color": "&H00FFFFFF&"
        },
        "fire": {
            "active_color": "&H002288FF&",   # Fiery Orange / Coral
            "inactive_color": "&H00FFFFFF&"
        }
    }

    @classmethod
    def generate_ass_subtitles(
        cls,
        cues: List[Dict[str, Any]],
        output_file: Path,
        style_preset: str = "pop",
        font_name: str = "Arial",
        font_size: int = 38
    ) -> Path:
        """
        Creates an ASS subtitle file with bold uppercase text, black outline,
        and animated bounce-in + vibrant color highlight on each active spoken word.
        """
        palette = cls.STYLES.get(style_preset, cls.STYLES["pop"])
        active_col = palette["active_color"]
        inactive_col = palette["inactive_color"]

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokReels, {font_name}, {font_size}, &H00FFFFFF, &H000000FF, &H00000000, &H80000000, 1, 0, 0, 0, 100, 100, 1, 0, 1, 5.0, 2.5, 2, 40, 40, 480, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines = []

        for cue in cues:
            phrase = cue.get("text", "").strip()
            if not phrase:
                continue

            start_t = float(cue.get("start", 0.0))
            end_t = float(cue.get("end", start_t + 2.5))
            duration = max(0.4, end_t - start_t)

            words = phrase.split()
            if not words:
                continue

            word_duration = duration / len(words)

            # Generate word-by-word bouncing lines
            for i, target_word in enumerate(words):
                w_start = start_t + (i * word_duration)
                w_end = w_start + word_duration

                colored_words = []
                for j, w in enumerate(words):
                    clean_w = re.sub(r'[^\w\s\'-]', '', w).upper()
                    if j == i:
                        # Bouncing pop scale: pops to 125% then settles to 100% with bright highlight
                        bounce_tag = "{\\t(0,90,\\fscx125\\fscy125)\\t(90,180,\\fscx100\\fscy100)"
                        colored_words.append(f"{bounce_tag}\\c{active_col}\\b1}}{clean_w}{{\\c{inactive_col}\\b1}}")
                    else:
                        colored_words.append(f"{{\\c{inactive_col}\\b1}}{clean_w}{{\\c{inactive_col}\\b1}}")

                formatted_text = " ".join(colored_words)
                start_str = _format_ass_time(w_start)
                end_str = _format_ass_time(w_end)

                dialogue_lines.append(
                    f"Dialogue: 0,{start_str},{end_str},TikTokReels,,0,0,0,,{formatted_text}"
                )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(dialogue_lines) + "\n")

        logger.info(f"Generated TikTok bouncing ASS captions file ({style_preset}): {output_file}")
        return output_file
