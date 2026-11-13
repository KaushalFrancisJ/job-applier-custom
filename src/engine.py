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
from src.browser_driver import PlaywrightDriver
from src.discovery import JobDiscoveryEngine
from src.matcher import JobMatcher
from src.notifier import AlertNotifier
from src.platforms.cutshort import CutshortPlatform
from src.platforms.hirist import HiristPlatform
from src.platforms.instahyre import InstahyrePlatform
from src.platforms.linkedin import LinkedInPlatform
from src.platforms.naukri import NaukriPlatform
from src.platforms.wellfound import WellfoundPlatform
from src.platforms.workatastartup import WorkAtAStartupPlatform
from src.reporter import ReportGenerator
from src.state_manager import JobRecord, StateManager
from src.quota_manager import PlatformQuotaManager

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
        self.quota_mgr = PlatformQuotaManager(self.state_mgr)
        self.reporter = ReportGenerator(self.reports_dir)
        self.discovery = JobDiscoveryEngine(self.config)
        self.notifier = AlertNotifier(self.config)

        # Shared browser driver across platforms
        self.driver = PlaywrightDriver(
            user_data_dir=Path(self.config.get("browser", {}).get("user_data_dir", "./browser_profile")),
            headless=self.config.get("browser", {}).get("headless", False),
            notifier=self.notifier,
        )

        # Platforms
        self.platforms = {
            "wellfound": WellfoundPlatform(self.config, notifier=self.notifier, driver=self.driver),
            "workatastartup": WorkAtAStartupPlatform(self.config, notifier=self.notifier, driver=self.driver),
            "cutshort": CutshortPlatform(self.config, notifier=self.notifier, driver=self.driver),
            "instahyre": InstahyrePlatform(self.config, notifier=self.notifier, driver=self.driver),
            "hirist": HiristPlatform(self.config, notifier=self.notifier, driver=self.driver, profile=self.profile),
            "linkedin": LinkedInPlatform(self.config),
            "naukri": NaukriPlatform(self.config),
        }

    def run_sweep(self, target_platform: str = "all") -> Dict[str, any]:
        """
        Executes one complete sweep:
        1. Discovers jobs
        2. Filters duplicates and irrelevant roles (pure ML, low salary)
        3. Prioritizes Wellfound -> WorkAtAStartup -> Instahyre -> Cutshort -> Hirist -> LinkedIn -> Naukri
        4. Applies or marks Action Required
        5. Generates Daily Report
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Starting job discovery sweep (Platform: {target_platform})...")
        driver_for_discovery = None if self.dry_run else self.driver
        discovered = self.discovery.fetch_live_job_opportunities(driver=driver_for_discovery, state_mgr=self.state_mgr)

        if target_platform and target_platform.lower() != "all":
            discovered = [j for j in discovered if j.platform.lower() == target_platform.lower()]

        sweep_stats = {
            "total_found": len(discovered),
            "applied": 0,
            "action_required": 0,
            "filtered_out": 0,
            "skipped_known": 0,
            "dry_run_matches": 0,
        }

        # Sort jobs according to platform priority: Wellfound -> WorkAtAStartup -> Instahyre -> Cutshort -> Hirist -> LinkedIn -> Naukri
        priority_order = {
            "wellfound": 0,
            "workatastartup": 1,
            "instahyre": 2,
            "cutshort": 3,
            "hirist": 4,
            "linkedin": 5,
            "naukri": 6,
        }

        def platform_priority(job):
            return priority_order.get(job.platform, 99)

        discovered.sort(key=platform_priority)

        # Log platform quota status and check for recovery of pending QUOTA_EXHAUSTED roles
        print(f"  📊 Quota Status: {self.quota_mgr.format_summary('workatastartup')}")
        waas_status = self.quota_mgr.get_quota_status("workatastartup")
        if waas_status["available_slots"] > 0 and waas_status["pending_queue_count"] > 0:
            recovered = self.recover_quota_exhausted_jobs("workatastartup")
            if recovered > 0:
                sweep_stats["applied"] += recovered

        for raw_job in discovered:
            job_id = raw_job.job_id
            if self.state_mgr.is_known(job_id, url=raw_job.url):
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
                company=raw_job.company,
                platform=raw_job.platform,
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

            # If action required (external link, custom test, LinkedIn Smart Shortlist, etc.)
            if eval_res.action_required or raw_job.platform == "linkedin":
                action_note = eval_res.action_notes
                if raw_job.platform == "linkedin":
                    action_note = f"LinkedIn Smart Shortlist ({eval_res.score:.0f}% match): Pre-drafted pitch ready. Click link to apply safely."
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
                    action_notes=action_note,
                    match_score=eval_res.score,
                )
                if not self.dry_run:
                    self.state_mgr.record_job(record)
                sweep_stats["action_required"] += 1
                print(f"  ⚠️ Action Required [{raw_job.company} - {raw_job.title}]: {action_note}")
                self.notifier.notify_action_required(
                    raw_job.company, raw_job.title, record.url, action_note, eval_res.score
                )
                continue

            # Check if platform has an active weekly quota cap with 0 available slots
            if not self.quota_mgr.can_apply(raw_job.platform):
                status = "QUOTA_EXHAUSTED"
                sweep_stats["action_required"] += 1
                q_status = self.quota_mgr.get_quota_status(raw_job.platform)
                next_str = q_status['next_slot_available_at'].strftime('%Y-%m-%d %H:%M:%S IST') if q_status['next_slot_available_at'] else 'rolling cooldown'
                action_notes = f"Platform weekly quota reached ({q_status['used_slots']}/{q_status['limit']}). Queued in priority retry queue for slot unlock at {next_str}."
                print(f"  ⏸️ Quota Exhausted [{raw_job.platform.capitalize()}]: 0 slots available. Queued in priority recovery queue.")
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
            elif "QUOTA_EXHAUSTED" in status_reason or "RATE_LIMITED" in status_reason:
                status = "QUOTA_EXHAUSTED"
                sweep_stats["action_required"] += 1
                action_notes = "Platform weekly quota reached (5/5). Queued for next weekly quota reset."
                print(f"  ⏸️ Quota Exhausted [{raw_job.platform.capitalize()}]: {status_reason}")
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
            elif self.dry_run:
                status = "DRY_RUN"
                sweep_stats["dry_run_matches"] += 1
                action_notes = f"Dry-run simulation: Matched ({eval_res.score:.0f}%) and ready to apply."
                print(f"  🔍 Dry-Run Match [{raw_job.platform.capitalize()}]: {raw_job.company} - {raw_job.title} ({eval_res.score:.0f}% match)")
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

        # Clean up shared browser driver context
        if hasattr(self, "driver") and self.driver:
            self.driver.close()

        return sweep_stats

    def recover_quota_exhausted_jobs(self, platform: str) -> int:
        """
        Submits applications for top-priority QUOTA_EXHAUSTED jobs
        when rolling weekly quota cooldown slots unlock.
        """
        status = self.quota_mgr.get_quota_status(platform)
        avail = status["available_slots"]
        if avail <= 0:
            return 0

        pending = self.quota_mgr.get_pending_jobs(platform)
        if not pending:
            return 0

        recovered_count = 0
        print(f"\n🔄 [Quota Recovery] {avail} slot(s) unlocked on {platform.capitalize()}! Processing top priority queued jobs...")

        from src.platforms.base import RawJob
        for job_dict in pending[:avail]:
            job_id = job_dict.get("job_id")
            url = job_dict.get("url")
            company = job_dict.get("company")
            title = job_dict.get("title")
            pitch_note = job_dict.get("pitch_note", "")

            print(f"  🎯 Applying to queued role [{job_dict.get('match_score')}%]: {company} - {title} ({url})...")
            platform_handler = self.platforms.get(platform)
            if not platform_handler or self.dry_run:
                continue

            raw_job = RawJob(
                platform=platform,
                job_id=job_id,
                title=title,
                company=company,
                location=job_dict.get("location", ""),
                salary=job_dict.get("salary", ""),
                url=url,
            )
            res = platform_handler.apply_to_job(
                raw_job, pitch_note, resume_path=self.profile.resume_pdf_path
            )
            success = False
            reason = ""
            if isinstance(res, tuple):
                success, reason = res
            else:
                success = bool(res)

            if success:
                record = JobRecord(
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=job_dict.get("location", ""),
                    salary=job_dict.get("salary", ""),
                    url=url,
                    platform=platform,
                    status="APPLIED",
                    applied_at=datetime.now().isoformat(),
                    pitch_note=pitch_note,
                    action_notes="Recovered from quota queue and submitted live upon weekly quota slot unlock.",
                    match_score=job_dict.get("match_score", 0),
                )
                self.state_mgr.record_job(record)
                recovered_count += 1
                print(f"  🎉 Successfully applied to queued role: {company} - {title}!")
            elif "QUOTA_EXHAUSTED" in reason:
                print(f"  ⏸️ Platform rejected submission; quota remains locked: {reason}")
                break
            else:
                print(f"  ⚠️ Could not submit queued role: {reason}")

        return recovered_count
