import json
from core.text import ThemeTagger
from projects.linkedin_jobs.transform import merge_items, to_row, parse_salary

items = json.load(open("samples/raw_sample.json", encoding="utf-8"))
tagger = ThemeTagger.from_yaml("projects/linkedin_jobs/themes.yaml")
merged = merge_items({"data scientist": items})
rows = [to_row(item, terms, tagger) for item, terms in merged.values()]

for r in rows:
    print(r["title"], "|", r["primary_industry"], "|", r["salary_min"], r["salary_period"], "|", r["themes"])

parse_salary(["$45.00/hr", "$55.00/hr"])
