import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("anihub-marketing")

from src.config import Config
from src.database.tracker import StateTracker
from src.fetchers.anilist import fetch_trending_anime, fetch_today_airing_anilist
from src.fetchers.jikan import fetch_today_airing_schedule
from src.generators.copywriter import ContentCopywriter
from src.generators.graphic_builder import PromoGraphicBuilder
from src.generators.video_builder import ReelVideoBuilder
from src.generators.clip_editor import ClipEditor
from src.generators.viral_seo import ViralSEOGenerator
from src.extractors.stream_recorder import StreamRecorder
from src.extractors.viral_timeline import ViralTimelineDetector
from src.publishers.instagram import InstagramPublisher
from src.publishers.twitter import TwitterPublisher
from src.utils.uploader import upload_public_image
from src.utils.notifier import send_notification

def run_marketing_pipeline(mode: str = "trending", max_posts: int = 1, platforms: str = "all"):
    logger.info(f"=== Starting AniHub Marketing Automation Pipeline (Mode: {mode.upper()}) ===")
    logger.info(f"Target Website: {Config.SITE_BASE_URL} | Dry Run Mode: {Config.DRY_RUN}")

    tracker = StateTracker()
    ig_publisher = InstagramPublisher()
    tw_publisher = TwitterPublisher()

    # 1. Fetch Candidates
    if mode == "schedule":
        candidates = fetch_today_airing_anilist() or fetch_today_airing_schedule()
        badge_text = "AIRING TODAY"
    else:
        candidates = fetch_trending_anime(limit=10)
        badge_text = "NOW TRENDING"

    if not candidates:
        logger.warning("No anime candidates retrieved. Exiting pipeline.")
        return

    published_count = 0
    target_platforms = ["instagram", "twitter"] if platforms == "all" else [platforms.lower()]

    for anime in candidates:
        anime_id = anime["id"]
        title = anime["title"]

        # Check if already posted across all targeted platforms
        needs_posting = any(not tracker.is_already_posted(anime_id, p) for p in target_platforms)
        if not needs_posting:
            logger.info(f"Skipping already posted anime: {title} (ID: {anime_id})")
            continue

        logger.info(f"\nProcessing Candidate [{published_count + 1}/{max_posts}]: '{title}'")

        try:
            # 2. Build Assets (Branded Graphic + 9:16 Video Reel)
            copy_bundle = ContentCopywriter.generate_copy(anime, post_type=mode)
            image_path = PromoGraphicBuilder.generate_poster(
                anime,
                badge_text=badge_text
            )
            video_path = ReelVideoBuilder.generate_reel(
                anime,
                badge_text=badge_text,
                duration=8
            )

            # 3. Instagram Publishing
            if "instagram" in target_platforms and not tracker.is_already_posted(anime_id, "instagram"):
                logger.info(f"Dispatching Instagram post for: {title}")
                if Config.DRY_RUN:
                    post_id = ig_publisher.publish_photo("mock_image_url", copy_bundle["instagram_text"])
                else:
                    public_img_url = upload_public_image(image_path)
                    post_id = ig_publisher.publish_photo(public_img_url, copy_bundle["instagram_text"])

                tracker.record_post(anime_id, title, "instagram", post_id)
                send_notification(
                    f"Published to Instagram: **{title}**\nLink: {copy_bundle['watch_url']}",
                    success=True
                )

            # 4. Twitter / X Publishing
            if "twitter" in target_platforms and not tracker.is_already_posted(anime_id, "twitter"):
                logger.info(f"Dispatching Twitter post for: {title}")
                tweet_id = tw_publisher.publish_tweet(
                    text=copy_bundle["twitter_text"],
                    local_image_path=image_path
                )
                tracker.record_post(anime_id, title, "twitter", tweet_id)
                send_notification(
                    f"Published to Twitter/X: **{title}**\nLink: {copy_bundle['watch_url']}",
                    success=True
                )

            published_count += 1
            if published_count >= max_posts:
                logger.info(f"Reached quota of {max_posts} post(s) for this run.")
                break

        except Exception as e:
            logger.error(f"Error processing anime '{title}': {e}", exc_info=True)
            send_notification(f"Failed to post '{title}': {str(e)}", success=False)

    logger.info(f"=== Pipeline Finished. Successfully published {published_count} item(s). ===")

