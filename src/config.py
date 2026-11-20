import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load local .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Config:
    """Centralized, typed application configuration."""
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    OUTPUT_DIR = BASE_DIR / "output"
    DB_PATH = BASE_DIR / "post_history.db"

    # Runtime Settings
    DRY_RUN: bool = os.getenv("DRY_RUN", "False").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Marketing Target
    SITE_BASE_URL: str = os.getenv("SITE_BASE_URL", "https://anihubstream.com").rstrip("/")
    SITE_NAME: str = os.getenv("SITE_NAME", "AniHub Stream")
    
    # Instagram Graph API
    INSTAGRAM_ACCOUNT_ID: Optional[str] = os.getenv("INSTAGRAM_ACCOUNT_ID")
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    
    # Twitter / X API v2
    TWITTER_API_KEY: Optional[str] = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET: Optional[str] = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: Optional[str] = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET: Optional[str] = os.getenv("TWITTER_ACCESS_SECRET")
    
    # Image Hosting
    IMGUR_CLIENT_ID: Optional[str] = os.getenv("IMGUR_CLIENT_ID")
    
    # Notifications
    DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")

    @classmethod
    def validate_for_live_run(cls, platform: str = "all"):
        """Validates credentials when not in DRY_RUN mode."""
        if cls.DRY_RUN:
            return
            
        missing = []
        if platform in ("instagram", "all"):
            if not cls.INSTAGRAM_ACCOUNT_ID:
                missing.append("INSTAGRAM_ACCOUNT_ID")
            if not cls.INSTAGRAM_ACCESS_TOKEN:
                missing.append("INSTAGRAM_ACCESS_TOKEN")
            if not cls.IMGUR_CLIENT_ID:
                missing.append("IMGUR_CLIENT_ID (Required for Instagram image staging)")

        if platform in ("twitter", "all"):
            if not cls.TWITTER_API_KEY:
                missing.append("TWITTER_API_KEY")
            if not cls.TWITTER_API_SECRET:
                missing.append("TWITTER_API_SECRET")
            if not cls.TWITTER_ACCESS_TOKEN:
                missing.append("TWITTER_ACCESS_TOKEN")
            if not cls.TWITTER_ACCESS_SECRET:
                missing.append("TWITTER_ACCESS_SECRET")

        if missing:
            raise ValueError(
                f"Missing required environment variables for live run: {', '.join(missing)}\n"
                "Please configure these in your .env or set DRY_RUN=True."
            )

# Ensure output directory exists
Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
