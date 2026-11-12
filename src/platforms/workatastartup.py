"""
Work at a Startup (workatastartup.com - Y Combinator) Integration Module.
Handles YC tech startup job discovery, founder note injection,
persistent candidate profile verification, and 1-Click founder application.
"""
import logging
from pathlib import Path
from typing import List, Optional

from src.browser_driver import PlaywrightDriver
from src.platforms.base import BasePlatform, RawJob

logger = logging.getLogger("workatastartup")


class WorkAtAStartupPlatform(BasePlatform):
    def __init__(self, config: dict, notifier=None, driver: Optional[PlaywrightDriver] = None):
        super().__init__(config)
        self.user_data_dir = Path(config.get("browser", {}).get("user_data_dir", "./browser_profile"))
        self.headless = config.get("browser", {}).get("headless", False)
        self.notifier = notifier
        self._driver: Optional[PlaywrightDriver] = driver

    def _get_driver(self) -> PlaywrightDriver:
        if self._driver is None:
            self._driver = PlaywrightDriver(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                notifier=self.notifier,
            )
        return self._driver

    def search_jobs(self, keywords: List[str], locations: List[str]) -> List[RawJob]:
        logger.info(f"[WorkAtAStartup] Searching for roles: {keywords[:3]} in {locations[:2]}...")
        return []

    def parse_job_card(self, card_data: dict) -> RawJob:
        return RawJob(
            platform="workatastartup",
            job_id=card_data.get("id", ""),
            title=card_data.get("title", ""),
            company=card_data.get("company", ""),
            location=card_data.get("location", "Remote (India)"),
            salary=card_data.get("salary", "Competitive"),
            description=card_data.get("description", ""),
            url=card_data.get("url", "https://www.workatastartup.com"),
            is_easy_apply=card_data.get("is_easy_apply", True),
            external_url=card_data.get("external_url"),
            has_custom_screening=card_data.get("has_custom_screening", False),
        )

    def apply_to_job(self, job: RawJob, pitch_note: str, resume_path: Optional[Path] = None) -> tuple:
        """
        Submits 1-Click Application on Work at a Startup (workatastartup.com):
        Uses Playwright driver with persistent profile, checks Cloudflare,
        injects custom founder pitch note into modal, confirms application.
        Returns (success: bool, status_reason: str).
        """
        logger.info(f"[WorkAtAStartup Live] Submitting live application: {job.company} - {job.title}...")
        try:
            driver = self._get_driver()
            min_salary_lpa = float(self.config.get("preferences", {}).get("expected_ctc_lpa", 10.0))
            return driver.apply_workatastartup(
                url=job.url,
                pitch_note=pitch_note,
                resume_path=resume_path,
                min_salary_lpa=min_salary_lpa,
            )
        except Exception as e:
            logger.error(f"[WorkAtAStartup Live] Submission error: {e}")
            return False, f"ERROR: {e}"
