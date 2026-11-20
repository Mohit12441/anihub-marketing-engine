import sqlite3
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from ..config import Config

logger = logging.getLogger(__name__)

class StateTracker:
    """Manages post history and prevents duplicate postings."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or Config.DB_PATH)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posted_items (
                    id TEXT PRIMARY KEY,
                    raw_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    post_reference TEXT,
                    posted_at TIMESTAMP NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_raw_platform 
                ON posted_items (raw_id, platform)
            """)
            conn.commit()

    def is_already_posted(self, raw_id: str, platform: str) -> bool:
        composite_id = f"{raw_id}_{platform.lower()}"
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM posted_items WHERE id = ?", (composite_id,))
            return cur.fetchone() is not None

    def record_post(self, raw_id: str, title: str, platform: str, post_reference: Optional[str] = None):
        composite_id = f"{raw_id}_{platform.lower()}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO posted_items 
                (id, raw_id, title, platform, post_reference, posted_at) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (composite_id, str(raw_id), title, platform.lower(), post_reference, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
        logger.info(f"Recorded post to database: [{platform.upper()}] {title} (ID: {raw_id})")

    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM posted_items ORDER BY posted_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]
