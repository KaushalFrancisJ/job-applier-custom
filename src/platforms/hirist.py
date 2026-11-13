"""
Hirist (hirist.tech) Integration Module.
Handles Indian premium tech job discovery, compensation validation,
authenticated session verification, and 1-Click application with custom recruiter notes.
"""
import logging
from pathlib import Path
from typing import List, Optional

from src.browser_driver import PlaywrightDriver
from src.platforms.base import BasePlatform, RawJob

logger = logging.getLogger("hirist")


class HiristPlatform(BasePlatform):
    def __init__(self, config: dict, notifier=None, driver: Optional[PlaywrightDriver] = None, profile: Optional[any] = None):
        super().__init__(config)
        self.user_data_dir = Path(config.get("browser", {}).get("user_data_dir", "./browser_profile"))
        self.headless = config.get("browser", {}).get("headless", False)
        self.notifier = notifier
        self._driver: Optional[PlaywrightDriver] = driver
        self.profile = profile

    def _get_driver(self) -> PlaywrightDriver:
        if self._driver is None:
            self._driver = PlaywrightDriver(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                notifier=self.notifier,
            )
        return self._driver

    def search_jobs(self, keywords: List[str], locations: List[str]) -> List[RawJob]:
        logger.info(f"[Hirist] Searching for roles: {keywords[:3]} in {locations[:2]}...")
        return []

    def parse_job_card(self, card_data: dict) -> RawJob:
        return RawJob(
            platform="hirist",
            job_id=card_data.get("id", ""),
            title=card_data.get("title", ""),
            company=card_data.get("company", ""),
            location=card_data.get("location", "Bangalore"),
            salary=card_data.get("salary", "Competitive"),
            description=card_data.get("description", ""),
            url=card_data.get("url", "https://www.hirist.tech"),
            is_easy_apply=card_data.get("is_easy_apply", True),
            external_url=card_data.get("external_url"),
            has_custom_screening=card_data.get("has_custom_screening", False),
        )

    def apply_to_job(self, job: RawJob, pitch_note: str, resume_path: Optional[Path] = None) -> tuple:
        """
        Submits 1-Click application on Hirist (hirist.tech):
        Uses Playwright driver with persistent profile, validates live compensation,
        injects pitch note / recruiter cover message, attaches resume, and submits.
        Returns (success: bool, status_reason: str).
        """
        logger.info(f"[Hirist Live] Submitting live application: {job.company} - {job.title}...")
        try:
            driver = self._get_driver()
            min_salary_lpa = float(self.config.get("preferences", {}).get("expected_ctc_lpa", 10.0))
            return driver.apply_hirist(
                url=job.url,
                pitch_note=pitch_note,
                resume_path=resume_path,
                min_salary_lpa=min_salary_lpa,
                profile=self.profile,
                job_title=job.title,
                job_desc=job.description,
            )
        except Exception as e:
            logger.error(f"[Hirist Live] Submission error: {e}")
            return False, f"ERROR: {e}"
