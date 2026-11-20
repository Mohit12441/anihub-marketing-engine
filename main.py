import argparse
import sys
import logging
from pathlib import Path

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
            # 2. Build Assets
            copy_bundle = ContentCopywriter.generate_copy(anime, post_type=mode)
            image_path = PromoGraphicBuilder.generate_poster(
                anime,
                badge_text=badge_text
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

def main():
    parser = argparse.ArgumentParser(description="AniHub Stream Social Marketing Automation Engine")
    parser.add_argument("--mode", choices=["trending", "schedule"], default="trending",
                        help="Content strategy mode: 'trending' or 'schedule'")
    parser.add_argument("--limit", type=int, default=1,
                        help="Number of new anime posts to publish per run (default: 1)")
    parser.add_argument("--platform", choices=["all", "instagram", "twitter"], default="all",
                        help="Target platform(s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate execution without sending live posts")

    args = parser.parse_args()

    if args.dry_run:
        Config.DRY_RUN = True

    run_marketing_pipeline(
        mode=args.mode,
        max_posts=args.limit,
        platforms=args.platform
    )

if __name__ == "__main__":
    main()
