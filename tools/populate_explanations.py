#!/usr/bin/env python3
"""
Populate and verify question_explanations table for all Category B questions (Milestone P2).
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_explanations import batch_generate_explanations
from tools.audit_explanations import run_explanations_audit


def main():
    parser = argparse.ArgumentParser(description="Populate question explanations cache")
    parser.add_argument("--force", action="store_true", help="Force recomputation of all explanations")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of questions to process")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without DB write")
    args = parser.parse_args()

    print("[START] Starting Batch Explanations Population for Category B...")
    batch_generate_explanations(
        dry_run=args.dry_run,
        limit=args.limit,
        force_recompute=args.force
    )

    if not args.dry_run:
        print("\n[AUDIT] Running Verification Audit:")
        run_explanations_audit()


if __name__ == "__main__":
    main()
