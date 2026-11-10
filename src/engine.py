"""
Core Job Applier Engine.
Orchestrates job discovery, deduplication, filtering, pitch generation,
auto-application, action flagging, and daily audit reporting.
"""
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List

from src.candidate_profile import load_candidate_profile
from src.discovery import JobDiscoveryEngine
from src.matcher import JobMatcher
from src.notifier import AlertNotifier
from src.platforms.linkedin import LinkedInPlatform
from src.platforms.naukri import NaukriPlatform
from src.platforms.wellfound import WellfoundPlatform
from src.reporter import ReportGenerator
from src.state_manager import JobRecord, StateManager

logger = logging.getLogger("engine")


class JobApplierEngine:
    def __init__(self, workspace_dir: Path, dry_run: bool = False):
        self.workspace_dir = workspace_dir
        self.dry_run = dry_run
        self.config_path = workspace_dir / "config.json"
        self.cv_path = workspace_dir / "cv.md"
        self.state_path = workspace_dir / "state" / "applications.json"
        self.reports_dir = workspace_dir / "reports"

        # Load configurations and candidate profile
        import json

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.profile = load_candidate_profile(self.config, self.cv_path)
        self.matcher = JobMatcher(self.profile, self.config)
        self.state_mgr = StateManager(self.state_path)
        self.reporter = ReportGenerator(self.reports_dir)
        self.discovery = JobDiscoveryEngine(self.config)
        self.notifier = AlertNotifier(self.config)

        # Platforms
        self.platforms = {
            "wellfound": WellfoundPlatform(self.config, notifier=self.notifier),
            "linkedin": LinkedInPlatform(self.config),
            "naukri": NaukriPlatform(self.config),
        }

    def run_sweep(self) -> Dict[str, any]:
        """
        Executes one complete sweep:
        1. Discovers jobs
        2. Filters duplicates and irrelevant roles (pure ML, low salary)
        3. Prioritizes Wellfound
        4. Applies or marks Action Required
        5. Generates Daily Report
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Starting job discovery sweep...")
        discovered = self.discovery.fetch_live_job_opportunities()

        sweep_stats = {
            "total_found": len(discovered),
            "applied": 0,
            "action_required": 0,
            "filtered_out": 0,
            "skipped_known": 0,
        }

        # Sort jobs so Wellfound is prioritized first
        def platform_priority(job):
            return 0 if job.platform == "wellfound" else 1

        discovered.sort(key=platform_priority)

        for raw_job in discovered:
            job_id = raw_job.job_id
            if self.state_mgr.is_known(job_id):
                sweep_stats["skipped_known"] += 1
                continue

            # Evaluate with Matcher
            eval_res = self.matcher.evaluate_job(
                title=raw_job.title,
                description=raw_job.description,
                location=raw_job.location,
                salary_str=raw_job.salary,
                external_url=raw_job.external_url,
                has_custom_questions=raw_job.has_custom_screening,
            )

            now_str = datetime.now().isoformat()

            if not eval_res.is_match:
                # Log as filtered out
                record = JobRecord(
                    job_id=job_id,
                    title=raw_job.title,
                    company=raw_job.company,
                    location=raw_job.location,
                    salary=raw_job.salary,
                    url=raw_job.url,
                    platform=raw_job.platform,
                    status="FILTERED_OUT",
                    applied_at=now_str,
                    action_notes=eval_res.reason,
                    match_score=eval_res.score,
                )
                if not self.dry_run:
                    self.state_mgr.record_job(record)
                sweep_stats["filtered_out"] += 1
                print(f"  🚫 Filtered [{raw_job.company} - {raw_job.title}]: {eval_res.reason}")
                continue

            # If action required (external link, custom test, etc.)
            if eval_res.action_required:
                record = JobRecord(
                    job_id=job_id,
                    title=raw_job.title,
                    company=raw_job.company,
                    location=raw_job.location,
                    salary=raw_job.salary,
                    url=raw_job.external_url or raw_job.url,
                    platform=raw_job.platform,
                    status="ACTION_REQUIRED",
                    applied_at=now_str,
                    pitch_note=eval_res.pitch_note,
                    action_notes=eval_res.action_notes,
                    match_score=eval_res.score,
                )
                if not self.dry_run:
                    self.state_mgr.record_job(record)
                sweep_stats["action_required"] += 1
                print(f"  ⚠️ Action Required [{raw_job.company} - {raw_job.title}]: {eval_res.action_notes}")
                self.notifier.notify_action_required(
                    raw_job.company, raw_job.title, record.url, eval_res.action_notes, eval_res.score
                )
                continue

            # Eligible for Direct / 1-Click Auto Apply
            platform_handler = self.platforms.get(raw_job.platform)
            applied_success = False
            status_reason = ""
            if not self.dry_run and platform_handler:
                res = platform_handler.apply_to_job(
                    raw_job, eval_res.pitch_note, resume_path=self.profile.resume_pdf_path
                )
                if isinstance(res, tuple):
                    applied_success, status_reason = res
                else:
                    applied_success = bool(res)

            if applied_success:
                status = "APPLIED"
                sweep_stats["applied"] += 1
                action_notes = "Submitted live via browser with customized pitch and resume."
                print(f"  ✅ Auto-Applied [{raw_job.platform.capitalize()}]: {raw_job.company} - {raw_job.title} ({eval_res.score:.0f}% match)")
            elif "INELIGIBLE" in status_reason:
                status = "FILTERED_OUT"
                sweep_stats["filtered_out"] += 1
                action_notes = "Ineligible: Recruiter set relocation or timezone constraints."
                print(f"  🚫 Ineligible [{raw_job.company} - {raw_job.title}]: Location/timezone constraint")
            elif "EXPIRED" in status_reason or "404" in status_reason:
                status = "EXPIRED"
                sweep_stats["filtered_out"] += 1
                action_notes = "Listing expired or no longer available."
                print(f"  🚫 Expired [{raw_job.company} - {raw_job.title}]: Listing is closed")
            else:
                status = "ACTION_REQUIRED"
                sweep_stats["action_required"] += 1
                action_notes = f"Requires manual action: {status_reason}"
                print(f"  ⚠️ Action Required [{raw_job.platform.capitalize()}]: {raw_job.company} - {raw_job.title} ({status_reason})")

            record = JobRecord(
                job_id=job_id,
                title=raw_job.title,
                company=raw_job.company,
                location=raw_job.location,
                salary=raw_job.salary,
                url=raw_job.url,
                platform=raw_job.platform,
                status=status,
                applied_at=now_str,
                pitch_note=eval_res.pitch_note,
                action_notes=action_notes,
                match_score=eval_res.score,
            )
            if not self.dry_run:
                self.state_mgr.record_job(record)

        # Generate markdown report
        all_records = self.state_mgr.get_all_records()
        report_path = self.reporter.generate_daily_report(all_records)
        print(f"📄 Updated daily report: {report_path.name}")

        # Clean up browser driver context
        for p in self.platforms.values():
            if hasattr(p, "_driver") and p._driver:
                p._driver.close()

        return sweep_stats
