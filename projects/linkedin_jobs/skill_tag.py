"""Module 12, pass 2: tag stored postings with skills from skills.yaml.

Usage:
    uv run python -m projects.linkedin_jobs.skill_tag --limit 10       # try it on 10 postings
    uv run python -m projects.linkedin_jobs.skill_tag                  # every posting not tagged yet
    uv run python -m projects.linkedin_jobs.skill_tag --retag "agent"  # re-tag postings mentioning a word
    uv run python -m projects.linkedin_jobs.skill_tag --retag-all      # re-tag everything
"""
import argparse
import sys
from pathlib import Path

import psycopg

from core import db
from core.skills import SkillTagger

HERE = Path(__file__).parent
MAX_FAILURES_IN_A_ROW = 5

def sync_skills(conn:psycopg.Connection, skills: list[dict]) -> None:
    """Sync the skills table with the provided list of skills."""
    names = [s['skill'] for s in skills]
    with conn.cursor() as cur:
        cur.executemany(
            """
            insert into jobs.skills (skill, category, definition) values (%(skill)s, %(category)s, %(definition)s)
            on conflict (skill) do update set category = excluded.category, definition = excluded.definition
            """,
            skills,
        )
    conn.execute("delete from jobs.posting_skills where skill <> all(%s)", (names,))
    conn.execute("delete from jobs.skills where skill <> all(%s)", (names,))
    
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Tag postings with skills')
    ap.add_argument('--limit', type=int, help='number of postings to process')
    ap.add_argument('--retag', metavar='WORD', help='re-tag postings mentioning a word')
    ap.add_argument('--retag-all', action='store_true', help='re-tag every posting')
    args = ap.parse_args(argv)
    
    path = HERE/'skills.yaml'
    if not path.exists():
        print("No skills.yaml yet. Run skill_discover, review skills_draft.yaml, then save it as skills.yaml.",
              file=sys.stderr)
        return 1
    tagger = SkillTagger.from_yaml(path)
    
    with db.connect() as conn:
        sync_skills(conn,tagger.skills)
        if args.retag_all:
            conn.execute("update jobs.postings set other_skills = null")
        elif args.retag:
            conn.execute("update jobs.postings set other_skills = null where description_text ilike %s",
                        (f"%{args.retag}%",))
        conn.commit() 
        
        rows = conn.execute(
            """
             select job_id, title, description_text from jobs.postings
             where other_skills is null and description_text is not null
             order by first_seen_at desc
             limit %s
            """,
            (args.limit,),
        ).fetchall()
        print(f"{len(rows)} postings to tag against {len(tagger.names)} skills with {tagger.claude.model}",flush=True)
        
        done, failed, in_a_row = 0, 0, 0
        for job_id, title, description in rows:
            try:
                found, other = tagger.tag(f"{title}\n\n{description}")
            except Exception as e:
                failed += 1
                in_a_row += 1
                print(f"Failed to tag {job_id}: {e}", file=sys.stderr, flush=True)
                if in_a_row >= MAX_FAILURES_IN_A_ROW:
                    print("Stopping after too many consecutive failures.", file=sys.stderr, flush=True)
                    break # goes to the first line after the for loop, stopping tagging altogether  
                continue # goes to the top of the for loop, with the next posting, skips this posting, keeps going
            in_a_row = 0
            conn.execute("delete from jobs.posting_skills where job_id = %s", (job_id,))
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into jobs.posting_skills (job_id, skill, level) values (%s, %s, %s)",
                    [(job_id, skill, level) for skill, level in found.items()],
                )
            conn.execute("update jobs.postings set other_skills = %s where job_id = %s", (other, job_id))
            done += 1
            if done % 50 == 0:
                conn.commit()
                print(f"  {done} tagged, ${tagger.claude.cost_usd:.3f} so far", flush=True)
        conn.commit()
        
    c = tagger.claude
    print(f"Tagged {done}, failed {failed}. Tokens: {c.input_tokens:,} in, {c.output_tokens:,} out. "
          f"Cost: ${c.cost_usd:.3f}")
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main())