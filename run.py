"""
CLI Entrypoint for Job Applier & Watcher.

Usage:
  python run.py --watch              # Run continuous watcher daemon (morning to evening)
  python run.py --once               # Run a single immediate job sweep
  python run.py --dry-run            # Test discovery and matching without applying
  python run.py --platform wellfound # Target specific platform
"""
import argparse
from pathlib import Path
import sys

# Ensure src is importable
WORKSPACE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE_DIR))

from src.engine import JobApplierEngine
from src.watcher import JobWatcherDaemon


def main():
    parser = argparse.ArgumentParser(description="Automated Job Applier & Persistent Watcher")
    parser.add_argument("--watch", action="store_true", help="Start continuous morning-to-evening watcher daemon")
    parser.add_argument("--once", action="store_true", help="Run a single job sweep and exit")
    parser.add_argument("--dry-run", action="store_true", help="Simulate discovery and matching without submitting")
    parser.add_argument("--platform", type=str, default="all", choices=["all", "wellfound", "workatastartup", "cutshort", "instahyre", "hirist", "linkedin", "naukri"], help="Target portal")

    args = parser.parse_args()

    # Default to single sweep if neither watch nor once specified
    if args.watch:
        daemon = JobWatcherDaemon(WORKSPACE_DIR, dry_run=args.dry_run, target_platform=args.platform)
        daemon.start_loop()
    else:
        engine = JobApplierEngine(WORKSPACE_DIR, dry_run=args.dry_run)
        stats = engine.run_sweep(target_platform=args.platform)
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print(f"Total Discovered: {stats['total_found']}")
        if args.dry_run:
            print(f"Dry-Run Matched:  {stats.get('dry_run_matches', 0)}")
        print(f"Auto-Applied:     {stats['applied']}")
        print(f"Action Required:  {stats['action_required']}")
        print(f"Filtered Out:     {stats['filtered_out']}")
        print(f"Already Known:    {stats['skipped_known']}")
        print("=" * 50)


if __name__ == "__main__":
    main()
