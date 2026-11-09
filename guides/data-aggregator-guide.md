# Data Aggregator: Build-Along Guide

*A self-study guide to building a monthly job-postings pipeline: Apify → Python → Supabase → GitHub Actions. Written October 2026, tested against uv 0.11, Python 3.12, apify-client 3.3 and psycopg 3.3.*

## How to use this guide

You'll build the monthly LinkedIn jobs pipeline yourself, one module at a time. Each module ends with working code, a git commit and a few questions to check your understanding. Type the code rather than pasting it: the typos you make and fix are part of the learning.

Conventions:

- **Run in the terminal** blocks are commands for VS Code's terminal (open it with Ctrl+\`). Where Windows and Mac differ, both are given.
- **Why** notes explain the reasoning behind a step, not just the keystrokes.
- **Checkpoint** marks a point where something should visibly work. If it doesn't, stop and fix it before moving on. Module 1 ends with a troubleshooting table, and later modules list their own common failures.
- Every code block in this guide was run and tested before it was written down. If yours behaves differently, compare it character by character first.

| Module | You build | You learn |
| --- | --- | --- |
| 1. Project setup | An empty uv project that can reach Apify and Supabase | uv, virtual environments, dependencies, secrets, `python -m` |
| 2. Calling Apify | A script that runs the scraper for one search | APIs, tokens, JSON, reading actor output |
| 3. Shaping the data | Clean rows from raw jobs | Parsing, normalizing, hashing, keyword tagging |
| 4. The database | Tables and views in Supabase | SQL schemas, keys, idempotent migrations |
| 5. Loading without duplicates | The monthly upsert | `ON CONFLICT`, staging tables, transactions |
| 6. The pipeline script | One command that runs everything | Run logging, error handling, command-line flags |
| 7. Tests | A safety net for every change | pytest, fixtures, fakes, a throwaway test database |
| 8. Automation | Monthly runs on GitHub | GitHub Actions, cron, secrets, keep-alive |
| 9. Analysis | The skill-gap answer you started this for | SQL views, connecting Power BI |
| 10. A second scraper | Your next back-burner project | Reusing the shared core |

The finished project looks like this. You'll create every file yourself, in this order:

```text
data-aggregator/
├── core/                         shared code every scraper reuses
│   ├── __init__.py
│   ├── settings.py               Module 1
│   ├── check_connections.py      Module 1
│   ├── text.py                   Module 3
│   ├── db.py                     Module 4
│   └── runlog.py                 Module 6
├── projects/
│   ├── __init__.py
│   └── linkedin_jobs/            code specific to this scraper
│       ├── __init__.py
│       ├── config.yaml           Module 2
│       ├── scrape.py             Module 2
│       ├── explore.py            Module 2
│       ├── themes.yaml           Module 3
│       ├── transform.py          Module 3
│       ├── load.py               Module 5
│       └── run.py                Module 6
├── sql/
│   ├── 001_core.sql              Module 4
│   ├── 010_linkedin_jobs.sql     Module 4
│   └── 020_analysis.sql          Module 9
├── tests/
│   ├── __init__.py
│   ├── fixtures/sample_items.json   Module 7
│   └── test_linkedin_jobs.py        Module 7
├── .github/workflows/            Module 8 (4 files)
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## Module 1: An empty uv project in VS Code

By the end of this module you'll have a project folder with the right Python packages, secrets kept out of git, and a script that proves it can reach both Apify and Supabase. Allow about 45 minutes.

### 1.1 Install uv

uv is one tool that installs Python, creates the project's private environment and manages its packages. It replaces pip, venv and pyenv.

**Run in the terminal**, Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Mac:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen the terminal, then:

```bash
uv --version
```

**Checkpoint:** it prints a version number such as `uv 0.11.x`.

### 1.2 Create the project

Before this step, create the GitHub repository **empty**: no README, no .gitignore, no license. uv creates those files locally, and a repo that already has them makes the first push fail with a conflict.

**Run in the terminal**, from the folder where you keep code projects:

```bash
uv init data-aggregator --python 3.12
cd data-aggregator
```

uv just created these:

| File | What it is |
| --- | --- |
| `pyproject.toml` | The project's ID card: name, Python version, dependencies |
| `.python-version` | Pins Python 3.12 for this folder |
| `main.py` | A placeholder script; you'll delete it in 1.5 |
| `README.md` | An empty readme |
| `.gitignore` | Files git should never track, like the environment folder |
| `.git/` (hidden) | A local git repository; uv ran `git init` for you |

Open `pyproject.toml`. It reads:

```toml
[project]
name = "data-aggregator"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []
```

Line by line:

1. `[project]` starts the section describing the project. TOML files are sections in brackets followed by `key = value` lines.
2. `name` is the project's name, taken from the folder name.
3. `version` is your own version number. It matters only if you publish the code as a package, which you won't.
4. `description` is a one-liner. Change it to `"Monthly web scrapers that land data in Supabase"`.
5. `readme` points to the readme file.
6. `requires-python` sets the minimum Python version the code supports.
7. `dependencies = []` is the list of packages the project needs. It's empty now; `uv add` fills it in 1.4.

Now run the placeholder script:

```bash
uv run main.py
```

**Why `uv run`:** it runs the command inside the project's own environment. The first time, uv creates a hidden `.venv` folder holding Python 3.12 and the project's packages (downloading Python if you don't have it). You never need to "activate" anything.

**Checkpoint:** it prints `Hello from data-aggregator!` and a `.venv` folder appears.

### 1.3 Open it in VS Code

**Run in the terminal:**

```bash
code .
```

The `.` means "this folder". If `code` isn't recognized on a Mac, open VS Code, press Cmd+Shift+P and run **Shell Command: Install 'code' command in PATH**. On Windows, reinstall VS Code with **Add to PATH** ticked, or open the folder from VS Code's File menu.

In VS Code:

1. Install the **Python** extension (by Microsoft) from the Extensions panel, if you don't have it.
2. Press Ctrl+Shift+P (Cmd+Shift+P on Mac), run **Python: Select Interpreter**, and pick the one inside `.venv`. On Windows it's `.venv\Scripts\python.exe`; on Mac, `.venv/bin/python`.
3. Open the terminal inside VS Code with Ctrl+\`. From here on, run every command there; it starts in the project folder.

**Why select the interpreter:** VS Code uses it for autocomplete and for the squiggly underlines that flag errors. Pointed at the wrong Python, it underlines every import as missing even when the code runs fine.

### 1.4 Add the packages

**Run in the terminal:**

```bash
uv add apify-client python-dotenv pyyaml "psycopg[binary]"
uv add --dev pytest
```

| Package | What we use it for |
| --- | --- |
| `apify-client` | Talking to Apify's API: start the scraper, fetch its results |
| `python-dotenv` | Reading secrets from a `.env` file into the program |
| `pyyaml` | Reading the settings files (search terms, themes) |
| `psycopg[binary]` | Talking to the Postgres database inside Supabase |
| `pytest` (dev only) | Running tests; not needed for the pipeline itself |

Details worth knowing:

- The quotes around `"psycopg[binary]"` stop the terminal from treating the square brackets as special characters.
- `[binary]` is an **extra**, an optional flavor of the package. This one comes prebuilt, so you don't need Postgres installed on your computer.
- `--dev` marks pytest as a development tool. It's listed separately, under `[dependency-groups]`, so the production run can skip it.

Open `pyproject.toml` again. `dependencies` now lists the four packages with minimum versions, such as `"apify-client>=3.3.0"`. There's also a new file, **`uv.lock`**. It records the exact version of every package, including the packages those packages depend on.

**Why `uv.lock` matters:** you'll commit it. When GitHub runs the pipeline next month, `uv sync --locked` installs exactly the same versions you tested with, not whatever happens to be newest that day. Never edit it by hand; uv maintains it.

While you have `pyproject.toml` open, add these lines at the bottom. They matter in Module 7, and adding them now saves a confusing error later:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

This tells pytest to treat the project folder as the starting point for imports, the same way `python -m` does (see 1.7).

**Checkpoint, run in the terminal:**

```bash
uv run python -c "import apify_client, psycopg, yaml, dotenv; print('all good')"
```

It prints `all good`. The `-c` flag runs a one-line program. Note that some import names differ from package names: `pyyaml` installs `yaml`, and `python-dotenv` installs `dotenv`.

### 1.5 Lay out the folders

Delete `main.py`. Then, in VS Code's Explorer panel, use **New File** to create these four empty files. Typing a path like `core/__init__.py` creates the folder too.

```text
core/__init__.py
projects/__init__.py
projects/linkedin_jobs/__init__.py
tests/__init__.py
```

Also create two empty folders, `sql` and `.github/workflows`, with **New Folder**.

**Why `__init__.py`:** an empty file with this name tells Python "this folder is a package". That's what lets one file import another with `from core import settings`.

**Why `core/` and `projects/`:** this is the shared-framework split. The database connection, run log and text helpers go in `core/` and are written once. Each scraper gets its own folder under `projects/`. Today there's one scraper, `linkedin_jobs`. Your next scraping project adds a folder there and reuses everything in `core/` (Module 10).

Git doesn't track empty folders, so `sql/` and `.github/` won't show up on GitHub until later modules put files in them. That's expected.

### 1.6 Keep secrets out of git

The pipeline needs two secrets: your Apify token and your Supabase connection string. Each lives in one of two places, and never in the code:

| Where the code runs | Where the secrets live |
| --- | --- |
| Your computer | A `.env` file in the project folder, which git ignores |
| GitHub Actions (Module 8) | GitHub's encrypted repository secrets |

The code reads both places the same way, as **environment variables**: named values handed to a program when it starts. The `python-dotenv` package copies the contents of `.env` into the environment variables, so the code can't tell the two places apart.

**Step 1: tell git to ignore `.env`.** Open `.gitignore`. uv already listed Python's cache files and the `.venv` folder. Add these lines at the bottom:

```text
# Secrets: never commit
.env

# Local scraper samples (Module 2)
samples/
```

**Step 2: create `.env.example`.** This file is committed. It's a template that shows which settings exist, without their values:

```text
# Copy this file to .env and fill in the values. Never commit .env.
APIFY_TOKEN=
SUPABASE_DB_URL=
```

**Step 3: create `.env`** by copying `.env.example`, then fill in the values. Put nothing around them: no quotes, no spaces around `=`.

- `APIFY_TOKEN`: Apify Console → **Settings → API & Integrations** → copy the personal API token.
- `SUPABASE_DB_URL`: in your Supabase project, click **Connect** → **Session pooler** → copy the string, then replace `[YOUR-PASSWORD]` with the database password, brackets included.

Two Supabase gotchas:

- Use the **Session pooler** string, not **Direct connection**. The direct one only works over IPv6, which many home networks and GitHub's servers lack.
- If the password contains `@`, `#`, `/`, `:` or `%`, it breaks the URL. Reset the database password to letters and digits only (Project Settings → Database), which is the easiest fix.

No Supabase project yet? Leave that value empty for now. The script in 1.7 will tell you it's missing.

**Checkpoint, run in the terminal:**

```bash
git status
```

`.env.example` should be listed as a new file. **`.env` must not appear.** If it does, check the spelling in `.gitignore` and that the file is saved, then run `git status` again.

### 1.7 Your first module: `core/settings.py`

Every later step needs the secrets, so the first real code is a small module that reads them and fails with a clear message when one is missing. Create `core/settings.py`:

```python
"""Read settings from environment variables (.env locally, GitHub Secrets in automation)."""
import os

from dotenv import load_dotenv

REQUIRED = ["APIFY_TOKEN", "SUPABASE_DB_URL"]


def get(name: str) -> str:
    """Return a required setting, or stop with a clear message if it's missing."""
    load_dotenv()
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to .env (local) or GitHub Secrets (automation).")
    return value


def check() -> None:
    """Report which settings are present, without ever printing their values."""
    load_dotenv()
    for name in REQUIRED:
        value = os.environ.get(name, "")
        status = f"set ({len(value)} characters)" if value else "MISSING"
        print(f"{name:<16} {status}")


if __name__ == "__main__":
    check()
```

Line by line:

