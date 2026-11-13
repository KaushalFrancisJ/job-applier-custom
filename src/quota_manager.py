"""
Platform Quota and Rate Limit Manager.
Tracks rolling application quotas (e.g. Work at a Startup 5 apps / 7 days),
manages the priority recovery queue of QUOTA_EXHAUSTED jobs, and automatically
applies to queued roles when quota cooldown slots reopen.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quota_manager")


class PlatformQuotaManager:
    # Supported rate-limiting & rolling quota rules per platform
    PLATFORM_RULES = {
        "workatastartup": {
            "limit": 5,
            "window_days": 7,
            "description": "Y Combinator 5 applications per rolling 7-day window",
        }
    }

    def __init__(self, state_mgr):
        self.state_mgr = state_mgr

    def get_quota_status(self, platform: str) -> Dict[str, any]:
        """
        Calculates the live quota status for a platform based on recorded applications.
        Returns a dict with limit, used_slots, available_slots, next_slot_available_at, and pending_queue_count.
        """
        rule = self.PLATFORM_RULES.get(platform.lower())
        if not rule:
            # Platform has no known strict weekly quota limit
            return {
                "platform": platform,
                "is_rate_limited_platform": False,
                "limit": None,
                "used_slots": 0,
                "available_slots": 999,
                "next_slot_available_at": None,
                "pending_queue_count": 0,
            }

        limit = rule["limit"]
        window = timedelta(days=rule["window_days"])
        now = datetime.now()

        # Find all genuine APPLIED jobs for this platform
        applied_timestamps = []
        for j in self.state_mgr.jobs.values():
            if j.get("platform", "").lower() == platform.lower() and j.get("status") == "APPLIED":
                ts_str = j.get("applied_at")
                if ts_str:
                    try:
                        dt = datetime.fromisoformat(ts_str)
                        applied_timestamps.append(dt)
                    except Exception:
                        pass

        applied_timestamps.sort()

        # Filter to applications inside the rolling window
        active_in_window = [ts for ts in applied_timestamps if now - ts < window]
        used_slots = len(active_in_window)
        available_slots = max(0, limit - used_slots)

        next_slot_available_at = None
        if used_slots >= limit and active_in_window:
            # Oldest application in active window unlocks first
            oldest_active = active_in_window[0]
            next_slot_available_at = oldest_active + window

        # Count pending QUOTA_EXHAUSTED jobs
        pending_jobs = self.get_pending_jobs(platform)

        return {
            "platform": platform,
            "is_rate_limited_platform": True,
            "limit": limit,
            "used_slots": used_slots,
            "available_slots": available_slots,
            "next_slot_available_at": next_slot_available_at,
            "pending_queue_count": len(pending_jobs),
        }

    def can_apply(self, platform: str) -> bool:
        """Returns True if the platform currently has available application slots."""
        status = self.get_quota_status(platform)
        return status["available_slots"] > 0

    def get_pending_jobs(self, platform: str) -> List[dict]:
        """
        Returns all QUOTA_EXHAUSTED jobs for the given platform,
        prioritized by match_score descending so high-value roles are applied first.
        """
        pending = []
        for j in self.state_mgr.jobs.values():
            if (
                j.get("platform", "").lower() == platform.lower()
                and j.get("status") == "QUOTA_EXHAUSTED"
            ):
                pending.append(j)

        pending.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return pending

    def format_summary(self, platform: str) -> str:
        """Returns a user-friendly summary of the quota status."""
        status = self.get_quota_status(platform)
        if not status["is_rate_limited_platform"]:
            return f"{platform.capitalize()}: Unlimited / No quota limit"

        limit = status["limit"]
        used = status["used_slots"]
        avail = status["available_slots"]
        pending = status["pending_queue_count"]
        next_dt = status["next_slot_available_at"]

        if avail > 0:
            return f"{platform.capitalize()}: {avail}/{limit} slots available ({pending} queued in recovery)"
        else:
            next_str = next_dt.strftime("%Y-%m-%d %H:%M:%S IST") if next_dt else "calculating..."
            return (
                f"{platform.capitalize()}: Quota exhausted ({used}/{limit} active). "
                f"Next slot unlocks at {next_str} ({pending} jobs queued in priority order)"
            )
