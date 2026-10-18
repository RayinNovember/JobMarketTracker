"""Turn raw scraper items into clean rows for jobs.postings."""

import re
from datetime import date

from core.text import ThemeTagger, content_hash

# Personal data about recruiters/posters: never stored.
PERSONAL_KEYS = {"jobPosterName", "jobPosterTitle", "jobPosterPhoto", "jobPosterProfileUrl"}

_MONEY = re.compile(r"\$?\s*([\d,]+(?:\.\d+)?)\s*([kK])?")
_PERIODS = {"yr": "yr", "year": "yr", "hr": "hr", "hour": "hr", "mo": "mo", "month": "mo", "wk": "wk", "week": "wk"}


def strip_personal(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in PERSONAL_KEYS}


def _int(v) -> int | None:
    if v is None or v == "":
        return None
    m = re.search(r"\d[\d,]*", str(v))
    return int(m.group(0).replace(",", "")) if m else None


def _date(v) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def parse_salary(info) -> tuple[float | None, float | None, str | None]:
    """salaryInfo is a list like ["$120,000.00/yr", "$150,000.00/yr"] (format may vary)."""
    if not info:
        return None, None, None
    parts = info if isinstance(info, list) else [info]
    text = " ".join(str(p) for p in parts)
    amounts = []
    for num, k in _MONEY.findall(text):
        try:
            val = float(num.replace(",", ""))
        except ValueError:
            continue
        amounts.append(val * 1000 if k else val)
    amounts = [a for a in amounts if a > 0]
    period = None
    m = re.search(r"/\s*(yr|year|hr|hour|mo|month|wk|week)", text, re.I)
    if m:
        period = _PERIODS[m.group(1).lower()]
    elif amounts:
        period = "hr" if max(amounts) < 500 else "yr"
    if not amounts:
        return None, None, period
    return min(amounts), max(amounts), period


def workplace(item: dict) -> str | None:
    wt = item.get("workplaceTypes")
    if isinstance(wt, list) and wt:
        return ", ".join(str(w) for w in wt)
    if isinstance(wt, str) and wt:
        return wt
    if item.get("workRemoteAllowed") is True:
        return "Remote"
    return None


def to_row(item: dict, search_terms: list[str], tagger: ThemeTagger) -> dict:
    industries = item.get("industries") or None
    if isinstance(industries, list):
        industries = ", ".join(industries)
    desc = item.get("descriptionText") or ""
    sal_min, sal_max, sal_period = parse_salary(item.get("salaryInfo") or item.get("salary"))
    return {
        "job_id": str(item["id"]),
        "title": item.get("title"),
        "company_name": item.get("companyName"),
        "company_url": item.get("companyLinkedinUrl"),
        "company_employees": _int(item.get("companyEmployeesCount")),
        "location": item.get("location"),
        "industries": industries,
        "primary_industry": industries.split(",")[0].strip() if industries else None,
        "seniority_level": item.get("seniorityLevel") or None,
        "employment_type": item.get("employmentType") or None,
        "job_function": item.get("jobFunction") or None,
        "workplace_type": workplace(item),
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salary_period": sal_period,
        "posted_at": _date(item.get("postedAt")),
        "applicants_count": _int(item.get("applicantsCount")),
        "link": item.get("link"),
        "description_text": desc or None,
        "content_hash": content_hash(item.get("companyName"), item.get("title"), item.get("location"), desc),
        "themes": tagger.tag(f"{item.get('title') or ''}\n{desc}"),
        "search_terms": sorted(set(search_terms)),
    }


def merge_items(batches: dict[str, list[dict]]) -> dict[str, tuple[dict, list[str]]]:
    """Combine results of several searches; a job found by two searches is kept once."""
    merged: dict[str, tuple[dict, list[str]]] = {}
    for term, items in batches.items():
        for it in items:
            if not it.get("id"):
                continue
            jid = str(it["id"])
            if jid in merged:
                merged[jid][1].append(term)
            else:
                merged[jid] = (strip_personal(it), [term])
    return merged


