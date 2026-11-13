"""
LinkedIn Integration Module.
Handles Easy Apply search, pre-filtering, and application execution.
"""
import logging
from pathlib import Path
from typing import List, Optional

from src.platforms.base import BasePlatform, RawJob

logger = logging.getLogger("linkedin")


class LinkedInPlatform(BasePlatform):
    def __init__(self, config: dict):
        super().__init__(config)

    def search_jobs(self, keywords: List[str], locations: List[str]) -> List[RawJob]:
        logger.info(f"[LinkedIn] Searching Easy Apply jobs for {keywords[:2]} in {locations[:2]}...")
        return []

    def apply_to_job(self, job: RawJob, pitch_note: str, resume_path: Optional[Path] = None) -> tuple:
        """
        Smart Shortlist Policy:
        LinkedIn applications are never auto-submitted by the bot to protect Kaushal's
        personal profile from bot detection, CAPTCHAs, and account checkpoints.
        Returns ACTION_REQUIRED so it is queued in the Daily Report with 1-click manual apply.
        """
        logger.info(f"[LinkedIn Smart Shortlist] Queued for manual apply: {job.company} - {job.title}")
        return False, "ACTION_REQUIRED: LinkedIn Smart Shortlist — apply manually via direct link with pre-drafted pitch"
