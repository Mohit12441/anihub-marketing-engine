import os
import unittest
import tempfile
from pathlib import Path
from PIL import Image

from src.database.tracker import StateTracker
from src.generators.copywriter import ContentCopywriter, clean_slug
from src.generators.graphic_builder import PromoGraphicBuilder
from src.generators.video_builder import ReelVideoBuilder
from src.generators.caption_animator import CaptionAnimator
from src.generators.viral_seo import ViralSEOGenerator
from src.generators.clip_editor import ClipEditor
from src.extractors.viral_timeline import ViralTimelineDetector

class TestMarketingPipeline(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db = Path(self.temp_dir.name) / "test_history.db"
        self.tracker = StateTracker(db_path=str(self.test_db))

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_clean_slug(self):
        slug = clean_slug("Frieren: Beyond Journey's End")
        self.assertEqual(slug, "frieren-beyond-journeys-end")

    def test_state_tracker_idempotency(self):
        self.assertFalse(self.tracker.is_already_posted("anime_123", "instagram"))
        self.tracker.record_post("anime_123", "Attack on Titan", "instagram", "post_ref_999")
        self.assertTrue(self.tracker.is_already_posted("anime_123", "instagram"))
        # Should not mark twitter as posted yet
        self.assertFalse(self.tracker.is_already_posted("anime_123", "twitter"))

    def test_copywriter_generation(self):
        mock_anime = {
            "title": "Solo Leveling",
            "score": 88,
            "genres": ["Action", "Fantasy", "Adventure"]
        }
        bundle = ContentCopywriter.generate_copy(mock_anime)
        
        self.assertIn("Solo Leveling", bundle["twitter_text"])
        self.assertIn("anihubstream.com/watch/solo-leveling", bundle["twitter_text"])
        self.assertLessEqual(len(bundle["twitter_text"]), 280)
        self.assertIn("DIRECT LINK IN BIO", bundle["instagram_text"])

    def test_graphic_builder(self):
        mock_anime = {
            "title": "Chainsaw Man",
            "score": 86,
            "genres": ["Action", "Supernatural"],
            "cover_url": None
        }
        img_path = PromoGraphicBuilder.generate_poster(mock_anime, filename="test_promo.jpg")
        self.assertTrue(img_path.exists())
        
        with Image.open(img_path) as img:
            self.assertEqual(img.size, (1080, 1350))
            
        if img_path.exists():
            img_path.unlink()

    def test_video_builder(self):
        mock_anime = {
            "title": "Jujutsu Kaisen",
            "score": 89,
            "genres": ["Action", "Fantasy"],
            "cover_url": None
        }
        # Render a short 1-second 1080x1920 test video
        video_path = ReelVideoBuilder.generate_reel(mock_anime, duration=1, fps=15, filename="test_reel.mp4")
        self.assertTrue(video_path.exists())
        self.assertGreater(video_path.stat().st_size, 10000)
        
        if video_path.exists():
            video_path.unlink()

    def test_viral_timeline_detector(self):
        segment = ViralTimelineDetector.find_viral_segment("jujutsu-kaisen", duration=15)
        self.assertEqual(segment["start_sec"], 1050)
        self.assertEqual(segment["duration"], 15)
        self.assertTrue(len(segment["subtitles"]) > 0)

    def test_caption_animator_ass(self):
        cues = [
            {"start": 0.0, "end": 2.5, "text": "Nobody expected this sudden power-up"},
            {"start": 2.5, "end": 5.0, "text": "Peak animation cinema"}
        ]
        out_ass = Path(self.temp_dir.name) / "test_sub.ass"
        result_path = CaptionAnimator.generate_ass_subtitles(cues, out_ass, style_preset="pop")
        self.assertTrue(result_path.exists())
        content = result_path.read_text(encoding="utf-8")
        self.assertIn("TikTokReels", content)
        self.assertIn("&H00D7FF&", content)

    def test_viral_seo_package(self):
        seo = ViralSEOGenerator.generate_seo_package("Jujutsu Kaisen")
        self.assertIn("anihubstream.com/watch/jujutsu-kaisen", seo["watch_url"])
        self.assertIn("Jujutsu Kaisen", seo["title_primary"])
        self.assertIn("#anime", seo["caption"])
        self.assertIn("jujutsu kaisen", seo["tags"].lower())

    def test_clip_editor_overlay(self):
        overlay = ClipEditor.create_graphic_overlay("Solo Leveling", "ARRISE SHADOW MONARCH")
        self.assertTrue(overlay.exists())
        with Image.open(overlay) as img:
            self.assertEqual(img.size, (1080, 1920))
        if overlay.exists():
            overlay.unlink()

if __name__ == "__main__":
    unittest.main()