1. The triple-quoted string at the top is a **docstring**: a description of the file. VS Code shows it when you hover over an import of this module.
2. `import os` brings in Python's built-in module for talking to the operating system. Environment variables are in `os.environ`.
3. `from dotenv import load_dotenv` imports the one function we need from `python-dotenv`. The blank line between the two imports separates built-in modules from installed ones, a common convention.
4. `REQUIRED = [...]` lists the settings the pipeline can't run without. Capital letters signal a constant: a value that's set once and never changed.
5. `def get(name: str) -> str:` defines a function. `name: str` says the argument should be text, and `-> str` says the function returns text. These **type hints** don't change how the code runs; they let VS Code warn you about mistakes.
6. `load_dotenv()` finds `.env` in the project folder and copies its values into the environment variables. When there's no `.env`, as on GitHub, it does nothing and the secrets already in the environment are used.
7. `os.environ.get(name)` looks up the variable and returns `None` if it doesn't exist. The plainer `os.environ[name]` would crash with a confusing `KeyError` instead.
8. `if not value:` is true for both `None` and an empty string, so it catches a missing setting and a blank line in `.env` alike.
9. `raise RuntimeError(...)` stops the program with a message saying exactly what to fix. The `f` before the string makes it an **f-string**: `{name}` inside it is replaced by the variable's value.
10. `check()` loops over the required names and prints whether each is set, and how long it is. It never prints the value, so the output is safe to screenshot or paste into a chat.
11. `{name:<16}` pads the name to 16 characters, left-aligned, so the two lines of output line up.
12. `if __name__ == "__main__":` is true only when you run this file directly, not when another file imports it. Running it calls `check()`; importing it just makes `get()` available.

**Checkpoint, run in the terminal:**

```bash
uv run python -m core.settings
```

Expected output (your lengths will differ):

```text
APIFY_TOKEN      set (46 characters)
SUPABASE_DB_URL  set (117 characters)
```

**Why `-m core.settings` and not `core/settings.py`:** `-m` runs the file as a module of the project, starting from the project folder. That's what makes imports like `from core import settings` work from any file. Every script in this guide runs this way.

### 1.8 Knock on both doors

Having the secrets isn't the same as having working ones. This script makes the smallest possible request to each service, your first real API call. Create `core/check_connections.py`:

```python
"""One-off check that Apify and Supabase both accept our credentials."""
import psycopg
from apify_client import ApifyClient

from core import settings

# Apify: ask "who am I?"
apify = ApifyClient(settings.get("APIFY_TOKEN"))
me = apify.user().get()
print(f"Apify     OK, signed in as {me.username}")

# Supabase: ask the database for its version
with psycopg.connect(settings.get("SUPABASE_DB_URL")) as conn:
    version = conn.execute("select version()").fetchone()[0]
print(f"Supabase  OK, {version.split(',')[0]}")
```

Line by line:

1. Two package imports, then a blank line, then our own module. Grouping imports this way (installed packages, then your own code) is a convention that makes files easier to scan.
2. `from core import settings` imports the file you wrote in 1.7. This line only works because of the `__init__.py` files and running with `-m`.
3. `ApifyClient(...)` creates a client: an object that knows Apify's address and carries your token on every request. Creating it doesn't contact Apify yet.
4. `apify.user().get()` makes the actual request: "tell me about the account this token belongs to". The answer comes back as JSON, which the client turns into a Python object with one attribute per field.
5. `me.username` reads one attribute of that object. A wrong token fails on line 4 with an authentication error, before this line runs.
6. `psycopg.connect(...)` opens a connection to the database. The `with` block closes it automatically when the block ends, even if an error happens inside.
7. `conn.execute("select version()")` sends one line of SQL. `.fetchone()` returns the first row of the answer as a tuple, and `[0]` takes its first column.
8. `version.split(',')[0]` keeps the text before the first comma, so you see a short `PostgreSQL 17.x ...` instead of a long build description.

**Checkpoint, run in the terminal:**

```bash
uv run python -m core.check_connections
```

Both lines print `OK`. If one fails, the troubleshooting table at the end of this module covers the usual causes.

**Try this:** run it the other way, `uv run python core/check_connections.py`. You'll get `ModuleNotFoundError: No module named 'core'`. That's the problem `-m` solves.

### 1.9 Commit and push

**Run in the terminal.** Replace `<you>` with your GitHub username:

```bash
git add .
git status
git commit -m "Module 1: project skeleton and connection check"
git branch -M main
git remote add origin https://github.com/<you>/data-aggregator.git
git push -u origin main
```

What each line does:

1. `git add .` stages every changed file, except the ones `.gitignore` excludes.
2. `git status` lets you look before committing. Confirm once more that `.env` is not in the list.
3. `git commit` saves a snapshot with a message describing it.
4. `git branch -M main` names the branch `main`, which is what GitHub expects.
5. `git remote add origin ...` tells your local repo where its GitHub copy lives. You only do this once.
6. `git push -u origin main` uploads the commit. `-u` remembers the destination, so from now on plain `git push` works.

**Checkpoint:** on GitHub, the repo shows `core/`, `projects/`, `tests/`, `pyproject.toml` and `uv.lock`. There's no `.env` and no `.venv`.

### Check your understanding

1. Why do you commit `uv.lock` but not `.venv`?
2. You delete the `.venv` folder by accident. What happens the next time you type `uv run ...`?
3. Where does the Apify token live on your computer, and where will it live when GitHub runs the pipeline? How does the code read it in both cases?
4. Why does `check()` print the length of each secret instead of its value?
5. What would break if `core/__init__.py` didn't exist?

<details>
<summary>Answers</summary>

1. `uv.lock` is a small text file that pins exact versions, so every machine installs the same thing. `.venv` is large, specific to one operating system, and fully rebuildable from `uv.lock`.
2. Nothing bad: uv notices it's missing and rebuilds it from `uv.lock` before running the command.
3. In `.env` locally and in GitHub's repository secrets later. The code reads environment variables in both cases; `load_dotenv()` fills them from `.env` when that file exists.
4. So the output can be shared safely. The length still tells you whether the value looks right, or whether you pasted half of it.
5. `from core import settings` would fail, because Python wouldn't treat `core` as a package.

</details>

### Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `uv` is not recognized | The terminal started before uv was installed | Close every terminal and VS Code window, reopen, try again |
| Imports underlined in yellow, but the code runs | VS Code is using a different Python | Ctrl+Shift+P → **Python: Select Interpreter** → the one in `.venv` |
| `ModuleNotFoundError: No module named 'core'` | Running a file path instead of a module, or not in the project folder | Run `uv run python -m core.<name>` from the project folder |
| `APIFY_TOKEN ... MISSING` | `.env` is missing, misnamed or not saved | The file is named exactly `.env` (not `.env.txt`), sits next to `pyproject.toml` and is saved |
| Apify: `401`, or "authentication token is not valid" | Wrong or partly copied token | Copy it again from Settings → API & Integrations |
| Supabase: connection times out, or `could not translate host name` | Using the Direct connection string | Use the **Session pooler** string from **Connect** |
| Supabase: `password authentication failed` | `[YOUR-PASSWORD]` still in the URL, or special characters in the password | Paste the real password; reset it to letters and digits if it has symbols |
| `git push` is rejected | The GitHub repo was created with a README or .gitignore | Run `git pull origin main --allow-unrelated-histories`, then push again |

---

## Module 2: Calling Apify

By the end of this module you'll have run the LinkedIn scraper from your own code, for one search capped at 5 jobs, and saved the raw results to a file you can read. Cost: about one cent. Allow about 45 minutes.

### 2.1 How an Apify run works

Three Apify words to know:

| Word | What it is | In the shop analogy |
| --- | --- | --- |
| **Actor** | A program that lives on Apify's servers, here `curious_coder/linkedin-jobs-scraper` | An item on the menu |
| **Run** | One execution of an actor, with the input you gave it | One order being prepared |
| **Dataset** | The results a run produces, stored on Apify as a list of JSON items | The packaged order |

Your code makes two requests, in order:

1. "Start this actor with this input, and wait until it finishes." The answer is a description of the run: its status, its cost and the ID of its dataset.
2. "Give me the items in dataset X." The answer is the list of jobs.

The actor's input is a JSON object. These are the fields we use:

| Input field | Our value | What it does |
| --- | --- | --- |
| `keywords` | `"data scientist"` | What to search for, as you'd type it on LinkedIn |
| `location` | `"United States"` | Where |
| `datePosted` | `"pastMonth"` | Only jobs posted in the last month; matches the monthly schedule |
| `limitPerSource` | `5` now, `1000` later | Maximum jobs for this search; this is what you pay for |
| `scrapeCompany` | `true` | Also fetch company details (size, website); slower |
| `splitByLocation` | `false` | Search city by city to get past LinkedIn's 1,000-per-search cap |

### 2.2 Settings in a file: `config.yaml`

Search terms and limits will change more often than the code, so they live in a settings file. Create `projects/linkedin_jobs/config.yaml`:

```yaml
# What the LinkedIn jobs pipeline searches for each month.
# Change roles or limits here; no code changes needed.

actor_id: curious_coder/linkedin-jobs-scraper

searches:
  - data scientist
  - data analyst
  - machine learning engineer
  - analytics engineer
  - data engineer

location: United States
date_posted: pastMonth      # anyTime | past24Hours | pastWeek | pastMonth
limit_per_search: 1000      # LinkedIn returns at most ~1,000 per search
scrape_company: true        # extra company details (size, website); slower

# Search city by city to get past the 1,000 cap. More results = more cost.
split_by_location: false
split_country: US
```

How YAML works:

- `key: value` sets a setting. Text doesn't need quotes unless it contains a `:` or starts with a special character.
- Lines starting with `-` under a key form a list. `searches` is a list of five terms.
- `#` starts a comment, which is ignored.
- Indentation is meaningful, and it must be spaces, never tabs. VS Code inserts spaces by default for `.yaml` files.

When Python reads it with `yaml.safe_load`, you get a dictionary: `cfg["location"]` is `"United States"`, and `cfg["searches"]` is a list of five strings.

### 2.3 The scraper wrapper: `scrape.py`

Create `projects/linkedin_jobs/scrape.py`:

```python
"""Run the Apify LinkedIn Jobs Scraper for one search term and return its results."""
from apify_client import ApifyClient

from core import settings


def client() -> ApifyClient:
    """An Apify client that sends our token with every request."""
    return ApifyClient(settings.get("APIFY_TOKEN"))


def build_input(cfg: dict, term: str, limit: int) -> dict:
    """Translate our config into the input the actor expects."""
    run_input = {
        "keywords": term,
        "location": cfg["location"],
        "datePosted": cfg["date_posted"],
        "limitPerSource": int(limit),
        "scrapeCompany": bool(cfg.get("scrape_company", True)),
        "splitByLocation": bool(cfg.get("split_by_location", False)),
    }
    if run_input["splitByLocation"]:
        run_input["splitCountry"] = cfg.get("split_country", "US")
    return run_input


def run_search(apify: ApifyClient, cfg: dict, term: str, limit: int) -> tuple[list[dict], float]:
    """Start the actor, wait for it to finish, and return (items, cost in USD)."""
    run = apify.actor(cfg["actor_id"]).call(run_input=build_input(cfg, term, limit))
    if run is None:
        raise RuntimeError(f"Apify run for '{term}' returned nothing")
    if run.status != "SUCCEEDED":
        raise RuntimeError(f"Apify run for '{term}' ended with status {run.status}")
    items = list(apify.dataset(run.default_dataset_id).iterate_items())
    return items, float(run.usage_total_usd or 0.0)
```

Function by function:

**`client()`** creates an `ApifyClient` with your token. It's a function, rather than a client created at the top of the file, so nothing happens until you ask for it. Importing `scrape.py` in a test doesn't need a token.

**`build_input(cfg, term, limit)`** translates our settings into the actor's input fields. Two details:

- Our config uses `snake_case` names (`date_posted`), Python's convention. The actor expects `camelCase` (`datePosted`), the JavaScript convention. This function is the one place that knows both.
- `cfg.get("scrape_company", True)` reads the setting, or uses `True` if the line is missing from the file. `cfg["location"]`, with square brackets, has no fallback: a missing location should be an error.
- `splitCountry` is only added when splitting is on, because the actor requires it in that case.

**`run_search(apify, cfg, term, limit)`** does the two requests from 2.1:

1. `apify.actor(cfg["actor_id"])` points at the actor. `.call(run_input=...)` starts it and waits until it finishes, which can take from 30 seconds to several minutes.
2. `.call()` returns a `run` object, or `None` if something went badly wrong. Both checks raise an error with the search term in the message, so a failure in month 6 tells you which search broke.
3. `run.status` is a word such as `SUCCEEDED`, `FAILED`, `ABORTED` or `TIMED-OUT`. Anything other than success is treated as an error.
4. `apify.dataset(run.default_dataset_id).iterate_items()` fetches the results. `iterate_items` pages through them automatically, so it works for 5 items or 5,000. `list(...)` collects them all into a Python list.
5. `run.usage_total_usd` is what the run cost you. `or 0.0` replaces a missing value with zero.

The function returns a **tuple**, two values at once. The caller unpacks it with `items, cost = run_search(...)`.

### 2.4 A first run: `explore.py`

Create `projects/linkedin_jobs/explore.py`:

```python
"""Module 2: run one small search and save the raw results to look at."""
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
out.write_text(json.dumps(items, indent=2, ensure_ascii=False))
print(f"Got {len(items)} jobs for ${cost:.4f}. Saved to {out}")
print("Fields in the first job:", ", ".join(items[0].keys()) if items else "(none)")
```

