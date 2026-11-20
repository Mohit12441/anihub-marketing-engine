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
    Generates TikTok / Instagram Reels styled dynamic word-by-word highlighted captions
    in ASS (Advanced SubStation Alpha) format for direct burning onto video streams.
    """

    @classmethod
    def generate_ass_subtitles(
        cls,
        cues: List[Dict[str, Any]],
        output_file: Path,
        font_name: str = "Arial",
        font_size: int = 34
    ) -> Path:
        """
        Creates an ASS subtitle file with bold white text, black outline,
        and vibrant yellow active-word highlights (&H0000FFFF) matching TikTok reels.
        """
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokPop, {font_name}, {font_size}, &H00FFFFFF, &H000000FF, &H00000000, &H80000000, 1, 0, 0, 0, 100, 100, 1, 0, 1, 4.5, 2.0, 2, 40, 40, 460, 1

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

            # Generate word-by-word highlighted lines
            for i, target_word in enumerate(words):
                w_start = start_t + (i * word_duration)
                w_end = w_start + word_duration
                
                # Format current sentence with target word highlighted in bright yellow
                colored_words = []
                for j, w in enumerate(words):
                    clean_w = re.sub(r'[^\w\s\'-]', '', w).upper()
                    if j == i:
                        # Yellow highlight with slight scale emphasis
                        colored_words.append(f"{{\\c&H00D7FF&\\b1}}{clean_w}{{\\c&HFFFFFF&\\b1}}")
                    else:
                        colored_words.append(f"{{\\c&HFFFFFF&\\b1}}{clean_w}{{\\c&HFFFFFF&\\b1}}")

                formatted_text = " ".join(colored_words)
                start_str = _format_ass_time(w_start)
                end_str = _format_ass_time(w_end)

                dialogue_lines.append(
                    f"Dialogue: 0,{start_str},{end_str},TikTokPop,,0,0,0,,{formatted_text}"
                )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(dialogue_lines) + "\n")

        logger.info(f"Generated TikTok animated ASS captions file: {output_file}")
        return output_file
