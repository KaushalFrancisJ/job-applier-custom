"""
Continuous Watcher Daemon.
Runs periodically throughout the working day (e.g. morning to evening),
performing automated discovery, smart filtering, auto-applying, and report updates.
"""
from datetime import datetime, time
import logging
from pathlib import Path
import random
import signal
import sys
import time as time_module
from typing import Optional

from src.engine import JobApplierEngine

logger = logging.getLogger("watcher")


class JobWatcherDaemon:
    def __init__(self, workspace_dir: Path, dry_run: bool = False):
        self.workspace_dir = workspace_dir
        self.dry_run = dry_run
        self.engine = JobApplierEngine(workspace_dir, dry_run=dry_run)
        self.running = True
        self.cycle_count = 0

        # Load watcher config
        watcher_cfg = self.engine.config.get("watcher", {})
        self.interval_seconds = int(watcher_cfg.get("interval_minutes", 30)) * 60
        self.jitter_seconds = int(watcher_cfg.get("jitter_minutes", 5)) * 60
        self.active_hours = watcher_cfg.get("active_hours", {"start": "09:00", "end": "19:00"})

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame):
        print("\n\n🛑 [Watcher] Graceful shutdown triggered. Saving state and finalizing reports...")
        self.running = False

    def is_within_active_window(self) -> bool:
        """Checks if current local time is within configured active hours."""
        now = datetime.now().time()
        start_parts = [int(p) for p in self.active_hours.get("start", "09:00").split(":")]
        end_parts = [int(p) for p in self.active_hours.get("end", "19:00").split(":")]
        start_time = time(start_parts[0], start_parts[1])
        end_time = time(end_parts[0], end_parts[1])
        return start_time <= now <= end_time

    def start_loop(self):
        print("=" * 70)
        print("🤖 JOB APPLIER PERSISTENT WATCHER INITIALIZED")
        print(f"Candidate: {self.engine.profile.name} | Target: ≥ {self.engine.profile.expected_ctc_lpa} LPA")
        print(f"Active Window: {self.active_hours.get('start')} - {self.active_hours.get('end')} IST")
        print(f"Interval: ~{self.interval_seconds // 60} minutes (with jitter)")
        print(f"Prioritizing: Wellfound ➔ LinkedIn ➔ Naukri")
        print("Press Ctrl+C at any time in the evening to cleanly stop.")
        print("=" * 70)

        while self.running:
            self.cycle_count += 1
            now_dt = datetime.now()
            print(f"\n--- [Cycle #{self.cycle_count}] {now_dt.strftime('%Y-%m-%d %H:%M:%S IST')} ---")

            # Execute job sweep
            try:
                stats = self.engine.run_sweep()
                print(
                    f"✨ Sweep finished: {stats['applied']} Applied, "
                    f"{stats['action_required']} Action Required, "
                    f"{stats['filtered_out']} Filtered, {stats['skipped_known']} Already seen."
                )
            except Exception as e:
                print(f"❌ Error during cycle sweep: {e}")

            if not self.running:
                break

            # Calculate sleep duration with jitter to avoid anti-bot detection
            jitter = random.uniform(-self.jitter_seconds, self.jitter_seconds)
            sleep_time = max(300, self.interval_seconds + jitter)  # Minimum 5 minutes
            next_run_time = datetime.fromtimestamp(time_module.time() + sleep_time)
            print(f"⏳ Sleeping for {sleep_time / 60:.1f} minutes. Next check at {next_run_time.strftime('%H:%M:%S IST')}...")

            # Responsive sleep loop checking for termination every second
            start_sleep = time_module.time()
            while self.running and (time_module.time() - start_sleep < sleep_time):
                time_module.sleep(1)

        print("\n✅ [Watcher] Offline. All states preserved in state/applications.json.")