Line by line, the parts that are new:

1. `from pathlib import Path` imports Python's tool for file paths. `Path(__file__).parent` is the folder this file is in, so the script finds `config.yaml` wherever you run it from.
2. `yaml.safe_load(...read_text())` reads the file and turns the YAML into a dictionary. Always use `safe_load`, never `load`: it refuses YAML that tries to run code.
3. `term = cfg["searches"][0]` takes the first search term, `data scientist`.
4. `limit=5` overrides the config's 1,000 for this test.
5. `out.parent.mkdir(exist_ok=True)` creates the `samples` folder if it doesn't exist yet. You added `samples/` to `.gitignore` in 1.6, so these files stay on your computer.
6. `json.dumps(items, indent=2, ensure_ascii=False)` turns the list back into JSON text, indented so it's readable. `ensure_ascii=False` keeps characters like `é` as they are instead of escape codes.
7. `${cost:.4f}` formats the cost with four decimals, since it's a fraction of a cent.

**Checkpoint, run in the terminal:**

```bash
uv run python -m projects.linkedin_jobs.explore
```

It takes a minute or two. The actor also prints its own progress lines as it works. Expect:

```text
Running the scraper for 'data scientist', 5 jobs...
Got 5 jobs for $0.0100. Saved to samples/raw_sample.json
Fields in the first job: id, link, title, companyName, ...
```

In Apify Console, under **Runs**, you'll see the same run listed, with its input and its dataset. That's the other side of the counter.

### 2.5 Read the raw data

Open `samples/raw_sample.json` in VS Code. Each job is a JSON object: `{ "key": value, ... }`. Here's what the main fields hold and what we'll do with them in Module 3:

| Raw field | Example | Keep? |
| --- | --- | --- |
| `id` | `"4012345678"` | Yes: LinkedIn's job ID, the key for deduplication |
| `title`, `companyName`, `location` | `"Senior Data Scientist"` | Yes |
| `descriptionText` | The full description, plain text | Yes: the source for themes |
| `descriptionHtml` | The same description with HTML tags | No: duplicates `descriptionText`, and much larger |
| `industries` | `"Hospitals and Health Care"` | Yes; sometimes several, comma-separated |
| `seniorityLevel`, `employmentType`, `jobFunction` | `"Mid-Senior level"` | Yes |
| `salaryInfo` | `["$130,000.00/yr", "$160,000.00/yr"]` | Yes, parsed into numbers |
| `postedAt` | `"2026-09-28"` | Yes, as a date |
| `applicantsCount` | `"87"` or `"Over 200 applicants"` | Yes, parsed into a number |
| `companyEmployeesCount` | `5400` | Yes |
| `workplaceTypes`, `workRemoteAllowed` | `["Remote"]`, `true` | Yes: remote, hybrid or on-site |
| `jobPosterName`, `jobPosterTitle`, `jobPosterPhoto`, `jobPosterProfileUrl` | A recruiter's name and profile | **No: personal data about a third party, and you don't need it** |
| `companyLogo`, `benefits`, `applyUrl` | | Not needed for the analysis; kept only in the raw copy |

Things to notice in your own sample, because Module 3 has to handle them:

- Numbers often arrive as **text**: `"87"`, or even `"Over 200 applicants"`.
- Salaries arrive as a list of formatted strings, sometimes hourly, sometimes yearly, often missing entirely.
- Some fields are missing from some jobs. Code that assumes every key exists will crash on the first job that lacks one.

The actor's own documentation warns that its sample output may be out of date, so your file is the source of truth. If a field name in your sample differs from this table, use yours in Module 3.

**Commit:**

```bash
git add .
git commit -m "Module 2: call the Apify scraper"
git push
```

### Check your understanding

1. What's the difference between an actor, a run and a dataset?
2. Why does `run_search` check `run.status` instead of just fetching the dataset?
3. Why is `limit` the setting that controls your bill?
4. Why does `samples/` belong in `.gitignore`?

<details>
<summary>Answers</summary>

1. The actor is the program, a run is one execution of it, and the dataset is that run's output.
2. A failed run can still have a dataset, empty or half-filled. Checking the status stops you from silently saving partial results as if they were complete.
3. This actor charges per result returned, so the maximum number of jobs is the maximum cost: 1,000 results cost about $1 on the Starter plan.
4. They're scratch files that change every time you run the script, and they contain recruiter names you've decided not to keep.

</details>

### Common failures

| Symptom | Fix |
| --- | --- |
| `Actor with this name was not found` | Check `actor_id` in `config.yaml` for typos |
| `ended with status FAILED` | Open the run in Apify Console → **Log** tab; the actor says what it rejected (often an input value) |
| `Got 0 jobs` | Try a broader search or `datePosted: pastMonth`; check the run's log in Apify Console |
| It seems to hang | `.call()` waits for the whole run; watch progress in Apify Console → **Runs** |

---

## Module 3: Shaping the data

By the end of this module, each raw job becomes one clean row: proper numbers and dates, no personal data, a fingerprint for spotting reposts, and a list of themes found in its description. Allow about an hour.

### 3.1 From raw to clean

Every decision in this module comes from what you saw in 2.5. Here's the plan:

