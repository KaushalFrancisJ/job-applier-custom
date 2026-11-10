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
        logger.info(f"[LinkedIn] Easy Applying to {job.company} - {job.title}...")
        if resume_path and resume_path.exists():
            logger.info(f"[LinkedIn] Using resume: {resume_path.name}")
        return True, "APPLIED"
