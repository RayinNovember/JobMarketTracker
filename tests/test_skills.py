"""Tests for skills by category (Module 12). No API calls: a fake client stands in.

Unit tests always run. Script tests run when TEST_DB_URL points at a throwaway
Postgres (never your Supabase project: they drop the jobs and core schemas):
    TEST_DB_URL=postgresql://... uv run pytest tests/test_skills.py
"""
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.skills import Claude, SkillTagger, build_list, extract_open

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "tests/fixtures/skills.yaml"


class FakeMessages:
    """Returns the given replies in turn, and records every request."""

    def __init__(self, *replies: dict):
        self.replies = list(replies)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(reply))],
            usage=SimpleNamespace(input_tokens=2000, output_tokens=200),
        )


def fake_claude(*replies: dict) -> Claude:
    return Claude(client=SimpleNamespace(messages=FakeMessages(*replies)))


# ---------- Unit tests: core/skills.py ----------

def test_tag_cleans_the_reply():
    claude = fake_claude({
        "skills": [
            {"skill": "sql", "level": "preferred"},
            {"skill": "SQL", "level": "required"},          # listed twice: required wins
            {"skill": "Mentoring", "level": "preferred"},
            {"skill": "Juggling", "level": "required"},     # not on the list: dropped
        ],
        "other_skills": ["  Marketplace   Analytics ", "marketplace analytics", "python", "a", "b", "c", "d"],
    })
    found, other = SkillTagger.from_yaml(SKILLS, claude=claude).tag("Senior Data Scientist ...")
    assert found == {"SQL": "required", "Mentoring": "preferred"}
    assert other == ["marketplace analytics", "a", "b", "c", "d"]   # cleaned, deduped, known skills dropped, max 5


def test_tag_request_uses_the_list():
    claude = fake_claude({"skills": [], "other_skills": []})
    tagger = SkillTagger.from_yaml(SKILLS, claude=claude)
    tagger.tag("x" * 20000)
    req = claude.client.messages.requests[0]
    item = req["output_config"]["format"]["schema"]["properties"]["skills"]["items"]
    assert item["properties"]["skill"]["enum"] == tagger.names
    assert item["properties"]["level"]["enum"] == ["required", "preferred"]
    assert "Business:\n- Metric definition and KPI design" in req["system"]
    assert req["thinking"] == {"type": "disabled"}
    assert len(req["messages"][0]["content"]) == 8000
    json.dumps(req["output_config"])   # the schema must be JSON-serializable (names is a list, not a set)


def test_empty_text_makes_no_call():
    claude = fake_claude({"skills": [], "other_skills": []})
    assert SkillTagger.from_yaml(SKILLS, claude=claude).tag(None) == ({}, [])
    assert claude.client.messages.requests == []


def test_discovery_helpers():
    claude = fake_claude(
        {"skills": [{"name": "Stakeholder management", "category": "communication"}]},
        {"skills": [{"skill": "Stakeholder management", "category": "communication", "definition": "..."}]},
    )
    assert extract_open(claude, "posting") == [{"name": "Stakeholder management", "category": "communication"}]
    counts = Counter({("stakeholder management", "communication"): 7, ("working with partners", "communication"): 3})
    assert build_list(claude, counts)[0]["skill"] == "Stakeholder management"
    sent = claude.client.messages.requests[1]["messages"][0]["content"]
    assert "7 | communication | stakeholder management" in sent
    assert claude.cost_usd == pytest.approx(4000 / 1e6 * 0.10 + 400 / 1e6 * 0.50)


# ---------- Script tests: skill_tag.py and skill_discover.py against a throwaway database ----------