| Clean column | From raw field | Conversion |
| --- | --- | --- |
| `job_id` | `id` | Text (IDs aren't numbers you do math with) |
| `primary_industry` | `industries` | The first industry before a comma |
| `salary_min`, `salary_max`, `salary_period` | `salaryInfo` | Parse `"$130,000.00/yr"` into `130000.0` and `"yr"` |
| `applicants_count`, `company_employees` | `applicantsCount`, `companyEmployeesCount` | The first number in the text |
| `posted_at` | `postedAt` | A real date |
| `workplace_type` | `workplaceTypes` or `workRemoteAllowed` | `"Remote"`, `"Hybrid"` etc. |
| `content_hash` | company + title + location + description | A fingerprint (3.2) |
| `themes` | title + description | A list of matched themes (3.2, 3.3) |
| `search_terms` | Which searches found the job | A sorted list |

### 3.2 Shared text helpers: `core/text.py`

These helpers live in `core/` because any future scraper can use them. Create `core/text.py`:

```python
"""Text helpers shared by projects: content hashing and keyword theme tagging."""

import hashlib
import re
from pathlib import Path

import yaml

_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w\s]")


def normalize(text: str | None) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    if not text:
        return ""
    return _WS.sub(" ", _NON_WORD.sub(" ", text.lower())).strip()


def content_hash(*parts: str | None) -> str:
    """Stable fingerprint of a record's content, used to spot reposts."""
    joined = "\x1f".join(normalize(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class ThemeTagger:
    """Tags text with themes whose signal phrases appear in it.

    themes.yaml format:
        - theme: Generative AI & LLMs
          phrases: [llm, large language model, rag, prompt engineering]
    Phrases match whole words, case-insensitively.
    """

    def __init__(self, themes: list[dict]):
        self.patterns = []
        for t in themes:
            alts = "|".join(re.escape(p.strip()) for p in t["phrases"] if p.strip())
            self.patterns.append((t["theme"], re.compile(rf"(?<!\w)(?:{alts})(?!\w)", re.I)))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ThemeTagger":
        return cls(yaml.safe_load(Path(path).read_text()))

    def tag(self, text: str | None) -> list[str]:
        if not text:
            return []
        return [theme for theme, pat in self.patterns if pat.search(text)]
```

**Regular expressions** (the `re` module) are patterns for matching text. You only need to read three here:

| Pattern | Means |
| --- | --- |
| `\s+` | One or more whitespace characters: spaces, tabs, line breaks |
| `[^\w\s]` | Any one character that's not a letter, digit, underscore or whitespace, i.e. punctuation |
| `(?<!\w)(?:a\|b)(?!\w)` | `a` or `b`, as a whole word: no letter or digit directly before or after |

`re.compile(...)` prepares a pattern once, at the top of the file, so it isn't rebuilt for every job.

**`normalize(text)`** makes two texts comparable even when they differ only in case, punctuation or spacing. `"Senior Data Scientist!"` and `"senior  data scientist"` both become `"senior data scientist"`.

**`content_hash(*parts)`** builds the repost fingerprint:

1. `*parts` means "any number of arguments", collected into a tuple. You'll call it with four: company, title, location, description.
2. Each part is normalized, then they're joined with `\x1f`, an invisible separator character that never appears in real text. Without a separator, `("ab", "c")` and `("a", "bc")` would join to the same `"abc"`.
3. `hashlib.sha256(...)` turns the text into a 64-character fingerprint. The same input always gives the same fingerprint, and any change gives a completely different one. Storing 64 characters is cheaper than comparing whole descriptions.

**`ThemeTagger`** is a **class**: a recipe for an object that bundles data (the compiled patterns) with the functions that use it (`tag`).

- `__init__` runs when you create a tagger. For each theme, it joins the theme's phrases into one pattern: `llm|large language model|rag`. `re.escape` makes characters like `/` in `a/b testing` or `.` match literally. `re.I` makes the match case-insensitive.
- `@classmethod from_yaml(cls, path)` is a second way to create a tagger, from a YAML file instead of a list. `cls` is the class itself, so `cls(...)` calls `__init__`.
- `tag(text)` returns every theme with at least one phrase in the text. The **list comprehension** `[theme for theme, pat in self.patterns if pat.search(text)]` is a compact loop that builds a list.

**Why whole words:** without `(?<!\w)` and `(?!\w)`, the phrase `rag` (retrieval-augmented generation) would match inside "sto**rag**e", "ave**rag**e" and "cove**rag**e", and every job mentioning storage would be tagged as GenAI work. Whole-word matching prevents that.

### 3.3 The themes: `themes.yaml`

Create `projects/linkedin_jobs/themes.yaml`:

```yaml
# Themes tagged in each job description. A posting gets a theme when any phrase
# appears as a whole word (case-insensitive). Edit freely; re-tag history with:
#   python -m projects.linkedin_jobs.run --retag

- theme: Machine learning modeling
  phrases: [machine learning, predictive model, predictive models, predictive modeling, classification, regression models, gradient boosting, xgboost, lightgbm, random forest, scikit-learn, sklearn, deep learning, pytorch, tensorflow]

- theme: Generative AI & LLMs
  phrases: [generative ai, genai, gen ai, llm, llms, large language model, large language models, rag, retrieval augmented, retrieval-augmented, prompt engineering, fine-tuning, fine tuning, langchain, ai agents, agentic]

- theme: Experimentation & causal inference
  phrases: [a/b test, a/b testing, ab testing, experimentation, experiment design, controlled experiments, causal inference, causal, uplift, difference-in-differences, quasi-experimental]

- theme: SQL & data pipelines
  phrases: [sql, etl, elt, dbt, data pipeline, data pipelines, airflow, spark, pyspark, snowflake, bigquery, data warehouse, data modeling]

- theme: Statistical rigor
  phrases: [statistics, statistical, hypothesis testing, bayesian, inference, statistical modeling, survival analysis, time-to-event]

- theme: Cloud & MLOps
  phrases: [aws, azure, gcp, google cloud, databricks, mlops, mlflow, sagemaker, model deployment, deploy models, docker, kubernetes, ci/cd, production models]

- theme: Stakeholder communication
  phrases: [stakeholder, stakeholders, cross-functional, storytelling, communicate findings, communication skills, executive, business partners, translate business]

- theme: Dashboards & BI
  phrases: [dashboard, dashboards, tableau, power bi, looker, business intelligence, kpi, kpis, reporting]

- theme: Forecasting & time series
  phrases: [forecasting, forecast, time series, time-series, demand planning, arima, prophet]

- theme: Product analytics
  phrases: [product analytics, product metrics, funnel, funnels, retention, user behavior, engagement metrics, growth analytics]
```

This is the one file in the project where your judgment matters more than code. Edit it freely: add phrases you see in real descriptions, split a theme in two, or add one that matters to your own career, such as `Survival analysis` or `Causal inference` on its own. Each entry is a dictionary with a `theme` and a list of `phrases`. Square brackets are YAML's one-line way of writing a list.

Keyword tagging is crude but free, fast and transparent: you can always see why a job got a theme. Replacing it with an LLM is an optional upgrade later, and the rest of the pipeline wouldn't change.

### 3.4 The transform: `transform.py`

Create `projects/linkedin_jobs/transform.py`:

```python
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
    sal_min, sal_max, sal_period = parse_salary(item.get("salaryInfo"))
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
```

Function by function:

**`PERSONAL_KEYS` and `strip_personal(item)`.** A set of the four recruiter fields, and a **dictionary comprehension** that copies the item without them. This runs before anything is stored, including the raw copy, so recruiter names never reach your database.

**`_int(v)` and `_date(v)`.** The leading underscore marks them as private helpers, used only inside this file.

- `_int` finds the first run of digits in the text (`\d[\d,]*` means a digit followed by digits or commas) and returns it as a number. `"Over 200 applicants"` becomes `200`, and missing or empty values become `None`.
- `_date` takes the first 10 characters (`2026-09-28`) and parses them. `try ... except ValueError` catches text that isn't a valid date and returns `None` instead of crashing.

**`parse_salary(info)`** is the fiddliest function, because salaries come in many formats:

1. `_MONEY` matches an optional `$`, a number with commas and decimals, and an optional `K`. `findall` returns every match in the text.
2. Each amount is converted to a number, multiplied by 1,000 if it had a `K`, and zeros are dropped.
3. The period comes from `/yr`, `/hr` and similar, mapped to a standard spelling by the `_PERIODS` dictionary. If there's no period in the text, a guess: under 500 is probably hourly, anything else yearly.
4. It returns the smallest and largest amount, so a single salary gives min = max.

**`workplace(item)`** checks `workplaceTypes` first (a list, or sometimes text), then falls back to `workRemoteAllowed`. If neither says anything, it returns `None` rather than guessing.

**`to_row(item, search_terms, tagger)`** builds one clean row as a dictionary whose keys match the database columns you'll create in Module 4. Things to notice:

- `item.get("title")` everywhere, never `item["title"]`: a missing field becomes `None` instead of a crash.
- `item.get("seniorityLevel") or None` also turns an empty string `""` into `None`, so the database stores "unknown" consistently.
- `industries.split(",")[0].strip()` keeps the first industry and trims spaces.
- Themes are tagged on the title plus the description, because a title like "Machine Learning Engineer" says something too.
- `sorted(set(search_terms))` removes duplicate terms and sorts them, so the same job always gets the same list.

**`merge_items(batches)`** combines the results of several searches. `batches` is a dictionary like `{"data scientist": [job, job, ...], "data analyst": [...]}`. A job found by two searches is kept once, with both terms recorded. Jobs without an `id` are skipped, since nothing downstream can work without one. The result maps each job ID to a pair: the cleaned raw item, and the list of terms that found it.

### 3.5 Try it on your sample

Start an interactive Python session in the terminal:

```bash
uv run python
```

At the `>>>` prompt, type these lines one at a time:

```python
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
```

After the `for` line, press Enter on an empty line to run the loop. Type `exit()` to leave.

**Checkpoint:** each of your 5 jobs prints with an industry, a salary where the posting had one, and a list of themes. The last line prints `(45.0, 55.0, 'hr')`.

Now read one job's `descriptionText` in `raw_sample.json` yourself and compare it with its themes. Did the tagger miss a theme you'd give it? Add the phrase to `themes.yaml`, rerun the lines above, and check again. This loop is how the themes get good.

**Commit:**

```bash
git add .
git commit -m "Module 3: clean rows, content hash and theme tagging"
git push
```

### Check your understanding

1. Why is `job_id` stored as text when it looks like a number?
2. Two postings have the same company, title and location, but one description has an extra sentence. Do they get the same `content_hash`?
3. Why does `to_row` use `item.get("title")` instead of `item["title"]`?
4. Why does `strip_personal` run before the raw copy is saved, not just before the clean table?

<details>
<summary>Answers</summary>

1. You never do math with it, and some systems drop leading zeros or round very long numbers. Text keeps it exactly as LinkedIn wrote it.
2. No. Any change produces a different hash. That's deliberate: it only catches exact reposts, which is most of them. Near-duplicates need fuzzy matching, a possible later upgrade.
3. Some jobs lack some fields. `.get` returns `None` for a missing key; square brackets would crash the whole run on the first incomplete job.
4. The decision is not to store recruiters' personal data at all. Keeping it in the raw table would store it anyway.

</details>

---

## Module 4: The database

By the end of this module, your Supabase database has the tables and views the pipeline writes to, created by code you can re-run safely at any time. Allow about an hour.

### 4.1 Postgres in five ideas

Supabase is a hosted **Postgres** database with a web interface on top. Five ideas cover everything this project needs:

1. **Tables** hold rows, and every column has a type. Postgres rejects a row whose values don't fit, which is what keeps the data clean.
2. A **schema** is a folder of tables. Ours: `core` for shared tables, `jobs` for this scraper. A future scraper gets its own schema.
3. A **primary key** is a column (or set of columns) whose value must be unique in the table. `job_id` is ours: the database itself refuses a second row for the same job.
4. A **view** is a saved query that looks like a table. It stores no data; it runs its query each time you read it.
5. **Migrations** are the `.sql` files that create all of the above. Written as "create if it doesn't exist", they're safe to run again and again.

The column types we use:

| Type | Holds | Example |
| --- | --- | --- |
| `text` | Any text | Titles, IDs, descriptions |
| `integer`, `bigint` | Whole numbers (bigint for very large ones) | Applicant counts, run IDs |
| `bigserial` | A `bigint` that numbers itself 1, 2, 3... | `run_id` |
| `numeric(10, 4)` | Exact decimals: 10 digits, 4 after the point | Costs |
| `date`, `timestamptz` | A day; a moment in time with its time zone | `posted_at`; `started_at` |
| `text[]` | A list of text values | `themes`, `search_terms` |
| `jsonb` | A whole JSON document | The raw scraper item |

### 4.2 Shared tables: `sql/001_core.sql`

Create `sql/001_core.sql`:

```sql
-- Shared tables used by every scraping project.
-- Safe to re-run: everything is "if not exists".

create schema if not exists core;

-- One row per pipeline run, across all projects.
create table if not exists core.run_log (
    run_id       bigserial primary key,
    project      text        not null,
    started_at   timestamptz not null default now(),
    finished_at  timestamptz,
    status       text        not null default 'running',  -- running | succeeded | failed
    params       jsonb,
    rows_fetched integer,
    rows_new     integer,
    cost_usd     numeric(10, 4),
    error        text
);

create index if not exists run_log_project_started_idx
    on core.run_log (project, started_at desc);
```

Reading it:

- `--` starts a comment in SQL.
- `create schema if not exists core;` makes the folder. Every statement ends with `;`.
- `run_id bigserial primary key` numbers each run automatically and makes the number unique.
- `not null` means the column must have a value. `default now()` fills `started_at` with the current time when you don't provide one.
- `status` starts as `'running'` and is updated when the run ends. SQL text values use single quotes.
- The **index** at the end is like a book's index: it makes "the latest runs for this project" fast to find. With a handful of runs a month it hardly matters; it's here as a habit.

### 4.3 The jobs tables: `sql/010_linkedin_jobs.sql`

The files are numbered `001`, `010`, `020` so they sort in the order they must run (the jobs tables refer to `core.run_log`), with gaps for files added later. Create `sql/010_linkedin_jobs.sql`:

```sql
-- LinkedIn job postings project.
-- Safe to re-run: everything is "if not exists" / "create or replace".

create schema if not exists jobs;

-- Raw landing table: exactly what the scraper returned (minus personal fields),
-- one row per job per run. Lets you rebuild the clean table without re-scraping.
create table if not exists jobs.raw_postings (
    run_id      bigint      not null references core.run_log (run_id),
    job_id      text        not null,
    scraped_at  timestamptz not null default now(),
    search_terms text[]     not null,
    payload     jsonb       not null,
    primary key (run_id, job_id)
);

-- Clean table: one row per LinkedIn job ID, ever.
create table if not exists jobs.postings (
    job_id            text primary key,
    title             text,
    company_name      text,
    company_url       text,
    company_employees integer,
    location          text,
    industries        text,
    primary_industry  text,
    seniority_level   text,
    employment_type   text,
    job_function      text,
    workplace_type    text,
    salary_min        numeric,
    salary_max        numeric,
    salary_period     text,          -- yr | hr | mo | wk
    posted_at         date,
    applicants_count  integer,
    link              text,
    description_text  text,
    content_hash      text,          -- same role reposted under a new job ID shares this
    themes            text[] not null default '{}',
    search_terms      text[] not null default '{}',
    first_seen_at     date    not null,
    last_seen_at      date    not null,
    times_seen        integer not null default 1,
    first_run_id      bigint references core.run_log (run_id),
    last_run_id       bigint references core.run_log (run_id)
);

create index if not exists postings_first_seen_idx on jobs.postings (first_seen_at);
create index if not exists postings_content_hash_idx on jobs.postings (content_hash);
create index if not exists postings_industry_idx on jobs.postings (primary_industry);

-- One row per distinct role: collapses reposts (same content_hash, new job ID)
-- to the earliest-seen posting, and spans the full window the role was visible.
create or replace view jobs.postings_dedup as
select distinct on (p.content_hash)
       p.*,
       min(p.first_seen_at) over (partition by p.content_hash) as role_first_seen_at,
       max(p.last_seen_at)  over (partition by p.content_hash) as role_last_seen_at,
       count(*)             over (partition by p.content_hash) as repost_count
from jobs.postings p
order by p.content_hash, p.first_seen_at, p.job_id;

-- Theme coverage: one row per posting x theme, handy for BI tools.
create or replace view jobs.posting_themes as
select p.job_id, p.primary_industry, p.seniority_level, p.first_seen_at, t.theme
from jobs.postings_dedup p
cross join lateral unnest(p.themes) as t(theme);
```

**`jobs.raw_postings`** keeps every job exactly as scraped, once per run.

- `primary key (run_id, job_id)` is a **composite key**: the pair must be unique, so a job appears once per run but can appear in many runs.
- `references core.run_log (run_id)` is a **foreign key**: every raw row must belong to a run that exists in the run log.
- **Why keep raw data at all:** when you improve the transform in six months, you can rebuild the clean table from this one without paying to scrape again.

**`jobs.postings`** is the clean table, one row per job ever seen. The columns match the dictionary `to_row` builds in Module 3, plus the bookkeeping columns Module 5 maintains: `first_seen_at`, `last_seen_at`, `times_seen`, `first_run_id` and `last_run_id`. `themes text[] not null default '{}'` stores a list, with `'{}'` (an empty list) as the default.

**`jobs.postings_dedup`** is a view that collapses reposts to one row per role:

- `distinct on (p.content_hash)` keeps one row per fingerprint. Which one? The first in the `order by`: the earliest `first_seen_at`.
- `min(...) over (partition by p.content_hash)` is a **window function**: it computes across all rows sharing that fingerprint without collapsing them. So the surviving row knows when the role was first seen across all its reposts (`role_first_seen_at`), when it was last seen (`role_last_seen_at`) and how many postings it had (`repost_count`).

**`jobs.posting_themes`** unpacks the theme lists into one row per job and theme. `cross join lateral unnest(p.themes)` means "for each job, one row per element of its themes list". BI tools handle that shape far more easily than a list column.

### 4.4 Connecting from Python: `core/db.py`

Create `core/db.py`:

```python
"""Database connection and migrations, shared by every project."""
from pathlib import Path

import psycopg

from core import settings

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def connect() -> psycopg.Connection:
    """Open a connection to the Supabase database."""
    return psycopg.connect(settings.get("SUPABASE_DB_URL"), prepare_threshold=None)


def migrate(conn: psycopg.Connection) -> list[str]:
    """Run every sql/*.sql file in name order. Each file is safe to re-run."""
    applied = []
    for path in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(path.read_text())
        applied.append(path.name)
    conn.commit()
    return applied


def ping(conn: psycopg.Connection) -> int:
    """A tiny query that counts as database activity (keeps a free project awake)."""
    return conn.execute("select count(*) from core.run_log").fetchone()[0]


if __name__ == "__main__":
    import sys

    with connect() as conn:
        if sys.argv[1:] == ["ping"]:
            print(f"Database awake. Runs logged so far: {ping(conn)}")
        else:
            for name in migrate(conn):
                print(f"Applied {name}")
```

- `SQL_DIR` finds the `sql` folder relative to this file: `.parent` is `core/`, and `.parent.parent` the project folder. `.resolve()` turns it into a full path first.
- `connect()` opens a connection using the secret from `settings`. `prepare_threshold=None` turns off a psycopg optimization (prepared statements) that some connection poolers don't support. Leaving it off costs nothing at this scale and avoids a confusing error.
- `migrate(conn)` runs every `.sql` file in name order. `sorted(...)` is what makes the numbering matter. `conn.commit()` saves everything at once at the end (more on commits in Module 5).
- `ping(conn)` runs a tiny query. Module 8 uses it weekly so Supabase's free tier doesn't pause the project for inactivity.
- The `__main__` block gives the file two jobs from the terminal: `python -m core.db` migrates, and `python -m core.db ping` pings. `sys.argv` is the list of words typed after the script name, so `sys.argv[1:] == ["ping"]` checks for exactly one extra word, `ping`.

### 4.5 Create the tables

**Run in the terminal:**

```bash
uv run python -m core.db
```

**Checkpoint:** it prints

```text
Applied 001_core.sql
Applied 010_linkedin_jobs.sql
```

In Supabase, open **Table Editor**, switch the schema dropdown (top left) from `public` to `jobs`, and you'll see `raw_postings` and `postings`, both empty. Switch to `core` for `run_log`.

Now run the same command again. It succeeds with the same output and changes nothing. That's what **idempotent** means, and it's why Module 8 can run migrations automatically whenever a `.sql` file changes.

**Why not create tables by clicking in Supabase:** clicks leave no record. A `.sql` file in git documents exactly what the database looks like, shows how it changed over time, and can rebuild it from scratch in seconds.

Supabase exposes the `public` schema through an automatic web API. The `core` and `jobs` schemas aren't exposed, so only something holding your connection string can read them. If the Table Editor shows a warning about Row Level Security, it applies to API access, which these schemas don't have.

### 4.6 Practice: a few queries

Open Supabase's **SQL Editor** and run these one at a time. They're harmless: the last one removes what the first one adds.

```sql
-- Add a pretend run
insert into core.run_log (project, status) values ('practice', 'succeeded');

-- See it
select run_id, project, status, started_at from core.run_log;

-- Count jobs (zero for now)
select count(*) from jobs.postings;

-- Remove the pretend run
delete from core.run_log where project = 'practice';
```

**Commit:**

```bash
git add .
git commit -m "Module 4: database schema and migrations"
git push
```

### Check your understanding

1. Why does `raw_postings` use `(run_id, job_id)` as its key, while `postings` uses `job_id` alone?
2. What does a view store?
3. You add a column to `jobs.postings` in `010_linkedin_jobs.sql` and re-run the migration. Does the column appear? (Hint: read the first line of the table definition.)
4. Why are the SQL files numbered?

<details>
<summary>Answers</summary>

1. The raw table records every sighting, so the same job appears once per run. The clean table records each job once, ever.
2. Nothing but its query. The data always comes fresh from the tables underneath.
3. No. `create table if not exists` skips the whole statement because the table exists. Changing an existing table takes a separate statement, `alter table jobs.postings add column if not exists ...`, added to the file. Watch for this whenever you change a table.
4. They run in sorted order, and later files depend on earlier ones: the jobs tables reference the run log.

</details>

---

## Module 5: Loading without duplicates

By the end of this module, loading the same jobs twice no longer creates duplicates. Instead, it updates when each job was last seen. Allow about an hour.

### 5.1 Three cases

Every job in a monthly run is one of three cases:

| Case | Example | What should happen |
| --- | --- | --- |
| New | First time this `job_id` appears | Insert it; `first_seen_at` = today |
| Seen again | Still open from last month, or found by two searches | Don't insert; update `last_seen_at`, add 1 to `times_seen`, merge `search_terms` |
| Repost | Same role, new `job_id` | Insert it (it is a new ID); the matching `content_hash` lets `postings_dedup` group it with the original |

The first two are handled by one SQL statement, an **upsert**. The third needs nothing extra: Module 3's fingerprint and Module 4's view already cover it.

### 5.2 Upsert in four lines

Paste this into Supabase's SQL Editor and run it as one script:

```sql
create temp table demo (id text primary key, seen int not null default 1);
insert into demo (id) values ('a'), ('b');
insert into demo (id) values ('b'), ('c')
on conflict (id) do update set seen = demo.seen + 1
returning id, seen, (xmax = 0) as inserted;
```

The result:

```text
 id | seen | inserted
----+------+----------
 b  |    2 | false
 c  |    1 | true
```

What happened:

1. `create temp table` makes a table that disappears when the session ends, so practice leaves nothing behind.
2. The first insert adds `a` and `b`.
3. The second insert tries `b` and `c`. `c` is new, so it's inserted. `b` hits the primary key, a **conflict**, and instead of failing, `on conflict (id) do update` runs: `seen` goes from 1 to 2.
4. `returning` sends back a row for each row inserted or updated. `(xmax = 0)` is a Postgres trick: `xmax` is a hidden system column that's 0 on a freshly inserted row and non-zero on an updated one. That's how the pipeline counts "new jobs" without a second query.

Inside `do update`, `demo.seen` is the value already in the table. The incoming row's values are available as `excluded.<column>`, which you'll see in the real version next.

### 5.3 Transactions

A **transaction** groups statements so they succeed or fail together. psycopg starts one automatically with your first statement. Nothing is permanent until `conn.commit()`; if anything fails, `conn.rollback()` (or closing the connection without committing) undoes all of it.

For this pipeline, that means a month's raw rows and clean rows are saved together or not at all. You never end up with raw rows for a run whose clean rows failed halfway.

### 5.4 The loader: `load.py`

Create `projects/linkedin_jobs/load.py`:

```python
"""Write raw items and clean rows to Supabase, deduplicating on LinkedIn job ID."""

from datetime import date

import psycopg
from psycopg.types.json import Jsonb

COLUMNS = [
    "job_id", "title", "company_name", "company_url", "company_employees", "location",
    "industries", "primary_industry", "seniority_level", "employment_type", "job_function",
    "workplace_type", "salary_min", "salary_max", "salary_period", "posted_at",
    "applicants_count", "link", "description_text", "content_hash", "themes", "search_terms",
]

# Fields refreshed from the latest scrape when a job is seen again.
REFRESH = [c for c in COLUMNS if c not in ("job_id", "search_terms")]


def insert_raw(conn: psycopg.Connection, run_id: int, merged: dict[str, tuple[dict, list[str]]]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "insert into jobs.raw_postings (run_id, job_id, search_terms, payload) values (%s, %s, %s, %s)"
            " on conflict (run_id, job_id) do nothing",
            [(run_id, jid, sorted(set(terms)), Jsonb(item)) for jid, (item, terms) in merged.items()],
        )


def upsert_postings(conn: psycopg.Connection, run_id: int, rows: list[dict], seen_on: date) -> int:
    """Insert new jobs; for known jobs update last_seen_at/times_seen. Returns # of new jobs."""
    if not rows:
        return 0
    cols = ", ".join(COLUMNS)
    placeholders = ", ".join(f"%({c})s" for c in COLUMNS)
    refresh = ",\n        ".join(f"{c} = coalesce(excluded.{c}, p.{c})" for c in REFRESH)
    with conn.cursor() as cur:
        cur.execute(
            "create temp table stage (like jobs.postings including defaults) on commit drop"
        )
        cur.executemany(f"insert into stage ({cols}, first_seen_at, last_seen_at) values ({placeholders}, current_date, current_date)", rows)
        cur.execute(
            f"""
            insert into jobs.postings as p
                ({cols}, first_seen_at, last_seen_at, times_seen, first_run_id, last_run_id)
            select {cols}, %(seen)s, %(seen)s, 1, %(run)s, %(run)s from stage
            on conflict (job_id) do update set
                {refresh},
                search_terms = (select array_agg(distinct t order by t)
                                  from unnest(p.search_terms || excluded.search_terms) as t),
                last_seen_at = greatest(p.last_seen_at, excluded.last_seen_at),
                times_seen   = p.times_seen + case when p.last_run_id = excluded.last_run_id then 0 else 1 end,
                last_run_id  = excluded.last_run_id
            returning (xmax = 0) as inserted
            """,
            {"seen": seen_on, "run": run_id},
        )
        new = sum(1 for (inserted,) in cur.fetchall() if inserted)
    return new


def retag_all(conn: psycopg.Connection, tagger) -> int:
    """Re-apply themes.yaml to every stored description (after editing themes)."""
    rows = conn.execute("select job_id, title, description_text from jobs.postings").fetchall()
    with conn.cursor() as cur:
        cur.executemany(
            "update jobs.postings set themes = %s where job_id = %s",
            [(tagger.tag(f"{t or ''}\n{d or ''}"), jid) for jid, t, d in rows],
        )
    conn.commit()
    return len(rows)
```

**`COLUMNS` and `REFRESH`.** `COLUMNS` lists the clean columns in one place, so the SQL below is built from it rather than typed out three times. `REFRESH` is every column except `job_id` (the key never changes) and `search_terms` (merged separately). These get the latest scraped values when a job is seen again: a title edit or a new applicant count.

**`insert_raw(conn, run_id, merged)`** writes one raw row per job:

- `cur.executemany(sql, list_of_values)` runs the same statement once per item in the list, in a single efficient batch.
- `%s` marks where each value goes. **Never** build SQL by pasting values into the string yourself: psycopg sends values separately from the SQL, which is what makes text like `O'Brien` or a malicious description safe.
- `Jsonb(item)` tells psycopg to store the dictionary as JSON.
- `on conflict (run_id, job_id) do nothing` makes re-running a load for the same run harmless.

**`upsert_postings(conn, run_id, rows, seen_on)`** is 5.2 at full size, in two steps:

1. **Staging.** `create temp table stage (like jobs.postings including defaults) on commit drop` makes an empty copy of the clean table's structure that vanishes at commit. `executemany` fills it with this month's rows. `%(job_id)s`-style placeholders take their values from each row dictionary by name.
2. **One upsert from staging.** `insert into jobs.postings ... select ... from stage on conflict (job_id) do update set ...`:
    - New jobs are inserted with `first_seen_at` and `last_seen_at` set to `seen_on`, and `times_seen` = 1.
    - For known jobs, each `REFRESH` column becomes `coalesce(excluded.c, p.c)`: the new value, unless the new scrape left it empty, in which case the old one is kept. `coalesce` returns its first non-null argument.
    - `search_terms` merges old and new lists: `unnest` turns both into rows, `array_agg(distinct t order by t)` turns them back into one sorted list without duplicates.
    - `times_seen` goes up by 1, but only if this is a different run than the last one that saw the job. Re-running the same load doesn't count twice.
    - `returning (xmax = 0)` gives one true/false per row; summing the trues gives the number of new jobs.

**Why staging instead of upserting row by row:** one statement over a staged table is one round trip to Supabase instead of thousands, and the whole month is handled by a single, readable piece of SQL.

**`retag_all(conn, tagger)`** re-applies `themes.yaml` to every stored description. After you improve the themes, history is re-tagged for free, which is another benefit of storing `description_text`.

### 5.5 Load your sample

Create a scratch script, `samples/try_load.py`. It lives in the git-ignored `samples` folder because it's for practice only:

```python
import json
from datetime import date

from core import db
from core.text import ThemeTagger
from projects.linkedin_jobs import load
from projects.linkedin_jobs.transform import merge_items, to_row

items = json.load(open("samples/raw_sample.json", encoding="utf-8"))
tagger = ThemeTagger.from_yaml("projects/linkedin_jobs/themes.yaml")
merged = merge_items({"data scientist": items})
rows = [to_row(item, terms, tagger) for item, terms in merged.values()]

with db.connect() as conn:
    run_id = conn.execute(
        "insert into core.run_log (project) values ('manual-test') returning run_id"
    ).fetchone()[0]
    load.insert_raw(conn, run_id, merged)
    new = load.upsert_postings(conn, run_id, rows, date.today())
    conn.commit()

print(f"Run {run_id}: {len(rows)} jobs, {new} new")
```

**Run it twice:**

```bash
uv run python -m samples.try_load
uv run python -m samples.try_load
```

**Checkpoint:** the first run prints `5 jobs, 5 new`; the second prints `5 jobs, 0 new`. In the SQL Editor:

```sql
select job_id, title, first_seen_at, last_seen_at, times_seen from jobs.postings;
```

Every job shows `times_seen` = 2, and `jobs.raw_postings` has 10 rows: two sightings of 5 jobs.

Before Module 6, clear out the practice data so your real history starts clean:

```sql
truncate jobs.raw_postings, jobs.postings, core.run_log restart identity;
```

`truncate` empties tables instantly, and `restart identity` resets `run_id` to start from 1 again. Listing all three tables together is required, because they reference one another.

**Commit:**

```bash
git add .
git commit -m "Module 5: deduplicating loader"
git push
```

### Check your understanding

1. In `on conflict ... do update`, what's the difference between `p.title` and `excluded.title`?
2. Why does `times_seen` check `p.last_run_id = excluded.last_run_id`?
3. What happens to this month's raw rows if the upsert fails halfway?
4. Why `%s` placeholders instead of f-strings for values?

<details>
<summary>Answers</summary>

1. `p.title` is the value already stored; `excluded.title` is the value from the row being inserted.
2. So re-running the same run's load (after a crash, say) doesn't count the job as seen twice.
3. They're rolled back too. The raw insert and the upsert are in one transaction, and nothing is committed until both succeed.
4. Safety and correctness. psycopg sends values separately from the SQL, so quotes or SQL fragments inside a job description can't break or alter the statement.

</details>

---

## Module 6: The pipeline script

By the end of this module, one command runs the whole month: scrape every search, transform, load, and record the run. You'll do your first real run, capped small. Allow about 45 minutes.

### 6.1 The run log: `core/runlog.py`

Create `core/runlog.py`:

```python
"""Run log: one row in core.run_log per pipeline run, across all projects."""

import json

import psycopg


def start_run(conn: psycopg.Connection, project: str, params: dict) -> int:
    run_id = conn.execute(
        "insert into core.run_log (project, params) values (%s, %s) returning run_id",
        (project, json.dumps(params)),
    ).fetchone()[0]
    conn.commit()
    return run_id


def finish_run(
    conn: psycopg.Connection,
    run_id: int,
    *,
    status: str,
    rows_fetched: int | None = None,
    rows_new: int | None = None,
    cost_usd: float | None = None,
    error: str | None = None,
) -> None:
    conn.rollback()  # clear any failed transaction before logging the outcome
    conn.execute(
        """
        update core.run_log
           set finished_at = now(), status = %s, rows_fetched = %s,
               rows_new = %s, cost_usd = %s, error = %s
         where run_id = %s
        """,
        (status, rows_fetched, rows_new, cost_usd, (error or None) and error[:4000], run_id),
    )
    conn.commit()
```

- `start_run` inserts a row with status `running` and returns its new `run_id`. It commits immediately, so the run is recorded even if everything after it crashes. A run stuck at `running` in the log tells you exactly that.
- `json.dumps(params)` stores the run's settings (searches, limits) as JSON, so you can later see what each run was asked to do.
- `finish_run` records the outcome. The `*` in its signature makes every argument after it **keyword-only**: you must write `status="failed"`, not just `"failed"`, which keeps calls readable.
- `conn.rollback()` first clears any failed transaction. Postgres refuses new statements in a transaction that has already hit an error, so without this line the failure itself couldn't be logged.
- `error[:4000]` caps the message length. `(error or None) and error[:4000]` reads: "if there's an error message, its first 4,000 characters; otherwise `None`".

### 6.2 The pipeline: `run.py`

Create `projects/linkedin_jobs/run.py`:

```python
"""Monthly LinkedIn jobs pipeline: scrape, land raw, upsert clean rows, log the run.

Usage:
    uv run python -m projects.linkedin_jobs.run                      # full run from config.yaml
    uv run python -m projects.linkedin_jobs.run --limit 25           # small, cheap run
    uv run python -m projects.linkedin_jobs.run --searches "data scientist" --limit 25
    uv run python -m projects.linkedin_jobs.run --retag              # re-apply themes.yaml
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
PROJECT = "linkedin_jobs"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Monthly LinkedIn jobs pipeline")
    ap.add_argument("--limit", type=int, help="max jobs per search (overrides config.yaml)")
    ap.add_argument("--searches", help="comma-separated search terms (overrides config.yaml)")
    ap.add_argument("--retag", action="store_true", help="re-tag stored postings with themes.yaml, then stop")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = yaml.safe_load((HERE / "config.yaml").read_text())
    tagger = ThemeTagger.from_yaml(HERE / "themes.yaml")

    if args.retag:
        with db.connect() as conn:
            print(f"Re-tagged {load.retag_all(conn, tagger)} postings.")
        return 0

    searches = [s.strip() for s in args.searches.split(",")] if args.searches else cfg["searches"]
    limit = args.limit or cfg["limit_per_search"]
    params = {"searches": searches, "limit_per_search": limit,
              "location": cfg["location"], "date_posted": cfg["date_posted"]}

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
```

**`parse_args`** defines the command-line options with `argparse`:

- `--limit 25` overrides the per-search limit; `type=int` converts the text `"25"` into a number.
- `--searches "data scientist,data analyst"` overrides the search list.
- `--retag` is a flag: present means `True`, absent means `False` (`action="store_true"`).
- `--help` comes for free. Try `uv run python -m projects.linkedin_jobs.run --help`.

**`main(argv)`** runs the month in four commented steps. Things to notice:

- `argv` defaults to `None`, which tells argparse to read the real command line. Tests can pass a list instead, such as `["--limit", "5"]`, which Module 7 uses.
- **A failed search doesn't stop the others.** The inner `try/except` around each search records the error and moves on. Losing the data scientist results because the analytics engineer search failed would be a bad trade.
- **Any other failure is logged, then re-raised.** The outer `except` records the run as `failed` with the error message, then `raise` lets the error continue so the program exits with an error and GitHub marks the run red (Module 8).
- **Status has three outcomes:** `succeeded`, `succeeded_with_errors` (some searches failed) and `failed` (all searches failed).
- **The return value is the exit code.** `sys.exit(main())` hands it to the operating system: 0 means success and anything else means failure. GitHub Actions reads exactly this.
- `flush=True` on `print` makes each line appear immediately in GitHub's live log instead of in one block at the end.

### 6.3 Your first real run

Five searches × 25 jobs = up to 125 jobs, about $0.25 on Apify's free plan.

**Run in the terminal:**

```bash
uv run python -m projects.linkedin_jobs.run --limit 25
```

**Checkpoint:** five `Scraping ...` lines, each followed by a job count, then a summary like

```text
Run 1: 118 jobs, 118 new, $0.25. Status: succeeded
```

The total is usually a little under 125, because some jobs match two searches and are kept once.

Now look at what you have, in the SQL Editor:

```sql
-- The run log
select run_id, status, rows_fetched, rows_new, cost_usd, error from core.run_log;

-- Jobs found by more than one search
select title, company_name, search_terms from jobs.postings where cardinality(search_terms) > 1;

-- The most common themes so far
select theme, count(*) from jobs.posting_themes group by theme order by count(*) desc;
```

Optional: run the same command again tomorrow and check that most jobs come back as already known, with `times_seen` = 2.

**Commit:**

```bash
git add .
git commit -m "Module 6: pipeline script with run log"
git push
```

### Check your understanding

1. Why does `start_run` commit straight away instead of waiting for the end?
2. The analytics engineer search fails, but the other four work. What does the run log show, and what's in `jobs.postings`?
3. Why does `main` re-raise the exception after logging it?
4. What would happen on GitHub if `main` always returned 0?

<details>
<summary>Answers</summary>

1. So the attempt is recorded even if the program crashes before reaching `finish_run`.
2. Status `succeeded_with_errors`, with the failed search in `error`. The other four searches' jobs are loaded normally.
3. Logging records the failure for you; re-raising makes the program exit with an error, so automation notices.
4. Every run would show green, even complete failures, and you'd only find out by reading the run log.

</details>

---

## Module 7: Tests

By the end of this module, one command checks the transform, the deduplication and the whole pipeline, without spending a cent or touching your real database. Allow about an hour.

### 7.1 Why bother

Right now you know the pipeline works because you ran it and looked. In three months you'll change `themes.yaml`, or the salary parsing, or uv will upgrade a package, and you won't remember everything to look at. Tests are the looking, written down so a machine can repeat it in seconds.

**pytest** runs every function whose name starts with `test_` in files whose names start with `test_`. Inside, `assert <something true>` passes silently, and a false assert fails with a report showing both sides.

### 7.2 Test data: `tests/fixtures/sample_items.json`

A **fixture** is data made up for testing. Real scraper output changes every month; tests need data that never changes, designed to hit the tricky cases on purpose. Create `tests/fixtures/sample_items.json`:

```json
[
  {"id": "4100000001", "link": "https://www.linkedin.com/jobs/view/4100000001", "title": "Senior Data Scientist",
   "companyName": "Example Health", "companyLinkedinUrl": "https://www.linkedin.com/company/example-health",
   "location": "Columbus, OH", "salaryInfo": ["$130,000.00/yr", "$160,000.00/yr"], "postedAt": "2026-09-28",
   "applicantsCount": "87", "descriptionText": "Build predictive models and run A/B testing. Strong SQL and Python. Communicate findings to stakeholders. Experience with LLMs a plus.",
   "jobPosterName": "Jane Recruiter", "jobPosterProfileUrl": "https://www.linkedin.com/in/someone",
   "seniorityLevel": "Mid-Senior level", "employmentType": "Full-time", "jobFunction": "Engineering and Information Technology",
   "industries": "Hospitals and Health Care", "companyEmployeesCount": 5400},
  {"id": "4100000002", "link": "https://www.linkedin.com/jobs/view/4100000002", "title": "Data Analyst",
   "companyName": "Example Staffing", "location": "Remote", "salaryInfo": ["$45.00/hr", "$55.00/hr"], "postedAt": "2026-10-02",
   "applicantsCount": "Over 200 applicants", "descriptionText": "Tableau dashboards and SQL reporting. Forecasting a plus.",
   "seniorityLevel": "Associate", "employmentType": "Contract", "jobFunction": "Information Technology",
   "industries": "Staffing and Recruiting", "workRemoteAllowed": true},
  {"id": "4100000003", "link": "https://www.linkedin.com/jobs/view/4100000003", "title": "Data Analyst",
   "companyName": "Example Staffing", "location": "Remote", "postedAt": "2026-10-09",
   "descriptionText": "Tableau dashboards and SQL reporting. Forecasting a plus.",
   "seniorityLevel": "Associate", "employmentType": "Contract", "industries": "Staffing and Recruiting"}
]
```

Each of the three jobs is there for a reason:

- Job 1 has a yearly salary, recruiter fields that must be stripped, and a description written to trigger five themes.
- Job 2 has an hourly salary, `"Over 200 applicants"` as text, and remote work given only as `workRemoteAllowed`.
- Job 3 is a repost of job 2: a new ID, but the same company, title, location and description.

### 7.3 The tests: `tests/test_linkedin_jobs.py`

Create `tests/test_linkedin_jobs.py`:

```python
"""Tests for the LinkedIn jobs pipeline.

Transform tests always run. Database tests run when TEST_DB_URL points at a
throwaway Postgres (never your Supabase project):
    TEST_DB_URL=postgresql://... uv run pytest
"""

import json
import os
from datetime import date
from pathlib import Path

import pytest

from core.text import ThemeTagger
from projects.linkedin_jobs.transform import merge_items, parse_salary, to_row

ROOT = Path(__file__).resolve().parent.parent
ITEMS = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text())
TAGGER = ThemeTagger.from_yaml(ROOT / "projects/linkedin_jobs/themes.yaml")


def rows_for(items, term="data scientist"):
    merged = merge_items({term: items})
    return merged, [to_row(i, t, TAGGER) for i, t in merged.values()]


def test_salary_parsing():
    assert parse_salary(["$130,000.00/yr", "$160,000.00/yr"]) == (130000.0, 160000.0, "yr")
    assert parse_salary(["$45.00/hr", "$55.00/hr"]) == (45.0, 55.0, "hr")
    assert parse_salary(["$120K", "$150K"]) == (120000.0, 150000.0, "yr")
    assert parse_salary(None) == (None, None, None)


def test_transform_fields_and_privacy():
    merged, rows = rows_for(ITEMS)
    r = {x["job_id"]: x for x in rows}
    a = r["4100000001"]
    assert a["primary_industry"] == "Hospitals and Health Care"
    assert a["applicants_count"] == 87 and a["company_employees"] == 5400
    assert a["posted_at"] == date(2026, 9, 28)
    assert {"Machine learning modeling", "Experimentation & causal inference", "SQL & data pipelines",
            "Stakeholder communication", "Generative AI & LLMs"} <= set(a["themes"])
    assert r["4100000002"]["workplace_type"] == "Remote"
    assert r["4100000002"]["applicants_count"] == 200
    for item, _ in merged.values():
        assert not any(k.startswith("jobPoster") for k in item)


def test_repost_shares_content_hash():
    _, rows = rows_for(ITEMS)
    r = {x["job_id"]: x for x in rows}
    assert r["4100000002"]["content_hash"] == r["4100000003"]["content_hash"]
    assert r["4100000001"]["content_hash"] != r["4100000002"]["content_hash"]


def test_merge_across_searches():
    merged = merge_items({"data scientist": ITEMS[:1], "machine learning engineer": ITEMS[:2]})
    assert len(merged) == 2
    assert sorted(merged["4100000001"][1]) == ["data scientist", "machine learning engineer"]


DB = os.environ.get("TEST_DB_URL")


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_monthly_runs_dedupe():
    import psycopg

    from core import db, runlog
    from projects.linkedin_jobs import load

    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.commit()
        db.migrate(conn)

        # Month 1: jobs 1 and 2
        run1 = runlog.start_run(conn, "linkedin_jobs", {})
        merged, rows = rows_for(ITEMS[:2])
        load.insert_raw(conn, run1, merged)
        assert load.upsert_postings(conn, run1, rows, date(2026, 10, 1)) == 2
        conn.commit()
        runlog.finish_run(conn, run1, status="succeeded", rows_fetched=2, rows_new=2)

        # Month 2: job 2 again (from two searches) plus job 3 (a repost of job 2)
        run2 = runlog.start_run(conn, "linkedin_jobs", {})
        merged = merge_items({"data analyst": ITEMS[1:3], "data scientist": ITEMS[1:2]})
        rows = [to_row(i, t, TAGGER) for i, t in merged.values()]
        load.insert_raw(conn, run2, merged)
        assert load.upsert_postings(conn, run2, rows, date(2026, 11, 1)) == 1  # only job 3 is new
        conn.commit()

        j2 = conn.execute(
            "select first_seen_at, last_seen_at, times_seen, search_terms from jobs.postings where job_id='4100000002'"
        ).fetchone()
        assert j2 == (date(2026, 10, 1), date(2026, 11, 1), 2, ["data analyst", "data scientist"])

        assert conn.execute("select count(*) from jobs.postings").fetchone()[0] == 3
        dedup = conn.execute(
            "select count(*), max(repost_count) from jobs.postings_dedup"
        ).fetchone()
        assert dedup == (2, 2)  # job 3 collapses into job 2
        assert conn.execute("select count(*) from jobs.raw_postings").fetchone()[0] == 4
        assert conn.execute("select count(*) from jobs.posting_themes").fetchone()[0] > 0

        # Analysis views (Module 9) read the same data
        conn.execute("insert into jobs.my_skills (theme, my_level) values ('Dashboards & BI', 5)")
        gap = dict(conn.execute("select theme, priority from jobs.skill_gap").fetchall())
        assert gap["Dashboards & BI"] == 0  # you're an expert: no gap
        assert conn.execute("select sum(roles) from jobs.industry_mix").fetchone()[0] == 2

        # Re-running the same month's load is harmless
        assert load.upsert_postings(conn, run2, rows, date(2026, 11, 1)) == 0
        conn.commit()
        assert conn.execute("select times_seen from jobs.postings where job_id='4100000002'").fetchone()[0] == 2


class FakeRun:
    """Stands in for the object apify-client returns from .call()."""
    status = "SUCCEEDED"
    default_dataset_id = "fake-dataset"
    usage_total_usd = 0.01


class FakeApify:
    """A pretend Apify client: same methods the pipeline calls, no network."""
    def actor(self, actor_id):
        return self

    def call(self, run_input):
        self.last_input = run_input
        return FakeRun()

    def dataset(self, dataset_id):
        return self

    def iterate_items(self):
        return iter(ITEMS)


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_pipeline_end_to_end(monkeypatch):
    import psycopg

    from core import db
    from projects.linkedin_jobs import run, scrape

    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    monkeypatch.setattr(scrape, "client", lambda: FakeApify())
    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.commit()
        db.migrate(conn)

    assert run.main(["--limit", "5", "--searches", "data scientist,data analyst"]) == 0

    with psycopg.connect(DB) as conn:
        status, fetched, new = conn.execute(
            "select status, rows_fetched, rows_new from core.run_log order by run_id desc limit 1"
        ).fetchone()
    assert (status, fetched, new) == ("succeeded", 3, 3)
```

The file has three kinds of test.

**Unit tests** check one function each, with no network or database:

- `test_salary_parsing` covers yearly, hourly, `K`-suffixed and missing salaries.
- `test_transform_fields_and_privacy` checks the conversions from 3.1 and that no `jobPoster` field survives.
- `test_repost_shares_content_hash` checks that jobs 2 and 3 share a fingerprint and job 1 doesn't.
- `test_merge_across_searches` checks that a job found by two searches is kept once, with both terms.
- `rows_for(...)` at the top is a helper the tests share. It doesn't start with `test_`, so pytest doesn't run it on its own.

**A database test**, `test_monthly_runs_dedupe`, plays out two months against a real Postgres:

- Month 1 loads jobs 1 and 2. Month 2 loads job 2 again (from two searches) plus job 3, the repost.
- It then checks every promise from Module 5: only job 3 is new; job 2 keeps its first date, gets a new last date, `times_seen` = 2 and both search terms; `postings_dedup` collapses the repost; re-running month 2 changes nothing.
- It also checks the Module 9 analysis views. Write that file before running the database tests (see 7.4).

**An end-to-end test**, `test_pipeline_end_to_end`, runs `run.main` itself with a **fake** Apify:

- `FakeRun` and `FakeApify` are tiny classes with exactly the attributes and methods the pipeline uses: `.actor().call()` returns a run whose status is `SUCCEEDED`, and `.dataset().iterate_items()` returns the fixture jobs.
- `monkeypatch` is a built-in pytest helper that swaps things out during one test and restores them afterwards. `monkeypatch.setattr(scrape, "client", lambda: FakeApify())` makes `scrape.client()` return the fake. `lambda: FakeApify()` is a one-line function with no name.
- Then `run.main(["--limit", "5", ...])` runs the real pipeline code, and the test checks the run log row.

**`@pytest.mark.skipif(not DB, ...)`** skips the two database tests unless `TEST_DB_URL` is set. Each of them starts by **dropping** the `jobs` and `core` schemas to begin from scratch.

> **Never set `TEST_DB_URL` to your Supabase connection string.** The database tests delete everything in `jobs` and `core`. They're meant for a throwaway database only.

### 7.4 Run them

**Run in the terminal:**

```bash
uv run pytest -v
```

**Checkpoint:** `4 passed, 2 skipped`. `-v` lists each test by name; the two skipped are the database tests.

The database tests will run automatically on GitHub in Module 8, against a throwaway Postgres that exists only for the length of the test run. That's the easiest way to run them, and you don't need anything installed locally.

They also need `sql/020_analysis.sql` from Module 9, so they'll fail on GitHub until you've written it. If you'd rather keep everything green, create that file now (its contents are in 9.1) and come back to the explanation later.

Optional, if you have Docker installed: run them locally against a temporary database.

```bash
docker run --name pg-test -e POSTGRES_PASSWORD=postgres -p 5433:5432 -d postgres:16
```

Then, Windows (PowerShell):

```powershell
$env:TEST_DB_URL="postgresql://postgres:postgres@localhost:5433/postgres"; uv run pytest -v
```

Mac:

```bash
TEST_DB_URL=postgresql://postgres:postgres@localhost:5433/postgres uv run pytest -v
```

That gives `6 passed`. Remove the container afterwards with `docker rm -f pg-test`.

**Try this:** break something on purpose. In `transform.py`, add `return None` as the first line inside `_int`, run `uv run pytest`, and read the failure report: `test_transform_fields_and_privacy` fails, showing `None == 87`. Then undo the change. Knowing what a failure looks like makes real ones less alarming.

**Commit:**

```bash
git add .
git commit -m "Module 7: tests"
git push
```

### Check your understanding

1. Why test with made-up jobs instead of last month's real scrape?
2. What does the fake Apify let you test, and what can't it test?
3. Why must the database tests never point at Supabase?

<details>
<summary>Answers</summary>

1. Real data changes every month, so the expected answers would too. A fixture is fixed, and it's designed to contain the tricky cases on purpose.
2. It tests everything in your code: merging, transforming, loading, logging, status and exit code. It can't test whether Apify itself still works or still returns the same field names. That's what the small monthly-run checks and the run log are for.
3. They drop and recreate the `jobs` and `core` schemas, which would erase your real history.

</details>

---

## Module 8: Automation with GitHub Actions

By the end of this module, GitHub runs the pipeline on the 1st of every month, keeps the database awake weekly, runs your tests on every push, and applies database changes when you change a `.sql` file. Allow about an hour.

### 8.1 GitHub Actions in five ideas

1. A **workflow** is a YAML file in `.github/workflows/`. GitHub finds and runs these files automatically.
2. **`on:`** says when it runs: on a `schedule`, on a `push`, or manually (`workflow_dispatch`, which adds a **Run workflow** button).
3. A **job** runs on a fresh, empty Linux machine (a **runner**) that GitHub creates for the run and throws away afterwards.
4. **Steps** run in order on that machine: check out your code, install uv, install packages, run your command.
5. **Secrets** are encrypted values you store in the repo's settings. A workflow reads them as `${{ secrets.NAME }}`, and GitHub hides them in logs.

The schedule uses **cron** syntax: five fields, always in UTC.

| Field | minute | hour | day of month | month | day of week |
| --- | --- | --- | --- | --- | --- |
| `17 11 1 * *` | 17 | 11 | 1 | any | any |

So `17 11 1 * *` means 11:17 UTC on the 1st of every month: 7:17am Eastern in summer, 6:17am in winter. The odd minute avoids the top of the hour, when GitHub's scheduler is busiest and runs start late.

### 8.2 Add the secrets

In your repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Add two:

| Name | Value |
| --- | --- |
| `APIFY_TOKEN` | The same value as in your `.env` |
| `SUPABASE_DB_URL` | The same Session pooler string as in your `.env` |

Names must match exactly; they're what the workflows ask for.

### 8.3 The four workflows

**`.github/workflows/setup-database.yml`** applies your SQL files:

```yaml
name: Set up database

on:
  workflow_dispatch:          # the "Run workflow" button
  push:
    branches: [main]
    paths: ["sql/**"]         # also run whenever a .sql file changes on main

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --locked
      - name: Apply sql/*.sql
        env:
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: uv run python -m core.db
```

- `actions/checkout@v4` copies your repository onto the runner. `@v4` pins the version of that action, as `uv.lock` pins your packages.
- `astral-sh/setup-uv@v6` installs uv. `enable-cache: true` keeps downloaded packages between runs, so later runs install in seconds.
- `uv sync --locked` installs exactly what `uv.lock` says, and fails if `uv.lock` is out of date with `pyproject.toml`. That failure is useful: it means you added a package and forgot to commit the lock file.
- `env:` hands the secret to the command as an environment variable, which `core/settings.py` reads. The code doesn't change between your laptop and GitHub.
- The `push` trigger with `paths: ["sql/**"]` re-runs migrations whenever a `.sql` file changes on `main`. Because your SQL is idempotent, that's always safe.

**`.github/workflows/linkedin-jobs.yml`** is the monthly run:

```yaml
name: LinkedIn jobs (monthly)

on:
  schedule:
    - cron: "17 11 1 * *"     # 1st of each month, 11:17 UTC (7:17am Eastern in summer)
  workflow_dispatch:
    inputs:
      limit:
        description: "Max jobs per search (blank = config.yaml)"
        required: false
      searches:
        description: "Comma-separated search terms (blank = config.yaml)"
        required: false

jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 240
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --locked --no-dev
      - name: Scrape and load
        env:
          APIFY_TOKEN: ${{ secrets.APIFY_TOKEN }}
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
          LIMIT: ${{ inputs.limit }}
          SEARCHES: ${{ inputs.searches }}
        run: |
          ARGS=()
          if [ -n "$LIMIT" ]; then ARGS+=(--limit "$LIMIT"); fi
          if [ -n "$SEARCHES" ]; then ARGS+=(--searches "$SEARCHES"); fi
          uv run --no-dev python -m projects.linkedin_jobs.run "${ARGS[@]}"
```

- `inputs` adds two optional boxes to the **Run workflow** button, so you can do a small manual run without editing any file.
- `timeout-minutes: 240` stops a stuck run after 4 hours instead of GitHub's default of 6.
- `--no-dev` skips pytest; the pipeline doesn't need it.
- The `run: |` block is a small bash script. `ARGS=()` starts an empty list; each `if` adds `--limit` or `--searches` only when you filled in that box. `"${ARGS[@]}"` passes the list on with each value kept whole, so a search term with spaces stays one value.

**`.github/workflows/keep-alive.yml`** pings the database every Monday:

```yaml
name: Keep database awake

on:
  schedule:
    - cron: "43 13 * * 1"     # Mondays 13:43 UTC
  workflow_dispatch:

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --locked --no-dev
      - name: Ping
        env:
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: uv run --no-dev python -m core.db ping
```

Supabase pauses free projects after a week without activity, and a monthly pipeline would find it paused almost every time. A weekly ping keeps it awake.

**`.github/workflows/tests.yml`** runs your tests on every push:

```yaml
name: Tests

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:                       # a throwaway database, just for this job
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 5s --health-timeout 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --locked
      - name: Run tests
        env:
          TEST_DB_URL: postgresql://postgres:postgres@localhost:5432/postgres
        run: uv run pytest -v
```

- `services: postgres:` starts a throwaway Postgres database alongside the job, from the official `postgres:16` image. It exists only for this run.
- `options: --health-cmd pg_isready ...` makes GitHub wait until the database accepts connections before starting the steps.
- `TEST_DB_URL` points at that throwaway database, so all 6 tests run here, including the two that were skipped on your laptop.

### 8.4 Push and watch

```bash
git add .
git commit -m "Module 8: GitHub Actions workflows"
git push
```

Then, on GitHub, open the **Actions** tab:

1. **Tests** starts by itself, triggered by the push. **Checkpoint:** a green tick, with `6 passed` in its log. (Red because `020_analysis.sql` doesn't exist yet? See 7.4.)
2. Click **Set up database** → **Run workflow**. **Checkpoint:** green, with the `Applied ...` lines in its log.
3. Click **LinkedIn jobs (monthly)** → **Run workflow**, type `25` in the limit box, and run it. Click into the run to watch the log live. **Checkpoint:** green, ending with the `Run N: ...` summary line, and a new row in `core.run_log`.
4. Click **Keep database awake** → **Run workflow**. **Checkpoint:** green.

From now on, the monthly and weekly runs happen on their own.

### 8.5 Before the first full monthly run

The full config scrapes 5 searches × 1,000 jobs: up to 5,000 results. On Apify's free plan that costs up to $10, but the free plan's credit is $5 a month, and runs stop when it's used up. Choose one:

| Option | Monthly cost | Covers |
| --- | --- | --- |
| Set `limit_per_search: 500` in `config.yaml` | $0 | Up to 2,500 jobs a month on the free credit |
| Upgrade Apify to Starter | $19 | Up to about 19,000 jobs a month at $1 per 1,000 |

Check `cost_usd` in `core.run_log` after the first full run; it's the real number.

Things to know about scheduled workflows:

- If a scheduled run fails, GitHub emails the person who last changed the workflow's `cron` line, which is you.
- GitHub turns off schedules in **public** repositories after 60 days without any commits. Keep the repository private and this doesn't apply.
- Private repositories get a monthly allowance of free Actions minutes (2,000 on the free plan when this was written). A full monthly run takes well under an hour, so you'll use a small fraction of it.

### Check your understanding

1. Where does `SUPABASE_DB_URL` come from on your laptop, and where on GitHub? What changes in the code between the two?
2. You `uv add` a new package but forget to commit `uv.lock`. What happens on GitHub?
3. Why does the Tests workflow get its own Postgres instead of using Supabase?

<details>
<summary>Answers</summary>

1. `.env` on your laptop, repository secrets on GitHub. Nothing changes in the code: both arrive as environment variables.
2. `uv sync --locked` fails, because `pyproject.toml` lists a package that `uv.lock` doesn't. Commit the lock file and push again.
3. The database tests wipe the `jobs` and `core` schemas. A throwaway database per run makes that safe, and keeps test runs from mixing with real data.

</details>

---

## Module 9: Analysis

By the end of this module, you can answer the question this project started with: what the market asks of data scientists, and where you're furthest from it. Allow about an hour, plus time to read your results.

### 9.1 The analysis layer: `sql/020_analysis.sql`

Create `sql/020_analysis.sql`:

```sql
-- Analysis layer: views the dashboard and your own queries read from.
-- "Recent" means the role was still visible within the last 90 days.

-- Your own rating of each theme: 0 = none, 5 = expert. Fill it in yourself.
create table if not exists jobs.my_skills (
    theme    text primary key,
    my_level smallint check (my_level between 0 and 5),
    notes    text
);

-- New roles per month (reposts counted once).
create or replace view jobs.monthly_summary as
select date_trunc('month', role_first_seen_at)::date as month,
       count(*)                                        as new_roles,
       count(distinct company_name)                    as companies,
       round(avg(case when workplace_type ilike '%remote%' then 1.0 else 0 end), 3) as remote_share
from jobs.postings_dedup
group by 1
order by 1;

-- Which industries are hiring, recent roles only.
create or replace view jobs.industry_mix as
select coalesce(primary_industry, '(unknown)') as industry,
       count(*)                                as roles,
       round(count(*)::numeric / sum(count(*)) over (), 3) as share
from jobs.postings_dedup
where role_last_seen_at >= current_date - 90
group by 1
order by roles desc;

-- How often each theme appears in recent job descriptions.
create or replace view jobs.theme_coverage as
with recent as (
    select * from jobs.postings_dedup where role_last_seen_at >= current_date - 90
)
select t.theme,
       count(*)                                                   as roles,
       round(count(*)::numeric / (select count(*) from recent), 3) as share
from recent
cross join lateral unnest(recent.themes) as t(theme)
group by t.theme
order by roles desc;

-- The gap: themes the market asks for most, weighted by how far you are from expert.
create or replace view jobs.skill_gap as
select c.theme,
       c.share                                         as market_share,
       s.my_level,
       round(c.share * (5 - coalesce(s.my_level, 0)), 3) as priority
from jobs.theme_coverage c
left join jobs.my_skills s using (theme)
order by priority desc;
```

- **`jobs.my_skills`** is the only table you fill by hand: your own rating of each theme, from 0 (none) to 5 (expert). `check (my_level between 0 and 5)` makes the database reject anything outside that range.
- **`jobs.monthly_summary`** counts new roles per month. `date_trunc('month', ...)` rounds a date down to the 1st of its month, so grouping by it groups by month. The remote share is the average of 1 for remote roles and 0 for the rest.
- **`jobs.industry_mix`** counts recent roles per industry. "Recent" means seen within the last 90 days, so the views describe the current market rather than all history. `sum(count(*)) over ()` is a window function across all rows: the total, used to compute each industry's share.
- **`jobs.theme_coverage`** gives the share of recent roles mentioning each theme. `with recent as (...)` names a sub-query (a **CTE**) so it can be used twice: once for counting themes, once for the total.
- **`jobs.skill_gap`** is the payoff. For each theme: how often the market asks for it, your level, and a **priority** = market share × (5 − your level). A theme in 60% of postings where you rate yourself 2 scores 0.6 × 3 = 1.8; one in 20% where you're a 5 scores 0. `left join` keeps themes you haven't rated, treating them as 0.

Commit and push. The **Set up database** workflow runs by itself, because a `.sql` file changed, and the Tests workflow now passes all 6 tests.

```bash
git add .
git commit -m "Module 9: analysis views"
git push
```

### 9.2 Rate yourself

In Supabase's SQL Editor, fill in your own levels. Be honest; nobody sees this table but you. Theme names must match `themes.yaml` exactly:

```sql
insert into jobs.my_skills (theme, my_level) values
    ('Machine learning modeling',          3),
    ('Generative AI & LLMs',               2),
    ('Experimentation & causal inference', 3),
    ('SQL & data pipelines',               5),
    ('Statistical rigor',                  4),
    ('Cloud & MLOps',                      2),
    ('Stakeholder communication',          4),
    ('Dashboards & BI',                    5),
    ('Forecasting & time series',          3),
    ('Product analytics',                  2)
on conflict (theme) do update set my_level = excluded.my_level;
```

The numbers above are placeholders; replace every one. The `on conflict` line means you can re-run the statement with new numbers whenever your skills change, which is the upsert from Module 5 again.

### 9.3 Ask the questions

Run these in the SQL Editor:

```sql
-- Where am I furthest from what the market asks for?
select * from jobs.skill_gap;

-- Which industries are hiring?
select * from jobs.industry_mix;

-- Which themes appear most?
select * from jobs.theme_coverage;

-- How is the market moving month to month? (Useful after a few months.)
select * from jobs.monthly_summary;

-- Do senior roles ask for different things than junior ones?
select seniority_level, theme, count(*) as roles
from jobs.posting_themes
group by seniority_level, theme
order by seniority_level, roles desc;
```

One more, with a survival-analysis angle. Roles not seen in the latest run have probably been filled or withdrawn, so `role_last_seen_at - role_first_seen_at` approximates how long they stayed visible:

```sql
select primary_industry,
       count(*)                                                 as roles_closed,
       round(avg(role_last_seen_at - role_first_seen_at), 1)    as avg_days_visible
from jobs.postings_dedup
where role_last_seen_at < (select max(last_seen_at) from jobs.postings)
group by primary_industry
order by roles_closed desc;
```

Two caveats, both familiar from survival analysis. With monthly runs, the dates are only accurate to about a month. And roles still open are **right-censored**: excluding them, as this query does, biases the average downward. A proper Kaplan–Meier fit on this table would handle them correctly, and would make a good blog post once you have a few months of data.

### 9.4 Connect Power BI (optional)

The views are ordinary tables to any BI tool. It's good practice to give the tool its own login that can only read. In the SQL Editor:

```sql
create role bi_reader with login password 'choose-a-long-password-here';
grant usage on schema jobs to bi_reader;
grant select on all tables in schema jobs to bi_reader;
alter default privileges in schema jobs grant select on tables to bi_reader;
```

The last line makes tables and views created later readable too. Then in Power BI Desktop:

1. **Get Data → PostgreSQL database**.
2. **Server**: the host and port from your Session pooler string, e.g. `aws-0-us-east-1.pooler.supabase.com:5432`. **Database**: `postgres`. Choose **Import**.
3. When asked for credentials, choose **Database**. The user name follows the pooler's format, `bi_reader.<project-ref>`, where `<project-ref>` is the part after `postgres.` in your own connection string's user name.
4. Select the `jobs` views: `skill_gap`, `industry_mix`, `theme_coverage`, `monthly_summary` and `posting_themes`.

If the pooler rejects the `bi_reader` login, use your main `postgres.<project-ref>` user to get started and come back to it. Pooler support for custom roles has changed over time, so check Supabase's current docs.

### Check your understanding

1. Why do the views only look at roles seen in the last 90 days?
2. A theme appears in 80% of postings and you rate yourself 4. Another appears in 30% and you rate yourself 1. Which has the higher priority?
3. Why give Power BI its own read-only login?

<details>
<summary>Answers</summary>

1. To describe the current market. Without a window, roles from a year ago would weigh as much as this month's.
2. The second: 0.3 × 4 = 1.2, against 0.8 × 1 = 0.8.
3. A BI connection only needs to read. A login that can't write or drop anything limits the damage if its password leaks or a query goes wrong.

</details>

---

## Module 10: A second scraper

Your back-burner scraping projects reuse everything in `core/`. Here's the recipe, using `<name>` for the new project.

### 10.1 What you reuse and what you write

| Reused as-is | Written new |
| --- | --- |
| `core/settings.py`: secrets | `projects/<name>/scrape.py`: fetch the data |
| `core/db.py`: connection, migrations, ping | `projects/<name>/transform.py`: raw → clean rows |
| `core/runlog.py`: one run log for every project | `projects/<name>/load.py`: the upsert for its key |
| `core/text.py`: hashing, keyword tagging | `projects/<name>/run.py`: the four steps, copied from LinkedIn's |
| The keep-alive and tests workflows | `sql/0NN_<name>.sql`: its own schema |
| uv, `.env`, GitHub secrets | One new workflow file |

### 10.2 The recipe

1. **Choose the source, in this order of preference.** An official API (the most stable), then an Apify actor someone maintains, then your own scraper with `uv add httpx beautifulsoup4`. Read the site's terms either way.
2. **Find the natural key**, the field that identifies one record forever, like `job_id`. Everything about deduplication depends on it. If there isn't one, build one with `content_hash` from the fields that define a record.
3. **Explore first** (Module 2): fetch a handful of records into `samples/` and read them before writing any transform.
4. **Write `sql/030_<name>.sql`** (Module 4): a `<name>` schema with a raw table keyed on `(run_id, <key>)` and a clean table keyed on `<key>`, with `first_seen_at`, `last_seen_at` and `times_seen`.
5. **Write `transform.py` and `load.py`** (Modules 3 and 5). Copy LinkedIn's `load.py` and change `COLUMNS`, the table names and the conflict key.
6. **Copy `run.py`** (Module 6). Change `PROJECT = "<name>"` and the imports; keep the four steps and the error handling.
7. **Add tests** (Module 7): a small fixture with the tricky cases, plus a two-run deduplication test.
8. **Copy `linkedin-jobs.yml`** (Module 8). Change the name, the schedule and the module path. If it needs a new secret, add it in GitHub and in `REQUIRED` in `settings.py`.

Each new project adds one schema, one folder and one workflow. The run log, the database connection and the habits from this guide carry over unchanged.

---

## Appendix: Command cheat sheet

| Task | Command |
| --- | --- |
| Check secrets | `uv run python -m core.settings` |
| Check both connections | `uv run python -m core.check_connections` |
| Create or update tables | `uv run python -m core.db` |
| Ping the database | `uv run python -m core.db ping` |
| Look at 5 raw jobs | `uv run python -m projects.linkedin_jobs.explore` |
| Small real run | `uv run python -m projects.linkedin_jobs.run --limit 25` |
| One search only | `uv run python -m projects.linkedin_jobs.run --searches "data scientist" --limit 25` |
| Re-tag after editing themes | `uv run python -m projects.linkedin_jobs.run --retag` |
| Run tests | `uv run pytest -v` |
| Add a package | `uv add <package>` (then commit `pyproject.toml` and `uv.lock`) |
| Upgrade all packages | `uv lock --upgrade`, then `uv run pytest`, then commit |

Monthly running cost: $0 with `limit_per_search: 500` on Apify's free plan, or $19 on Apify Starter for the full 5,000. Supabase, GitHub Actions and uv are free at this scale.
