"""The dashboard's "Skills by category" section (Module 12). Called from app.py."""

import altair as alt
import pandas as pd
import streamlit as st

from core import db
from core.skills import CATEGORIES
from projects.linkedin_jobs import skill_queries

GAP = "#D85A30"
COVERED = "#87867F"


@st.cache_data(ttl="1h", show_spinner=False)
def load(terms: list[str], start, end) -> dict | None:
    with db.connect() as conn:
        if not skill_queries.has_skills(conn):
            return None
        return skill_queries.skills_dashboard(conn, terms, start, end)


def show(terms: list[str], start, end) -> None:
    data = load(terms, start, end)
    if data is None:
        return  # Module 12 not set up yet: show nothing

    skills = pd.DataFrame(data["skills"])
    mine = st.sidebar.multiselect(
        "Skills I already have", sorted(skills["skill"]),
        help="Tick what you can already show on your resume. Everything else counts as a gap.",
    )
    skills["you"] = skills["skill"].map(lambda s: "Covered" if s in mine else "Gap")

    st.subheader("Skills by category")
    st.caption(f"Share of {data['tagged_roles']:,} tagged roles asking for each skill. "
               "Hover a bar to see how often it's required rather than preferred.")
    tabs = st.tabs([c.capitalize() for c in CATEGORIES])
    for tab, category in zip(tabs, CATEGORIES):
        rows = skills[(skills["category"] == category) & (skills["roles"] > 0)]
        with tab:
            if rows.empty:
                st.caption("No roles ask for these skills under the current filters.")
                continue
            chart = (
                alt.Chart(rows)
                .mark_bar(cornerRadiusEnd=4)
                .encode(
                    x=alt.X("pct:Q", title="% of roles asking for the skill"),
                    y=alt.Y("skill:N", sort="-x", title=None, axis=alt.Axis(labelLimit=280)),
                    color=alt.Color("you:N", title=None,
                                    scale=alt.Scale(domain=["Gap", "Covered"], range=[GAP, COVERED]),
                                    legend=alt.Legend(orient="top")),
                    tooltip=["skill", "roles", alt.Tooltip("pct", title="% of roles"),
                             alt.Tooltip("pct_required", title="% where required")],
                )
            )
            st.altair_chart(chart, width="stretch")

    st.subheader("Emerging skills")
    st.caption("Skills employers ask for that aren't in skills.yaml yet. Add the real ones to the list, "
               "then re-tag (Module 12).")
    if data["emerging"]:
        st.dataframe(pd.DataFrame(data["emerging"]), hide_index=True,
                     column_config={"phrase": "Skill", "roles": "Roles"})
    else:
        st.caption("Nothing new yet.")
