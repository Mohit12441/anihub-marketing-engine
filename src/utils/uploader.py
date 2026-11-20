import os
import logging
import requests
from pathlib import Path
from typing import Optional
from ..config import Config

logger = logging.getLogger(__name__)

def upload_public_image(image_path: Path) -> str:
    """
    Uploads a local image to a public host (Imgur or free file host)
    so the Instagram Meta Graph API can ingest it.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at {image_path}")

    # 1. Check if Imgur Client ID is configured
    client_id = Config.IMGUR_CLIENT_ID
    if client_id:
        try:
            logger.info("Staging image to Imgur...")
            headers = {"Authorization": f"Client-ID {client_id}"}
            with open(image_path, "rb") as f:
                res = requests.post(
                    "https://api.imgur.com/3/image",
                    headers=headers,
                    files={"image": f},
                    timeout=20
                )
            res.raise_for_status()
            url = res.json().get("data", {}).get("link")
            if url:
                logger.info(f"Image successfully staged to Imgur: {url}")
                return url
        except Exception as e:
            logger.warning(f"Imgur upload failed: {e}. Trying secondary public host...")

    # 2. Secondary free fallback host (0x0.st / tmpfiles.org) for automation convenience
    try:
        logger.info("Staging image to temporary public host (tmpfiles.org)...")
        with open(image_path, "rb") as f:
            res = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=20
            )
        res.raise_for_status()
        raw_url = res.json().get("data", {}).get("url")
        if raw_url:
            # Transform view URL to direct image URL: https://tmpfiles.org/123/img.jpg -> https://tmpfiles.org/dl/123/img.jpg
            direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            logger.info(f"Image staged to tmpfiles: {direct_url}")
            return direct_url
    except Exception as e:
        logger.error(f"Fallback upload failed: {e}")
        raise RuntimeError("Failed to stage image to a public URL for Instagram API ingestion.")
