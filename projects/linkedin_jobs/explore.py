import json
from pathlib import Path

import yaml

from projects.linkedin_jobs import scrape

HERE = Path(__file__).parent
cfg = yaml.safe_load((HERE / "config.yaml").read_text())

term = cfg["searches"][0]
print(f"Running the scraper for '{term}', 5 jobs...")
items, cost = scrape.run_search(scrape.client(), cfg, term, limit=5)

out = Path("samples") / "raw_sample.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Got {len(items)} jobs for ${cost:.4f}. Saved to {out}")
print("Fields in the first job:", ", ".join(items[0].keys()) if items else "(none)")