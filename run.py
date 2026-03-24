"""
run.py — Full pipeline orchestrator. Runs all 4 agents in sequence.

Usage:
    python run.py                  # full run
    python run.py --skip-scrape    # use existing scraped data (skip agent 1)
    python run.py --no-email       # run everything except email delivery
    python run.py --skip-scrape --no-email
"""

import sys
from agent1_scrape  import run as scrape
from agent2_score   import run as score
from agent3_report  import run as build_report
from agent4_deliver import run as deliver


def main():
    skip_scrape = "--skip-scrape" in sys.argv
    no_email    = "--no-email"    in sys.argv

    print("\n  JARVIS AI NEWS AGENT — FULL PIPELINE")
    print("  " + "=" * 40)

    # Agent 1 — scrape sources
    if skip_scrape:
        print("\n[Skipping scrape — using existing data]\n")
    else:
        scrape()

    # Agent 2 — AI scoring
    score()

    # Agent 3 — HTML report
    build_report()

    # Agent 4 — deliver (vault + email)
    if no_email:
        # Temporarily patch env to skip email
        import os
        os.environ["_SKIP_EMAIL"] = "1"
    deliver()

    print("  Pipeline complete.\n")


if __name__ == "__main__":
    main()
