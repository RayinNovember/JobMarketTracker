"""Monthly LinkedIn jobs pipeline: scrape, land raw, upsert clean rows, log the run.

Usage:
    uv run python -m projects.linkedin_jobs.run                      # full run from config.yaml
    uv run python -m projects.linkedin_jobs.run --limit 25           # small, cheap run
    uv run python -m projects.linkedin_jobs.run --searches "data scientist" --limit 25
    uv run python -m projects.linkedin_jobs.run --retag              # re-apply themes.yaml
    uv run python -m projects.linkedin_jobs.run --rehash             # backfill job_hash
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from core import db, runlog
from core.text import ThemeTagger
from projects.linkedin_jobs import load, scrape
from projects.linkedin_jobs.transform import merge_items, to_row

HERE = Path(__file__).parent
PROJECT = 'linkedin_jobs'

def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Monthly LinkedIn jobs pipeline')
    ap.add_argument('--limit',type=int,help='max jobs persearch (overriades config.yaml)')
    ap.add_argument("--searches", help="comma-separated search terms (overrides config.yaml)")
    ap.add_argument("--retag", action="store_true", help="re-tag stored postings with themes.yaml, then stop")
    ap.add_argument("--rehash", action="store_true", help="recompute job_hash for stored postings, then stop")
    return ap.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = yaml.safe_load((HERE / "config.yaml").read_text())
    tagger = ThemeTagger.from_yaml(HERE / "themes.yaml")
    
    if args.retag:
        with db.connect() as conn:
            n = load.retag_all(conn, tagger)
        print(f"Re-tagged {n} postings with themes.yaml")
        return 0

    if args.rehash:
        with db.connect() as conn:
            n = load.rehash_all(conn)
        print(f"Recomputed job_hash for {n} postings")
        return 0

    searches = [s.strip() for s in args.searches.split(",")] if args.searches else cfg["searches"]
    limit = args.limit or cfg["limit_per_search"]
    params = {"searches": searches, "limit_per_search": limit,"location": cfg["location"], "date_posted": cfg["date_posted"]}
    
    apify = scrape.client()
    with db.connect() as conn:
        run_id = runlog.start_run(conn, PROJECT, params)
        batches, errors, cost = {}, [], 0.0
        try:
            # 1. Scrape: one actor run per search term. A failed search doesn't stop the others.
            for term in searches:
                print(f"Scraping '{term}' (up to {limit})...", flush=True)
                try:
                    items, c = scrape.run_search(apify, cfg, term, limit)
                    batches[term] = items
                    cost += c
                    print(f"  {len(items)} jobs, ${c:.2f}", flush=True)
                except Exception as e:
                    errors.append(f"{term}: {e}")
                    print(f"  FAILED: {e}", file=sys.stderr, flush=True)

            # 2. Transform: merge searches, then one clean row per job.
            merged = merge_items(batches)
            rows = [to_row(item, terms, tagger) for item, terms in merged.values()]

            # 3. Load: raw copy first, then the deduplicating upsert, in one transaction.
            load.insert_raw(conn, run_id, merged)
            new = load.upsert_postings(conn, run_id, rows, date.today())
            conn.commit()

            # 4. Log the outcome.
            if not errors:
                status = "succeeded"
            elif batches:
                status = "succeeded_with_errors"
            else:
                status = "failed"
            runlog.finish_run(conn, run_id, status=status, rows_fetched=len(rows), rows_new=new,
                              cost_usd=cost, error="\n".join(errors) or None)
            print(f"Run {run_id}: {len(rows)} jobs, {new} new, ${cost:.2f}. Status: {status}")
            return 0 if status != "failed" else 1
        except Exception as e:
            runlog.finish_run(conn, run_id, status="failed", cost_usd=cost, error=f"{type(e).__name__}: {e}")
            raise


if __name__ == "__main__":
    sys.exit(main())