DB = os.environ.get("TEST_DB_URL")


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_skill_tag_script(monkeypatch, tmp_path):
    import psycopg
    import yaml

    from core import db
    from core.text import ThemeTagger
    from projects.linkedin_jobs import load, skill_tag
    from projects.linkedin_jobs.transform import merge_items, to_row

    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    items = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text(encoding="utf-8"))
    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.commit()
        db.migrate(conn)
        run_id = conn.execute("insert into core.run_log (project) values ('t') returning run_id").fetchone()[0]
        merged = merge_items({"data scientist": items})
        tagger = ThemeTagger.from_yaml(ROOT / "projects/linkedin_jobs/themes.yaml")
        load.upsert_postings(conn, run_id, [to_row(i, t, tagger) for i, t in merged.values()], date(2026, 10, 1))
        conn.commit()

    # The script reads skills.yaml next to itself; point it at a copy of the fixture instead.
    (tmp_path / "skills.yaml").write_text(SKILLS.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(skill_tag, "HERE", tmp_path)
    reply = {"skills": [{"skill": "SQL", "level": "required"}, {"skill": "Mentoring", "level": "preferred"}],
             "other_skills": ["marketplace analytics"]}
    monkeypatch.setattr(SkillTagger, "from_yaml", classmethod(
        lambda cls, path: cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")), claude=fake_claude(reply))))

    assert skill_tag.main([]) == 0
    with psycopg.connect(DB) as conn:
        assert conn.execute("select count(*) from jobs.posting_skills").fetchone()[0] == 6   # 3 postings x 2
        assert conn.execute("select count(*) from jobs.skills").fetchone()[0] == 6
        # jobs 2 and 3 are one role, so the view counts 2 roles
        assert conn.execute("select count(distinct job_id) from jobs.role_skills").fetchone()[0] == 2
        assert conn.execute("select distinct category from jobs.role_skills where skill = 'SQL'").fetchall() \
            == [("technical",)]
        # every posting is marked as done, with the cleaned other skill
        assert conn.execute("select distinct other_skills from jobs.postings").fetchall() \
            == [(["marketplace analytics"],)]

    # Nothing left to tag; a second run only syncs the list
    assert skill_tag.main([]) == 0

    # Recategorize and delete a skill in skills.yaml: no re-tagging needed
    skills = yaml.safe_load(SKILLS.read_text(encoding="utf-8"))
    skills = [dict(s, category="leadership") if s["skill"] == "Presenting to leadership" else s
              for s in skills if s["skill"] != "Mentoring"]
    (tmp_path / "skills.yaml").write_text(yaml.safe_dump(skills), encoding="utf-8")
    assert skill_tag.main(["--retag", "nothing mentions this"]) == 0
    with psycopg.connect(DB) as conn:
        assert conn.execute("select category from jobs.skills where skill = 'Presenting to leadership'").fetchone()[0] \
            == "leadership"
        assert conn.execute("select count(*) from jobs.posting_skills where skill = 'Mentoring'").fetchone()[0] == 0

    # --retag-all marks everything untagged and tags it again
    assert skill_tag.main(["--retag-all", "--limit", "1"]) == 0
    with psycopg.connect(DB) as conn:
        assert conn.execute("select count(*) from jobs.postings where other_skills is null").fetchone()[0] == 2


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_skill_discover_writes_a_draft(monkeypatch, tmp_path):
    import yaml

    from projects.linkedin_jobs import skill_discover

    # Uses the postings that test_skill_tag_script loaded (2 distinct roles).
    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    replies = (
        {"skills": [{"name": "SQL", "category": "technical"}]},
        {"skills": [{"name": "SQL", "category": "technical"}]},
        {"skills": [{"skill": "SQL", "category": "technical", "definition": "Querying data."}]},
    )
    monkeypatch.setattr(skill_discover, "Claude", lambda: fake_claude(*replies))
    out = tmp_path / "draft.yaml"
    assert skill_discover.main(["--sample", "2", "--out", str(out)]) == 0
    assert yaml.safe_load(out.read_text(encoding="utf-8")) == [
        {"skill": "SQL", "category": "technical", "definition": "Querying data."}]
