# Module 12 notes: issues found and how they were handled

Running log of problems found while running Module 12 (skills by category), and the fix for each.
Open items to revisit are marked **To revisit**.

## 1. `extract_open` replies cut off (Pass 1), 2026-11-09

**Issue.** A 20-posting test run skipped 5 of 20 postings with `JSONDecodeError` ("Unterminated string",
"Expecting value"). Every reply broke at about 2,300 characters: `max_tokens=800` in `extract_open` was too
small for long postings that list 40+ skills, so the JSON was cut off before it closed.

**Solution.** Raised `max_tokens` from 800 to 2000 in `extract_open` (`core/skills.py`, with a comment).
Re-ran the 20-posting test: 0 skipped. The full 500-posting run then skipped none, for $0.301 in total.
You only pay for tokens actually generated, so the higher limit costs nothing on short postings.
The guide still says 800, so this code now differs from the guide.

**Watch.** `SkillTagger.tag` (Pass 2) also used `max_tokens=800`, and did hit the same error (see issue 4).

## 2. Pass 1 returned 78 skills instead of 40 to 60, with near-duplicates, 2026-11-09

**Issue.** The full run read 500 postings (9,146 distinct phrases) and `build_list` returned **78 skills**,
although the prompt asks for 40 to 60. Many overlap, so the tagger would split one skill across two names and
undercount both:

| Merged | Into |
| --- | --- |
| Stakeholder communication, Stakeholder management | Stakeholder management |
| Presentation skills, Executive communication, Explaining data insights | Presenting insights (Data storytelling kept separate) |
| Verbal communication, Written communication, Interpersonal skills | Communication skills (only when nothing more specific applies) |
| Hypothesis testing, A/B testing, Experiment design | A/B testing and experimentation |
| Statistical analysis, Statistical modeling, Quantitative analysis | Statistical analysis and modeling (Regression analysis kept separate) |
| Machine learning, Predictive modeling | Machine learning and predictive modeling |
| Clustering, Anomaly detection, Data mining | Unsupervised learning |
| Forecasting, Time series analysis | Forecasting and time series |
| Data analysis, Large dataset analysis, Exploratory data analysis | Data analysis |
| Data cleaning, Data validation, Data quality management | Data cleaning and quality |
| Business intelligence tools, Dashboard development | Dashboard development (Tableau and Power BI kept as tools) |
| Reporting automation, Process automation | Automation |
| Actionable insight generation, Data-driven decision support | Decision support and recommendations |
| Multi-priority management, Organizational skills | Prioritization and organization |
| Algorithm development | dropped (covered by Machine learning) |

Also: *Root cause analysis* moved technical → business, *Attention to detail* moved business → leadership,
*Problem solving* renamed *Solving ambiguous problems*, *Cloud platforms (AWS)* widened to *Cloud platforms*
(AWS, Azure, GCP), and tool names shortened (*SQL querying* → *SQL*, *Python programming* → *Python*).

**Solution.** Cleaned the draft by hand into `projects/linkedin_jobs/skills.yaml`: **56 skills** (32 technical,
7 communication, 10 business, 7 leadership). Where two skills could overlap, the definitions say which one to
use (for example, *Dashboard development* also tags Tableau or Power BI when they're named). The original
draft is kept as `projects/linkedin_jobs/skills_draft.yaml` for comparison.

**To revisit: improving Pass 1.** Ideas, not yet tried:

- Make the size a hard limit: ask for "at most 60" and add a schema constraint (`maxItems`), or check the
  count in `skill_discover.py` and ask again when it's over.
- Tell `build_list` to merge more aggressively: one skill per tool or method, no near-synonyms, no generic
  soft skills split by channel (verbal, written).
- Raise `effort` for `build_list` from `medium` to `high`. It's one request, so the cost is negligible.
- Normalize phrases more before counting (for example, strip "skills", "programming", "proficiency"), so
  fewer variants reach `build_list`.
- Send fewer, more frequent phrases (top 200 instead of 400), or drop phrases seen in only 1 or 2 postings.
- Add a second, cheap review request that lists likely duplicates in the draft for you to decide on.

## 3. Pass 2 `other_skills` repeats skills the list already covers, 2026-11-09

**Issue.** The first `skill_tag --limit 10` run (0 failures, $0.007, 7–27 skills per posting) looked right,
but some `other_skills` phrases are already covered by a list skill's *definition*, not its name:
"anomaly detection" and "data mining" (in *Unsupervised learning*), "exploratory data analysis" (in
*Data analysis*). `tag()` only drops other phrases that exactly match a skill *name*.

**Solution (for now).** Accepted as minor: it only adds noise to the emerging-skills list, and doesn't
affect the counts in `jobs.posting_skills`. When reviewing emerging skills, ignore phrases a definition
already covers.

**To revisit.** Tell the tagger in its prompt to put a phrase in `other_skills` only if no listed skill's
definition covers it, or give near-synonyms their own skill name. Then re-tag with `--retag WORD`.

## 4. Full Pass 2 run: 11 replies cut off, then the database connection dropped, 2026-11-09

**Issue.** The full `skill_tag` run (1,992 postings) had two problems:

- 11 postings failed with `JSONDecodeError` ("Unterminated string" at about char 2,000). `SkillTagger.tag` used
  `max_tokens=800`, too small for postings that match 30+ skills. This is the same problem as issue 1.
- Near the end (after about 1,950 postings, roughly 45 minutes), Supabase closed the connection
  (`psycopg.OperationalError: server closed the connection unexpectedly`), and the script crashed.

**Solution.**

- Raised `max_tokens` from 800 to 2000 in `SkillTagger.tag` (`core/skills.py`, with a comment). Unit tests still pass.
- No code change for the dropped connection. Committing every 50 postings saved all the finished work; only
  the uncommitted batch was lost. The failed and lost postings still had `other_skills` NULL, so running the
  script again picked up just those: 42 postings, 0 failures, $0.033.
- End state: all 2,002 postings tagged (none left with NULL), about $1.45 in total for Pass 2.

**To revisit (optional).** If dropped connections happen again on long runs, reconnect and continue inside
the script instead of crashing. For now, running it again is enough.
