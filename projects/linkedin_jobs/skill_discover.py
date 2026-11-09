"""Module 12, pass 1: draft a skill list from a random sample of stored postings.

Usage:
    uv run python -m projects.linkedin_jobs.skill_discover --sample 20    # a quick look
    uv run python -m projects.linkedin_jobs.skill_discover                # 500 postings

Writes skills_draft.yaml next to this file. Review it, then save it as skills.yaml.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

from core import db
from core.skills import Claude, build_list, extract_open

HERE = Path(__file__).parent

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Discover skills from a sample of postings')
    ap.add_argument('--sample', type=int, default=500, help='number of postings to sample')
    ap.add_argument('--out', type=Path, default=HERE/"skills_draft.yaml", help='where to write the draft skill list')
    args = ap.parse_args(argv)
    
    claude = Claude()
    with db.connect() as conn:
        rows = conn.execute(
            """
            select title, description_text from jobs.postings_dedup
             where description_text is not null
             order by random()
             limit %s
            """,
            (args.sample,),
        ).fetchall()
    print(f'Reading {len(rows)} postings with {claude.model}', flush=True)
    
    counts: Counter = Counter()
    failed = 0
    for i, (title,description) in enumerate(rows,start=1):
        try:
            found = extract_open(claude,f"{title}\n\n{description}")
        except Exception as e:
            failed += 1
            print(f"  skipped one: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            continue
            # Count each phrase once per posting, so one wordy posting can't dominate.
        counts.update({(" ".join(s["name"].lower().split()), s["category"]) for s in found})
        """
        found
        # posting 1
        [{"name": "SQL queries", "category": "technical"},
        {"name": "Presenting to executives", "category": "communication"},
        {"name": "sql queries", "category": "technical"}]      # the model repeated itself

        # posting 2
        [{"name": "SQL", "category": "technical"},
        {"name": "stakeholder management", "category": "business"}]
        
        counts 
        Counter({("sql", "technical"): 48,
        ("sql queries", "technical"): 21,
        ("stakeholder management", "business"): 19,
        ("stakeholder management", "communication"): 6,   # same phrase, other category: a separate entry
        ...})                                              # often 2,000+ distinct pairs
        """
        
        if i % 50 == 0:
            print(f"  {i} read, ${claude.cost_usd:.3f} so far", flush=True)
    
    if not counts:
        print("No skills found, exiting", file=sys.stderr)
        return 1
    
    print(f"{len(counts):,} distinct phrases. Grouping them into a list...", flush=True)
    skills = build_list(claude, counts)
    skills.sort(key=lambda s: (s["category"], s["skill"]))

    header = (
        f"# Draft skill list from {len(rows) - failed} postings. Review it, then save as skills.yaml.\n"
        "# Rename, merge, split or delete freely; categories: technical, communication, business, leadership.\n\n"
    )
    args.out.write_text(header + yaml.safe_dump(skills, sort_keys=False, allow_unicode=True, width=100),
                        encoding="utf-8")
    print(f"Wrote {len(skills)} skills to {args.out.name}. Cost: ${claude.cost_usd:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())