"""Job market dashboard. Run from the project folder:
    uv run streamlit run projects/linkedin_jobs/app.py
"""

import sys
from pathlib import Path

# `streamlit run` puts this file's folder on sys.path, not the project folder,
# so add the project folder ourselves to make `core` and `projects` importable.
# The imports below have to come after this fix.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import altair as alt
import pandas as pd
import streamlit as st
import yaml

from core import db
from projects.linkedin_jobs import app_skills, queries

GAP = "#D85A30"      # themes you don't cover yet: the one color that should catch the eye
COVERED = "#87867F"  # themes you already cover: recessive grey
THEMES = [t["theme"] for t in yaml.safe_load((ROOT / "projects/linkedin_jobs/themes.yaml").read_text(encoding="utf-8"))]

st.set_page_config(page_title="Job market tracker", layout="wide")


def bars(rows: list[dict], label: str):
    """A horizontal bar chart of roles per category, longest bar first."""
    return (
        alt.Chart(pd.DataFrame(rows))
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("roles:Q", title="Roles"),
            y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=[label, "roles"],
        )
    )


@st.cache_data(ttl="1h", show_spinner=False)
def load_options() -> dict:
    with db.connect() as conn:
        return queries.filter_options(conn)


@st.cache_data(ttl="1h", show_spinner="Querying Supabase...")
def load_dashboard(terms: list[str], start, end) -> dict:
    with db.connect() as conn:
        return queries.dashboard(conn, terms, start, end)


# ---------- Sidebar: filters ----------
options = load_options()
if not options["months"]:
    st.info("No postings yet. Run the pipeline (Module 6) first, then refresh this page.")
    st.stop()

st.sidebar.header("Filters")
terms = st.sidebar.multiselect("Searches", options["terms"], default=options["terms"])
months = options["months"]
if len(months) > 1:
    start, end = st.sidebar.select_slider(
        "Months", options=months, value=(months[0], months[-1]),
        format_func=lambda m: m.strftime("%b %Y"),
    )
else:
    start = end = months[0]
    st.sidebar.caption(f"Month: {start:%b %Y}")

mine = st.sidebar.multiselect(
    "Themes I already cover", THEMES,
    help="Tick what your current work already includes. Everything else counts as a gap.",
)

if not terms:
    st.warning("Pick at least one search in the sidebar.")
    st.stop()

data = load_dashboard(terms, start, end)
all_themes = [t["theme"] for t in data["themes"]]  # most-mentioned first

# ---------- Headline numbers ----------
st.title("Job market tracker")
s = data["summary"]
st.caption(f"{', '.join(terms)} · {start:%b %Y} to {end:%b %Y} · reposts and multi-city postings counted once")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Roles", f"{s['roles']:,}")
c2.metric("Companies", f"{s['companies']:,}")
c3.metric("Show a salary", f"{s['pct_with_salary'] or 0:.0f}%")
c4.metric("Median yearly salary", f"${s['median_salary']:,.0f}" if s["median_salary"] else "n/a")

# ---------- Skill gap ----------
st.subheader("What employers ask for, and where your gaps are")
themes = pd.DataFrame(data["themes"])
if themes.empty:
    st.info("No themes tagged for these filters.")
else:
    themes["you"] = themes["theme"].map(lambda t: "Covered" if t in mine else "Gap")
    chart = (
        alt.Chart(themes)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("pct:Q", title="% of roles mentioning the theme"),
            y=alt.Y("theme:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
            color=alt.Color(
                "you:N", title=None,
                scale=alt.Scale(domain=["Gap", "Covered"], range=[GAP, COVERED]),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=["theme", "roles", alt.Tooltip("pct", title="% of roles")],
        )
    )
    st.altair_chart(chart, width="stretch")

    gaps = themes[themes["you"] == "Gap"].head(3)
    if mine and not gaps.empty:
        top = ", ".join(f"**{r.theme}** ({r.pct:.0f}%)" for r in gaps.itertuples())
        st.markdown(f"Your biggest gaps by demand: {top}.")

# ---------- Skills by category (Module 12) ----------
app_skills.show(terms, start, end)

# ---------- Who is hiring ----------
left, right = st.columns(2)
with left:
    st.subheader("Industries hiring")
    st.altair_chart(bars(data["industries"], "industry"), width="stretch")
with right:
    st.subheader("Seniority")
    st.altair_chart(bars(data["seniority"], "seniority"), width="stretch")

# ---------- Themes by industry ----------
st.subheader("Themes by industry")
st.caption("Share of each industry's roles that mention the theme. Top 8 industries by roles.")
grid = pd.DataFrame(data["theme_by_industry"])
if not grid.empty:
    heat = (
        alt.Chart(grid)
        .mark_rect(stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("industry:N", title=None, axis=alt.Axis(labelAngle=-35, labelLimit=200, labelOverlap=False)),
            y=alt.Y("theme:N", title=None, sort=all_themes, axis=alt.Axis(labelLimit=260)),
            color=alt.Color("pct:Q", title="% of roles", scale=alt.Scale(scheme="blues")),
            tooltip=["industry", "theme", alt.Tooltip("pct", title="% of roles")],
        )
    )
    st.altair_chart(heat, width="stretch")

# ---------- Browse postings ----------
st.subheader("Browse roles")
pick = st.selectbox("Only roles mentioning", ["Any theme", *all_themes])
rows = data["postings"]
if pick != "Any theme":
    rows = [r for r in rows if pick in r["themes"]]
st.caption(f"{len(rows):,} roles")
st.dataframe(
    pd.DataFrame(rows),
    hide_index=True,
    column_config={
        "title": "Title",
        "company_name": "Company",
        "primary_industry": "Industry",
        "seniority_level": "Seniority",
        "location": "Location",
        "location_count": st.column_config.NumberColumn("Cities", help="Cities this role was posted in"),
        "workplace_type": "Workplace",
        "salary_min": st.column_config.NumberColumn("Salary from", format="$%,.0f"),
        "salary_max": st.column_config.NumberColumn("Salary to", format="$%,.0f"),
        "salary_period": "Per",
        "first_seen": st.column_config.DateColumn("First seen"),
        "link": st.column_config.LinkColumn("Link", display_text="Open"),
        "themes": st.column_config.ListColumn("Themes"),
    },
)
