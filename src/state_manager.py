"""
State persistence and deduplication manager.
Tracks all discovered, applied, and action-required jobs in state/applications.json.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

from src.utils import sanitize_unicode


@dataclass
class JobRecord:
    job_id: str
    title: str
    company: str
    location: str
    salary: str
    url: str
    platform: str
    status: str  # 'APPLIED', 'ACTION_REQUIRED', 'FILTERED_OUT', 'FAILED'
    applied_at: str
    pitch_note: str = ""
    action_notes: str = ""
    match_score: float = 0.0
    external_url: str = ""


class StateManager:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.jobs: Dict[str, dict] = {}
        self._load()

    def _load(self):
        import tempfile
        fallback_file = Path(tempfile.gettempdir()) / "job_applier_custom" / "state" / self.state_file.name

        workspace_data = {}
        fallback_data = {}

        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        workspace_data = json.loads(content)
            except Exception as e:
                print(f"[StateManager] Warning reading {self.state_file}: {e}")

        if fallback_file.exists():
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        fallback_data = json.loads(content)
            except Exception:
                pass

        # Merge both dictionaries, prioritizing whichever has newer/more records
        self.jobs = {**workspace_data, **fallback_data}
        if not self.jobs:
            self.jobs = {}
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            self._save()

    def _save(self):
        try:
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            # Fallback to user temp storage if workspace is write-locked (e.g. sandbox environment)
            import tempfile
            fallback_dir = Path(tempfile.gettempdir()) / "job_applier_custom" / "state"
            try:
                fallback_dir.mkdir(parents=True, exist_ok=True)
                fallback_file = fallback_dir / self.state_file.name
                with open(fallback_file, "w", encoding="utf-8") as f:
                    json.dump(self.jobs, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    @staticmethod
    def generate_id(platform: str, title: str, company: str, url: str = "") -> str:
        raw = f"{platform}:{title.strip().lower()}:{company.strip().lower()}:{url.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def is_known(self, job_id: str, url: str = "") -> bool:
        if job_id in self.jobs:
            return True
        if url:
            clean_url = url.split("?")[0].rstrip("/").lower()
            for j in self.jobs.values():
                j_url = j.get("url", "").split("?")[0].rstrip("/").lower()
                ext_url = j.get("external_url", "").split("?")[0].rstrip("/").lower()
                if clean_url in (j_url, ext_url) and clean_url:
                    return True
        return False

    def is_url_known(self, url: str) -> bool:
        if not url:
            return False
        clean_url = url.split("?")[0].rstrip("/").lower()
        for j in self.jobs.values():
            j_url = j.get("url", "").split("?")[0].rstrip("/").lower()
            ext_url = j.get("external_url", "").split("?")[0].rstrip("/").lower()
            if clean_url in (j_url, ext_url) and clean_url:
                return True
        return False

    def record_job(self, record: JobRecord):
        rec_dict = asdict(record)
        for k, v in rec_dict.items():
            if isinstance(v, str):
                rec_dict[k] = sanitize_unicode(v)
        self.jobs[record.job_id] = rec_dict
        self._save()

    def get_record(self, job_id: str) -> Optional[dict]:
        return self.jobs.get(job_id)

    def get_today_counts(self) -> Dict[str, int]:
        today_str = datetime.now().strftime("%Y-%m-%d")
        counts = {"applied": 0, "action_required": 0, "filtered_out": 0}
        for j in self.jobs.values():
            if j.get("applied_at", "").startswith(today_str):
                st = j.get("status")
                if st == "APPLIED":
                    counts["applied"] += 1
                elif st == "ACTION_REQUIRED":
                    counts["action_required"] += 1
                elif st == "FILTERED_OUT":
                    counts["filtered_out"] += 1
        return counts

    def get_all_records(self) -> List[dict]:
        return list(self.jobs.values())
