import logging
from pathlib import Path
from typing import Optional
from ..config import Config

logger = logging.getLogger(__name__)

class TwitterPublisher:
    """Official Twitter / X API v2 Publisher using Tweepy."""

    def __init__(self):
        self.api_key = Config.TWITTER_API_KEY
        self.api_secret = Config.TWITTER_API_SECRET
        self.access_token = Config.TWITTER_ACCESS_TOKEN
        self.access_secret = Config.TWITTER_ACCESS_SECRET

    def publish_tweet(self, text: str, local_image_path: Optional[Path] = None) -> Optional[str]:
        """
        Publishes a tweet with an optional attached media image.
        """
        if Config.DRY_RUN:
            logger.info(f"[DRY_RUN] Mock Twitter tweet succeeded: {text[:60]}...")
            return "dry_run_tweet_id"

        Config.validate_for_live_run(platform="twitter")

        try:
            import tweepy
            
            # 1. Authenticate with Twitter API v1.1 for media upload
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_secret
            )
            api_v1 = tweepy.API(auth)

            media_ids = []
            if local_image_path and local_image_path.exists():
                logger.info(f"Uploading media {local_image_path} to Twitter...")
                media = api_v1.media_upload(str(local_image_path))
                media_ids.append(media.media_id)

            # 2. Authenticate with Twitter Client (API v2) for tweeting
            client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret
            )

            logger.info("Posting tweet to X / Twitter...")
            res = client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
            tweet_id = str(res.data.get("id"))
            logger.info(f"Successfully posted to Twitter! Tweet ID: {tweet_id}")
            return tweet_id
        except Exception as e:
            logger.error(f"Failed to publish tweet: {e}")
            raise
