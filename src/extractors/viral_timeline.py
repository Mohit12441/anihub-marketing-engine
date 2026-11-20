import re
import shutil
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from ..config import Config

logger = logging.getLogger(__name__)

def _get_ffmpeg_exe() -> str:
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

# Canonical climax timestamps (seconds into the episode) for viral anime
# Sourced from high-engagement fight peaks (Domain Expansion, Boss fights, Awakenings)
ICONIC_CLIMAX_REGISTRY: Dict[str, Dict[str, Any]] = {
    "jujutsu-kaisen": {
        "start_sec": 1050,  # 17:30 - Sukuna vs Megumi / Curse climax battle
        "duration": 15,
        "hook": "BRO REALLY THOUGHT HE COULD BEAT HIM",
        "subtitles": [
            {"start": 0.0, "end": 2.5, "text": "Nobody expected this sudden power-up"},
            {"start": 2.5, "end": 5.5, "text": "The animation reached absolute peak cinema"},
            {"start": 5.5, "end": 9.0, "text": "He completely unleashed his domain expansion"},
            {"start": 9.0, "end": 12.0, "text": "Watch this full fight in 1080p Ultra HD"},
            {"start": 12.0, "end": 15.0, "text": "Link in bio to stream free on AniHub"}
        ]
    },
    "solo-leveling": {
        "start_sec": 980,   # 16:20 - Jinwoo Blood-Red Commander Igris Climax
        "duration": 15,
        "hook": "THE EXACT MOMENT HE BECAME THE MONARCH",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "Arise... the shadows have awoken"},
            {"start": 3.0, "end": 6.5, "text": "He single-handedly cleared the S-rank dungeon"},
            {"start": 6.5, "end": 10.0, "text": "From E-rank weakling to unstoppable god"},
            {"start": 10.0, "end": 13.0, "text": "Stream every episode free on AniHub Stream"},
            {"start": 13.0, "end": 15.0, "text": "Tap the link in bio right now"}
        ]
    },
    "demon-slayer-kimetsu-no-yaiba": {
        "start_sec": 1120,  # 18:40 - Hinokami Kagura Dance climax
        "duration": 15,
        "hook": "THIS FIGHT BROKE THE INTERNET WORLDWIDE",
        "subtitles": [
            {"start": 0.0, "end": 3.2, "text": "Ufotable spent the entire budget on this scene"},
            {"start": 3.2, "end": 6.8, "text": "Hinokami Kagura unleashed against Rui"},
            {"start": 6.8, "end": 10.5, "text": "The sound design gave everyone literal chills"},
            {"start": 10.5, "end": 13.0, "text": "Watch the complete series in 1080p HD"},
            {"start": 13.0, "end": 15.0, "text": "Available now free on AniHubStream"}
        ]
    },
    "chainsaw-man": {
        "start_sec": 1020,  # 17:00 - Denji Chainsaw rampage
        "duration": 15,
        "hook": "MAPPA WENT COMPLETELY UNHINGED HERE",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "He revved the engine and showed zero mercy"},
            {"start": 3.0, "end": 6.5, "text": "The bloodiest battle in modern anime history"},
            {"start": 6.5, "end": 10.0, "text": "Uncensored ultra quality animation"},
            {"start": 10.0, "end": 13.0, "text": "Stream full episodes free without ads"},
            {"start": 13.0, "end": 15.0, "text": "Click the link in bio to watch now"}
        ]
    },
    "bleach": {
        "start_sec": 1080,  # 18:00 - Bankai activation
        "duration": 15,
        "hook": "HE FINALLY UNLEASHED HIS TRUE BANKAI",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "The spiritual pressure shook the entire realm"},
            {"start": 3.0, "end": 6.5, "text": "Studio Pierrot delivered the cleanest sakuga"},
            {"start": 6.5, "end": 10.0, "text": "Ten years of waiting for this single moment"},
            {"start": 10.0, "end": 13.0, "text": "Stream Thousand-Year Blood War in 1080p"},
            {"start": 13.0, "end": 15.0, "text": "Watch free on AniHub Stream • Link in Bio"}
        ]
    },
    "kaiju-no-8": {
        "start_sec": 1040,  # 17:20 - Kafka transformation punch
        "duration": 15,
        "hook": "ONE SINGLE PUNCH OBLITERATED EVERYTHING",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "His combat fortitude skyrocketed to 9.8"},
            {"start": 3.0, "end": 6.5, "text": "The shockwave cleared the entire battlefield"},
            {"start": 6.5, "end": 10.0, "text": "Production I.G went absolutely god tier"},
            {"start": 10.0, "end": 13.0, "text": "Watch Kaiju No. 8 episodes for free"},
            {"start": 13.0, "end": 15.0, "text": "Link in bio to stream on AniHub"}
        ]
    },
    "dandadan": {
        "start_sec": 990,   # 16:30 - Turbo Granny hyper-speed chase
        "duration": 15,
        "hook": "SCIENCE SARU CREATED PURE MASTERPIECE HERE",
        "subtitles": [
            {"start": 0.0, "end": 3.0, "text": "The sheer momentum and fluid animation"},
            {"start": 3.0, "end": 6.5, "text": "Hands down the most chaotic anime of the year"},
            {"start": 6.5, "end": 10.0, "text": "Every single frame is hand-drawn perfection"},
            {"start": 10.0, "end": 13.0, "text": "Watch all episodes in crystal clear 1080p"},
            {"start": 13.0, "end": 15.0, "text": "Stream free now on AniHub Stream"}
        ]
    }
}

