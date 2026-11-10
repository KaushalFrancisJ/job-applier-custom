"""
Base class definition for job portal platform integrations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RawJob:
    platform: str
    job_id: str
    title: str
    company: str
    location: str
    salary: str
    description: str
    url: str
    is_easy_apply: bool = True
    external_url: Optional[str] = None
    has_custom_screening: bool = False


class BasePlatform(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def search_jobs(self, keywords: List[str], locations: List[str]) -> List[RawJob]:
        """Discovers jobs on the portal matching keywords and locations."""
        pass

    @abstractmethod
    def apply_to_job(self, job: RawJob, pitch_note: str, resume_path: Optional[Path] = None) -> bool:
        """Submits an application to the specified job with the given pitch and optional resume PDF."""
        pass