def run_clip_pipeline(
    anime_name: str,
    stream_url: Optional[str] = None,
    start_time: Optional[str] = None,
    duration: int = 15,
    hook_text: Optional[str] = None
):
    logger.info(f"=== Starting Viral Climax Clip & SEO Generation for: '{anime_name}' ===")
    
    # 1. Generate SEO & Viral Metadata
    seo_data = ViralSEOGenerator.generate_seo_package(anime_name)
    safe_slug = seo_data["slug"]

    # 2. Intelligent Viral Timeline & Climax Detection
    timeline = ViralTimelineDetector.find_viral_segment(slug=safe_slug, duration=duration)
    hook = hook_text or timeline.get("hook") or seo_data["hook"]
    
    # Use user-specified start if provided, else use detected battle climax timestamp
    if start_time:
        effective_start = start_time
    else:
        start_sec = timeline.get("start_sec", 960)
        m = start_sec // 60
        s = start_sec % 60
        effective_start = f"00:{m:02d}:{s:02d}"

    logger.info(f"🎯 Target Viral Climax Window: {effective_start} (+{duration}s)")
    
    # 3. Extract Real Anime Video Clip from AniHubStream Provider
    clip_source = StreamRecorder.get_real_anime_clip(
        anime_title=anime_name,
        stream_source=stream_url,
        start_time=effective_start,
        duration=duration
    )

    # 4. Apply 9:16 Vertical Video Reframe with Ambient Blur & TikTok Animated Captions
    final_video = ClipEditor.process_vertical_clip(
        raw_clip_path=clip_source,
        anime_title=anime_name,
        hook_text=hook,
        output_filename=f"viral_short_{safe_slug}.mp4",
        subtitle_cues=timeline.get("subtitles")
    )

    # 4. Save Comprehensive Viral SEO & Tag Package
    seo_file = Config.OUTPUT_DIR / f"seo_{safe_slug}.txt"
    with open(seo_file, "w", encoding="utf-8") as f:
        f.write("=== YOUTUBE SHORTS / TIKTOK VIRAL SEO PACKAGE ===\n\n")
        f.write(f"TITLES (Choose best variant):\n")
        f.write(f"  • Primary: {seo_data['title_primary']}\n")
        f.write(f"  • Alt 1:   {seo_data['title_alt_1']}\n")
        f.write(f"  • Alt 2:   {seo_data['title_alt_2']}\n\n")
        f.write("CAPTION (TikTok / Instagram Reels):\n")
        f.write(f"{seo_data['caption']}\n\n")
        f.write(f"TAGS (YouTube Shorts):\n{seo_data['tags']}\n\n")
        f.write(f"PINNED COMMENT TEMPLATE:\n{seo_data['pinned_comment']}\n\n")
        f.write(f"DIRECT TRACKED WATCH LINK:\n{seo_data['watch_url']}\n")

    logger.info(f"✅ Real Video Clip with Audio generated: {final_video}")
    logger.info(f"✅ Viral SEO Package saved: {seo_file}")
    return final_video, seo_file

def main():
    parser = argparse.ArgumentParser(description="AniHub Stream Social Marketing Automation Engine")
    parser.add_argument("--mode", choices=["trending", "schedule", "clip"], default="trending",
                        help="Content strategy mode: 'trending', 'schedule', or 'clip'")
    parser.add_argument("--limit", type=int, default=1,
                        help="Number of new anime posts to publish per run (default: 1)")
    parser.add_argument("--platform", choices=["all", "instagram", "twitter"], default="all",
                        help="Target platform(s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate execution without sending live posts")
    parser.add_argument("--anime", type=str, default="Solo Leveling",
                        help="Anime title for clip mode (default: 'Solo Leveling')")
    parser.add_argument("--stream", type=str, default=None,
                        help="Optional stream or video URL to slice (HLS m3u8 or mp4)")
    parser.add_argument("--start", type=str, default=None,
                        help="Optional start timestamp (default: auto-detect viral climax)")
    parser.add_argument("--duration", type=int, default=15,
                        help="Clip duration in seconds (default: 15)")
    parser.add_argument("--hook", type=str, default=None,
                        help="Custom hook text for top overlay")

    args = parser.parse_args()

    if args.dry_run:
        Config.DRY_RUN = True

    if args.mode == "clip":
        run_clip_pipeline(
            anime_name=args.anime,
            stream_url=args.stream,
            start_time=args.start,
            duration=args.duration,
            hook_text=args.hook
        )
    else:
        run_marketing_pipeline(
            mode=args.mode,
            max_posts=args.limit,
            platforms=args.platform
        )

if __name__ == "__main__":
    main()
