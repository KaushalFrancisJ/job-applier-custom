"""
Markdown Report Generator.
Generates comprehensive daily audit reports in reports/daily_report_YYYY-MM-DD.md.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class ReportGenerator:
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        try:
            self.reports_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def generate_daily_report(self, all_jobs: List[dict], run_metadata: dict = None) -> Path:
        today_str = datetime.now().strftime("%Y-%m-%d")
        report_file = self.reports_dir / f"daily_report_{today_str}.md"

        # Filter jobs for today
        today_jobs = [j for j in all_jobs if j.get("applied_at", "").startswith(today_str)]
        applied = [j for j in today_jobs if j.get("status") == "APPLIED"]
        action_req = [j for j in today_jobs if j.get("status") == "ACTION_REQUIRED"]
        skipped = [j for j in today_jobs if j.get("status") == "FILTERED_OUT"]
        quota_queue = [j for j in all_jobs if j.get("status") == "QUOTA_EXHAUSTED"]

        lines = [
            f"# 🚀 Job Application & Watcher Report — {today_str}",
            "",
            f"> **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}  ",
            f"> **Status:** Active Watcher Mode | **Target CTC:** ≥ 10 LPA | **Locations:** Chennai, Bangalore, Remote, India",
            "",
            "## 📊 Daily Summary",
            "",
            "| Metric | Count | Notes |",
            "| :--- | :---: | :--- |",
            f"| **Total Processed Today** | **{len(today_jobs)}** | Jobs discovered across Wellfound, Instahyre, Cutshort, Hirist, LinkedIn & Naukri |",
            f"| ✅ **Auto-Applied** | **{len(applied)}** | Successfully submitted with custom pitch |",
            f"| ⏸️ **Quota Queue (Cooldown)** | **{len(quota_queue)}** | Queued for auto-apply upon weekly quota slot unlock |",
            f"| ⚠️ **Action Required** | **{len(action_req)}** | Needs your manual submission or external test |",
            f"| 🚫 **Filtered Out** | **{len(skipped)}** | Pure ML excluded / salary < 10 LPA / mismatch |",
            "",
        ]

        # Action Required Section
        lines.append("## ⚠️ Action Required Jobs & Smart Shortlists")
        lines.append("These jobs match your profile and target salary (≥ 10 LPA). For LinkedIn Smart Shortlists and external ATS postings, click the direct link and paste your pre-drafted pitch note (100% account safe).")
        lines.append("")
        if not action_req:
            lines.append("_No pending actions right now. All matching jobs were submitted automatically._\n")
        else:
            lines.append("| Platform | Company | Role | Match | Tailored Pitch to Copy | Reason / Action |")
            lines.append("| :---: | :--- | :--- | :---: | :--- | :--- |")
            for j in action_req:
                p_name = j.get("platform", "LinkedIn").capitalize()
                url_link = f"[{j.get('title')}]({j.get('url')})" if j.get("url") else j.get("title")
                score = f"{j.get('match_score', 80):.0f}%"
                pitch = j.get("pitch_note", "") or "Apply with primary resume."
                if len(pitch) > 130:
                    pitch = pitch[:127] + "..."
                notes = j.get("action_notes", "Manual 1-click apply")
                lines.append(
                    f"| **{p_name}** | **{j.get('company')}** | {url_link} | {score} | *\"{pitch}\"* | {notes} |"
                )
            lines.append("")

        # Successfully Applied Section
        lines.append("## ✅ Successfully Applied Jobs")
        if not applied:
            lines.append("_No jobs auto-applied in the current cycle yet._\n")
        else:
            lines.append("| Platform | Company | Role | Location | Match Score | Pitch Note Used |")
            lines.append("| :---: | :--- | :--- | :--- | :---: | :--- |")
            for j in applied:
                pitch_preview = j.get("pitch_note", "")
                if len(pitch_preview) > 120:
                    pitch_preview = pitch_preview[:117] + "..."
                lines.append(
                    f"| **{j.get('platform', 'Wellfound').capitalize()}** | **{j.get('company')}** | [{j.get('title')}]({j.get('url')}) | {j.get('location')} | {j.get('match_score', 85):.0f}% | *\"{pitch_preview}\"* |"
                )
            lines.append("")

        # Platform Quota Cooldown & Recovery Queue Section
        lines.append("## ⏸️ Platform Quota Cooldown & Recovery Queue")
        lines.append("These high-matching jobs were queued because a platform's weekly limit (e.g. YC Work at a Startup 5 apps/week) was reached. They will be auto-applied in priority order the moment rolling quota slots unlock.")
        lines.append("")
        if not quota_queue:
            lines.append("_No platform quotas currently active. All platforms ready._\n")
        else:
            # Sort by match score descending
            sorted_quota = sorted(quota_queue, key=lambda x: x.get("match_score", 0), reverse=True)
            lines.append("| Priority | Platform | Company | Role | Match Score | Status / Unlock Note |")
            lines.append("| :---: | :---: | :--- | :--- | :---: | :--- |")
            for idx, j in enumerate(sorted_quota, 1):
                p_name = j.get("platform", "").capitalize()
                c_name = j.get("company", "YC Startup")
                t_link = f"[{j.get('title')}]({j.get('url')})" if j.get("url") else j.get("title")
                score = f"{j.get('match_score', 0):.0f}%"
                note = j.get("action_notes", "Queued for weekly quota reset")
                lines.append(f"| #{idx} | **{p_name}** | {c_name} | {t_link} | {score} | {note} |")
            lines.append("")

        # Filtered / Excluded Section
        lines.append("## 🚫 Filtered / Excluded Jobs")
        if not skipped:
            lines.append("_No jobs filtered out yet._\n")
        else:
            lines.append("<details><summary>Click to view skipped jobs & rejection reasons</summary>\n")
            lines.append("| Platform | Company | Role | Filter Reason |")
            lines.append("| :---: | :--- | :--- | :--- |")
            for j in skipped:
                lines.append(
                    f"| {j.get('platform', '').capitalize()} | {j.get('company')} | {j.get('title')} | {j.get('action_notes') or 'Filtered'} |"
                )
            lines.append("\n</details>\n")

        lines.append("---")
        lines.append("*Generated automatically by your custom Job Applier Watcher.*")

        content = "\n".join(lines)
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(content)
            return report_file
        except (PermissionError, OSError):
            import tempfile
            fallback_dir = Path(tempfile.gettempdir()) / "job_applier_custom" / "reports"
            try:
                fallback_dir.mkdir(parents=True, exist_ok=True)
                fallback_file = fallback_dir / report_file.name
                with open(fallback_file, "w", encoding="utf-8") as f:
                    f.write(content)
                return fallback_file
            except Exception:
                return report_file
