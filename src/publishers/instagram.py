import time
import logging
import requests
from typing import Dict, Any, Optional
from ..config import Config

logger = logging.getLogger(__name__)

class InstagramPublisher:
    """Official Meta Graph API Publisher for Instagram Professional/Creator accounts."""

    API_VERSION = "v19.0"

    def __init__(self):
        self.account_id = Config.INSTAGRAM_ACCOUNT_ID
        self.access_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.base_url = f"https://graph.facebook.com/{self.API_VERSION}"

    def publish_photo(self, public_image_url: str, caption: str) -> Optional[str]:
        """
        Publishes a photo post via Meta Graph API:
        Step 1: POST /{ig-user-id}/media -> creates media container
        Step 2: Poll container status until FINISHED
        Step 3: POST /{ig-user-id}/media_publish -> publishes post
        """
        if Config.DRY_RUN:
            logger.info(f"[DRY_RUN] Mock Instagram post succeeded for image: {public_image_url}")
            return "dry_run_instagram_post_id"

        Config.validate_for_live_run(platform="instagram")

        # Step 1: Create Container
        logger.info(f"Creating Instagram media container for account {self.account_id}...")
        container_endpoint = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "image_url": public_image_url,
            "caption": caption,
            "access_token": self.access_token
        }
        res = requests.post(container_endpoint, data=payload, timeout=20)
        if not res.ok:
            logger.error(f"Failed to create Instagram container: {res.text}")
            res.raise_for_status()
            
        creation_id = res.json().get("id")
        logger.info(f"Container created with ID: {creation_id}. Polling readiness...")

        # Step 2: Poll status
        status_endpoint = f"{self.base_url}/{creation_id}"
        max_attempts = 10
        ready = False
        for attempt in range(max_attempts):
            time.sleep(3)
            status_res = requests.get(status_endpoint, params={"fields": "status_code", "access_token": self.access_token}, timeout=10)
            if status_res.ok:
                status_code = status_res.json().get("status_code")
                if status_code == "FINISHED":
                    ready = True
                    break
                elif status_code == "ERROR":
                    raise RuntimeError(f"Instagram media container processing failed: {status_res.text}")
            logger.debug(f"Media container status poll attempt {attempt+1}/{max_attempts}...")

        if not ready:
            raise TimeoutError("Timed out waiting for Instagram media container to finish processing.")

        # Step 3: Publish container
        logger.info(f"Publishing container {creation_id} to Instagram feed...")
        publish_endpoint = f"{self.base_url}/{self.account_id}/media_publish"
        pub_res = requests.post(publish_endpoint, data={"creation_id": creation_id, "access_token": self.access_token}, timeout=20)
        if not pub_res.ok:
            logger.error(f"Failed to publish Instagram media: {pub_res.text}")
            pub_res.raise_for_status()

        post_id = pub_res.json().get("id")
        logger.info(f"Successfully published post to Instagram! Post ID: {post_id}")
        return post_id