class ViralTimelineDetector:
    """
    Intelligently identifies the most viral fight/climax scene timestamps
    for an anime using:
    1. Canonical Climax Registry (verified viral timestamps).
    2. AniSkip API (OP/ED stripping & Act 3 window calculation).
    3. Audio Energy Peak Detection (FFmpeg RMS/astats analysis for impact moments).
    """

    @classmethod
    def detect_audio_impact_peak(cls, video_path: Path) -> float:
        """
        Scans the sliced audio track for the loudest RMS spike (impact punch, explosion, scream)
        to trigger impact frames and camera punch-in zoom effects.
        Returns timestamp in seconds relative to the clip start.
        """
        if not video_path.exists():
            return 7.5

        ffmpeg_exe = _get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-i", str(video_path),
            "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
            "-f", "null", "-"
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
            peaks = []
            curr_time = 0.0

            for line in res.stdout.splitlines():
                if "pts_time:" in line:
                    m = re.search(r"pts_time:([0-9.]+)", line)
                    if m:
                        curr_time = float(m.group(1))
                elif "RMS_level=" in line:
                    m = re.search(r"RMS_level=([-0-9.]+)", line)
                    if m:
                        val = float(m.group(1))
                        # Filter out silent or boundary anomalies (ignore first 1.5s and last 1s)
                        if 1.5 <= curr_time <= 14.0:
                            peaks.append((curr_time, val))

            if peaks:
                # Max volume is highest value (closest to 0 dB, e.g. -15dB is louder than -35dB)
                best_peak = max(peaks, key=lambda x: x[1])
                logger.info(f"💥 Detected major audio impact spike at {best_peak[0]:.2f}s ({best_peak[1]:.1f} dB)")
                return round(best_peak[0], 2)
        except Exception as e:
            logger.warning(f"Audio peak detection fallback to center: {e}")

        return 7.5  # Midpoint default

    @classmethod
    def fetch_aniskip_climax_window(cls, mal_id: int, episode_len: int = 1440) -> Optional[int]:
        """
        Queries AniSkip API with episodeLength to strip OP and ED intervals.
        Calculates the Act 3 battle climax window (right before the ED).
        """
        try:
            url = f"https://api.aniskip.com/v2/skip-times/{mal_id}/1?types=op&types=ed&types=recap&episodeLength={episode_len}"
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                results = res.json().get("results", [])
                ed_start = None
                op_end = 120

                for r in results:
                    skip_type = r.get("skipType")
                    interval = r.get("interval", {})
                    if skip_type == "op":
                        op_end = int(interval.get("endTime", 120))
                    elif skip_type == "ed":
                        ed_start = int(interval.get("startTime", episode_len - 90))

                if ed_start:
                    # In anime, the climax fight concludes right before the ED begins
                    # Target 120 seconds before ED
                    climax_start = max(op_end + 300, ed_start - 150)
                    logger.info(f"AniSkip pinpointed ED at {ed_start}s -> Act 3 Climax at {climax_start}s")
                    return climax_start
        except Exception as e:
            logger.warning(f"AniSkip dynamic query skipped: {e}")

        return None

    @classmethod
    def find_viral_segment(cls, slug: str, mal_id: Optional[int] = None, duration: int = 15) -> Dict[str, Any]:
        """
        Returns optimal start_sec, duration, hook, and subtitle cues for maximum viral retention.
        """
        clean_slug = slug.lower().strip()

        # 1. Curated Canonical Climax Registry
        for key, config in ICONIC_CLIMAX_REGISTRY.items():
            if key in clean_slug or clean_slug in key:
                logger.info(f"⚡ Matched curated viral climax for '{slug}' at {config['start_sec']}s (Act 3 Boss Climax)")
                return {
                    "start_sec": config["start_sec"],
                    "duration": duration or config["duration"],
                    "hook": config["hook"],
                    "subtitles": config["subtitles"]
                }

        # 2. AniSkip API: Skip OP and calculate Act 3 Battle Climax before ED
        if mal_id:
            aniskip_climax = cls.fetch_aniskip_climax_window(mal_id)
            if aniskip_climax:
                logger.info(f"Targeting AniSkip Act 3 Battle Climax at {aniskip_climax}s for '{slug}'")
                return {
                    "start_sec": aniskip_climax,
                    "duration": duration,
                    "hook": "THE ANIMATION REACHED ABSOLUTE PEAK HERE",
                    "subtitles": cls._generate_default_cues()
                }

        # 3. Default Golden Ratio Heuristic:
        # Standard 24-minute anime (1440s), battle climax occurs around 16:30 (990s)
        climax_start = 990
        logger.info(f"Targeting Standard Act 3 Climax at {climax_start}s for '{slug}'")

        return {
            "start_sec": climax_start,
            "duration": duration,
            "hook": "NOBODY EXPECTED THIS INSANE LEVEL OF SAKUGA",
            "subtitles": cls._generate_default_cues()
        }

    @staticmethod
    def _generate_default_cues() -> List[Dict[str, Any]]:
        return [
            {"start": 0.0, "end": 3.0, "text": "Wait until you see how this scene concludes"},
            {"start": 3.0, "end": 6.5, "text": "The animation quality completely peaked right here"},
            {"start": 6.5, "end": 10.0, "text": "Nobody expected this insane level of sakuga"},
            {"start": 10.0, "end": 13.0, "text": "Watch the full 1080p episode in Sub & Dub"},
            {"start": 13.0, "end": 15.0, "text": "Stream free on AniHubStream • Link in Bio"}
        ]
