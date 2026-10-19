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
| 9. A second scraper | Your next back-burner project | Reusing the shared core |
| 10. LLM theme tagging (optional) | Themes chosen by Claude instead of keywords | Calling an LLM API, structured outputs, cost control |
| 11. A dashboard | A web app showing demand and your skill gaps | Streamlit, Altair charts, caching, a read-only user, deploying |
| 12. Skills by category (optional) | Technical, communication, business and leadership skills, with statistics | Two-pass LLM extraction, dimension and fact tables, re-tagging |

The finished project looks like this. You'll create every file yourself, in this order:

```text
data-aggregator/
├── core/                         shared code every scraper reuses
│   ├── __init__.py
│   ├── settings.py               Module 1
│   ├── check_connections.py      Module 1
│   ├── text.py                   Module 3
│   ├── db.py                     Module 4
│   ├── runlog.py                 Module 6
│   ├── llm_tagger.py             Module 10 (optional)
│   └── skills.py                 Module 12 (optional)
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
│       ├── run.py                Module 6
│       ├── llm_tag.py            Module 10 (optional)
│       ├── queries.py            Module 11
│       ├── app.py                Module 11
│       ├── skill_discover.py     Module 12 (optional)
│       ├── skills.yaml           Module 12 (optional, you review it)
│       ├── skill_tag.py          Module 12 (optional)
│       ├── skill_queries.py      Module 12 (optional)
│       └── app_skills.py         Module 12 (optional)
├── sql/
│   ├── 001_core.sql              Module 4
│   ├── 010_linkedin_jobs.sql     Module 4
│   ├── 040_skills.sql            Module 12 (optional)
│   └── 900_dashboard_reader.sql  Module 11
├── tests/
│   ├── __init__.py
│   ├── fixtures/sample_items.json   Module 7
│   ├── fixtures/skills.yaml         Module 12 (optional)
│   ├── test_linkedin_jobs.py        Module 7
│   ├── test_llm_tagger.py           Module 10 (optional)
│   ├── test_dashboard.py            Module 11
│   └── test_skills.py               Module 12 (optional)
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

**Why `core/` and `projects/`:** this is the shared-framework split. The database connection, run log and text helpers go in `core/` and are written once. Each scraper gets its own folder under `projects/`. Today there's one scraper, `linkedin_jobs`. Your next scraping project adds a folder there and reuses everything in `core/` (Module 9).

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
cfg = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))

term = cfg["searches"][0]
print(f"Running the scraper for '{term}', 5 jobs...")
items, cost = scrape.run_search(scrape.client(), cfg, term, limit=5)

out = Path("samples") / "raw_sample.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Got {len(items)} jobs for ${cost:.4f}. Saved to {out}")
print("Fields in the first job:", ", ".join(items[0].keys()) if items else "(none)")
```

Line by line, the parts that are new:

1. `from pathlib import Path` imports Python's tool for file paths. `Path(__file__).parent` is the folder this file is in, so the script finds `config.yaml` wherever you run it from.
2. `yaml.safe_load(...read_text(encoding="utf-8"))` reads the file and turns the YAML into a dictionary. Always use `safe_load`, never `load`: it refuses YAML that tries to run code.
3. `term = cfg["searches"][0]` takes the first search term, `data scientist`.
4. `limit=5` overrides the config's 1,000 for this test.
5. `out.parent.mkdir(exist_ok=True)` creates the `samples` folder if it doesn't exist yet. You added `samples/` to `.gitignore` in 1.6, so these files stay on your computer.
6. `json.dumps(items, indent=2, ensure_ascii=False)` turns the list back into JSON text, indented so it's readable. `ensure_ascii=False` keeps characters like `é` as they are instead of escape codes.
7. `${cost:.4f}` formats the cost with four decimals, since it's a fraction of a cent.
8. `encoding="utf-8"` on every `read_text` and `write_text`: **on Windows this is required.** Windows otherwise uses an old character set (cp1252) that can't represent emoji or many symbols found in job descriptions, and the write fails with `UnicodeEncodeError: 'charmap' codec can't encode characters`. Mac and Linux default to UTF-8, so code without it can work there and break on Windows. Make it a habit for every text file you read or write.

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
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

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

The files are numbered `001` and `010` so they sort in the order they must run (the jobs tables refer to `core.run_log`), with gaps for files added later: a second scraper's schema would be `020` (Module 9). Create `sql/010_linkedin_jobs.sql`:

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

-- Views are rebuilt on every migration. Dropping them first (cascade also drops the
-- views built on top of them, which later files recreate) lets the tables above gain
-- new columns without "cannot change name of view column" errors.
drop view if exists jobs.postings_dedup cascade;

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

**`drop view if exists jobs.postings_dedup cascade;`**, just before the views, deletes the views so they can be built fresh on every migration. `cascade` also drops any view built on top of this one (`posting_themes` here), and the statements that follow recreate them. **Why:** `p.*` means "every column of `postings`", and Postgres fixes that list when the view is created. If you later add a column to `postings`, `create or replace view` on its own would fail with `cannot change name of view column`. Rebuilding avoids that, and since views store no data, nothing is lost.

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
        conn.execute(path.read_text(encoding="utf-8"))
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
3. No. `create table if not exists` skips the whole statement because the table exists. Changing an existing table takes a separate statement, `alter table jobs.postings add column if not exists ...`, added to the file after the `create table`. Watch for this whenever you change a table. The views pick up the new column automatically, because they're dropped and rebuilt on every migration. Module 10 does exactly this.
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
    cfg = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
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
ITEMS = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text(encoding="utf-8"))
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

1. **Tests** starts by itself, triggered by the push. **Checkpoint:** a green tick, with `6 passed` in its log.
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

## Module 9: A second scraper

Your back-burner scraping projects reuse everything in `core/`. Here's the recipe, using `<name>` for the new project.

### 9.1 What you reuse and what you write

| Reused as-is | Written new |
| --- | --- |
| `core/settings.py`: secrets | `projects/<name>/scrape.py`: fetch the data |
| `core/db.py`: connection, migrations, ping | `projects/<name>/transform.py`: raw → clean rows |
| `core/runlog.py`: one run log for every project | `projects/<name>/load.py`: the upsert for its key |
| `core/text.py`: hashing, keyword tagging | `projects/<name>/run.py`: the four steps, copied from LinkedIn's |
| The keep-alive and tests workflows | `sql/0NN_<name>.sql`: its own schema |
| uv, `.env`, GitHub secrets | One new workflow file |

### 9.2 The recipe

1. **Choose the source, in this order of preference.** An official API (the most stable), then an Apify actor someone maintains, then your own scraper with `uv add httpx beautifulsoup4`. Read the site's terms either way.
2. **Find the natural key**, the field that identifies one record forever, like `job_id`. Everything about deduplication depends on it. If there isn't one, build one with `content_hash` from the fields that define a record.
3. **Explore first** (Module 2): fetch a handful of records into `samples/` and read them before writing any transform.
4. **Write `sql/020_<name>.sql`** (Module 4): a `<name>` schema with a raw table keyed on `(run_id, <key>)` and a clean table keyed on `<key>`, with `first_seen_at`, `last_seen_at` and `times_seen`.
5. **Write `transform.py` and `load.py`** (Modules 3 and 5). Copy LinkedIn's `load.py` and change `COLUMNS`, the table names and the conflict key.
6. **Copy `run.py`** (Module 6). Change `PROJECT = "<name>"` and the imports; keep the four steps and the error handling.
7. **Add tests** (Module 7): a small fixture with the tricky cases, plus a two-run deduplication test.
8. **Copy `linkedin-jobs.yml`** (Module 8). Change the name, the schedule and the module path. If it needs a new secret, add it in GitHub and in `REQUIRED` in `settings.py`.

Each new project adds one schema, one folder and one workflow. The run log, the database connection and the habits from this guide carry over unchanged.

---

## Module 10 (optional): Theme tagging with an LLM

Keyword tagging (Module 3) is free and transparent, but it can't read meaning: "no deep learning required" still matches `deep learning`, and a theme that's implied rather than named gets missed. This module adds a second tagger that asks Claude to choose themes from your same list. Allow about an hour. At this project's volume it costs about $1 a month (see 10.7).

Nothing from Modules 1–9 is removed. The keyword themes stay in `themes`; the LLM's choices go in a new column, `themes_llm`; and the `jobs.posting_themes` view uses the LLM's themes wherever they exist, falling back to keywords otherwise.

### 10.1 Get an API key

1. Sign in to the Claude Developer Platform at [platform.claude.com](https://platform.claude.com) with any account. A Claude.ai subscription doesn't include API usage; the API is billed separately, per use.
2. Under **Billing**, add a small amount of prepaid credit. A few dollars covers months of this project.
3. Under **API keys**, create a key named something like `job-market-tracker`, and copy it. It's shown only once.
4. Add it to `.env`:

```text
ANTHROPIC_API_KEY=sk-ant-...
```

Add the name, without a value, to `.env.example`, so the template stays complete:

```text
ANTHROPIC_API_KEY=
```

`ANTHROPIC_API_KEY` stays out of `REQUIRED` in `settings.py`, because the pipeline runs fine without it. `settings.get("ANTHROPIC_API_KEY")` still stops with a clear message if the tagger needs it and it's missing.

### 10.2 Install the SDK

**Run in the terminal:**

```bash
uv add anthropic
```

`anthropic` is Anthropic's official Python package for the API. It handles the address, the key, retries on temporary errors, and turning replies into Python objects, the same role `apify-client` plays for Apify.

### 10.3 The model and its settings

| Setting | Value | Why |
| --- | --- | --- |
| Model | `claude-haiku-5-5` (Claude Haiku 5.5) | The smallest, cheapest current model, built for high-volume classification |
| Price | $0.10 per million input tokens, $0.50 per million output | October 2026 prices for prompts under 100K tokens; check the [pricing page](https://platform.claude.com/docs/en/about-claude/pricing) before relying on them |
| Thinking | Disabled | Haiku 5.5 can "think" before answering, and thinking tokens are billed as output. Picking themes from a list doesn't need it |
| Effort | `low` | Less work per answer; plenty for this task |
| Output format | A JSON schema | **Structured outputs**: the reply is guaranteed to be valid JSON in your shape, and theme names can only come from your list |

A **token** is the unit models read and write, roughly three-quarters of a word, or about 4 characters of English. You pay for tokens in (the instructions plus the job description) and tokens out (the answer).

### 10.4 The tagger: `core/llm_tagger.py`

Create `core/llm_tagger.py`:

```python
"""Theme tagging with an LLM (optional, Module 10). Same .tag() method as ThemeTagger."""
import json
from pathlib import Path

import anthropic
import yaml

from core import settings

MODEL = "claude-haiku-5-5"
# USD per million tokens for MODEL, for prompts under 100K tokens (October 2026 prices).
PRICE_IN = 0.10
PRICE_OUT = 0.50
MAX_TEXT_CHARS = 8000  # long descriptions are cut here to cap the cost per job


class LLMTagger:
    """Asks Claude which of a fixed list of themes a job posting asks for."""

    def __init__(self, themes: list[dict], client=None, model: str = MODEL):
        self.names = [t["theme"] for t in themes]
        self.client = client or anthropic.Anthropic(api_key=settings.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0

        theme_lines = "\n".join(f"- {t['theme']} (for example: {', '.join(t['phrases'][:6])})" for t in themes)
        self.system = (
            "You classify job postings for a labor-market analysis.\n"
            "From the themes below, choose every theme the posting genuinely asks for: a required "
            "or preferred skill, or a core part of the work. Do not choose a theme that is only "
            "mentioned in passing or explicitly not needed. Choose none if none apply.\n\n"
            f"Themes:\n{theme_lines}"
        )
        self.schema = {
            "type": "object",
            "properties": {
                "themes": {"type": "array", "items": {"type": "string", "enum": self.names}},
            },
            "required": ["themes"],
            "additionalProperties": False,
        }

    @classmethod
    def from_yaml(cls, path: str | Path, **kwargs) -> "LLMTagger":
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")), **kwargs)

    def tag(self, text: str | None) -> list[str]:
        """Return the themes the model picked, in themes.yaml order."""
        if not text:
            return []
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=self.system,
            messages=[{"role": "user", "content": text[:MAX_TEXT_CHARS]}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": self.schema},
            },
            thinking={"type": "disabled"},
        )
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens

        reply = next(block.text for block in response.content if block.type == "text")
        picked = {p.lower() for p in json.loads(reply)["themes"]}
        return [name for name in self.names if name.lower() in picked]

    @property
    def cost_usd(self) -> float:
        """What the calls so far have cost, from the token counts Anthropic reported."""
        return self.input_tokens / 1e6 * PRICE_IN + self.output_tokens / 1e6 * PRICE_OUT
```

**The constants at the top.** `MODEL`, the two prices, and `MAX_TEXT_CHARS` are the values most likely to need changing: a newer model, a price change, a different cost cap. Keeping them together at the top makes that a one-line edit. They stay Python constants rather than YAML because the prices only mean something next to the code that uses them.

**`__init__`** prepares everything that's the same for every job:

- `self.names` is the list of theme names from `themes.yaml`, in order.
- `client or anthropic.Anthropic(...)` uses a client you pass in, or creates a real one with your key. Being able to pass one in is what lets the tests use a fake (10.6).
- `self.system` is the **system prompt**: standing instructions sent with every request. It explains the task, including "do not choose a theme that is only mentioned in passing or explicitly not needed", the case keywords get wrong. It then lists each theme with up to six of its phrases from `themes.yaml` as examples. `t['phrases'][:6]` takes the first six.
- `self.schema` is the JSON schema the reply must follow: an object with one key, `themes`, holding a list of strings, each of which must be one of your names (`"enum": self.names`). `"additionalProperties": False` forbids extra keys; structured outputs require it.

**`tag(text)`** makes one request per job:

- `messages=[{"role": "user", "content": ...}]` is the conversation: one message from you containing the job text, cut at `MAX_TEXT_CHARS`. The responsibilities and requirements usually come early in a posting, so the cut rarely loses anything that matters, and it caps the cost of unusually long postings.
- `max_tokens=300` limits the length of the answer. A list of themes needs well under 100.
- `output_config` sets the effort and the JSON schema; `thinking={"type": "disabled"}` turns thinking off (10.3).
- `response.usage` reports the tokens actually used. Adding them to running totals is how the script reports real cost.
- `response.content` is a list of blocks; `next(... if block.type == "text")` takes the first text block, which holds the JSON.
- `json.loads(reply)["themes"]` parses it. Names are compared in lowercase, because the model may occasionally change capitalization; the loop then returns your exact names, in `themes.yaml` order, so results are tidy and comparable.

**`cost_usd`** is a **property**: a method you read like an attribute, `tagger.cost_usd`, without brackets. It turns the token totals into dollars with the prices above.

The class has the same `tag(text)` method as `ThemeTagger`, so anything that works with one works with the other.

### 10.5 The database change and the tagging script

**Add the column.** In `sql/010_linkedin_jobs.sql`, just before the first `create index`, add:

```sql
-- Module 10 (optional): themes chosen by an LLM. NULL = not tagged yet.
alter table jobs.postings add column if not exists themes_llm text[];
```

`NULL` (nothing stored) means "not tagged yet", while an empty list `'{}'` means "tagged, and no theme applies". That difference is how the script knows what's left to do.

**Make the view prefer it.** In the same file, change the last line of `jobs.posting_themes` to:

```sql
cross join lateral unnest(coalesce(p.themes_llm, p.themes)) as t(theme);
```

`coalesce` returns the first value that isn't `NULL`: the LLM's themes where they exist, the keyword themes otherwise. Any query or BI report built on `jobs.posting_themes` follows automatically.

Because Module 4's migration drops and rebuilds the views, this works when you re-run it, even though `postings` gained a column. Apply it now:

```bash
uv run python -m core.db
```

**The script.** Create `projects/linkedin_jobs/llm_tag.py`:

```python
"""Optional (Module 10): tag stored postings that don't have LLM themes yet.

Usage:
    uv run python -m projects.linkedin_jobs.llm_tag --limit 10   # try it on 10 postings
    uv run python -m projects.linkedin_jobs.llm_tag              # every untagged posting
"""
import argparse
import sys
from pathlib import Path

from core import db
from core.llm_tagger import LLMTagger

HERE = Path(__file__).parent
MAX_FAILURES_IN_A_ROW = 5


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tag untagged postings with an LLM")
    ap.add_argument("--limit", type=int, help="tag at most this many postings (default: all)")
    args = ap.parse_args(argv)

    tagger = LLMTagger.from_yaml(HERE / "themes.yaml")
    with db.connect() as conn:
        rows = conn.execute(
            """
            select job_id, title, description_text from jobs.postings
             where themes_llm is null and description_text is not null
             order by first_seen_at desc
             limit %s
            """,
            (args.limit,),
        ).fetchall()
        print(f"{len(rows)} postings to tag with {tagger.model}", flush=True)

        done, failed, in_a_row = 0, 0, 0
        for job_id, title, description in rows:
            try:
                themes = tagger.tag(f"{title}\n\n{description}")
            except Exception as e:
                failed += 1
                in_a_row += 1
                print(f"  {job_id}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                if in_a_row >= MAX_FAILURES_IN_A_ROW:
                    print("Stopping: too many failures in a row.", file=sys.stderr)
                    break
                continue
            in_a_row = 0
            conn.execute("update jobs.postings set themes_llm = %s where job_id = %s", (themes, job_id))
            done += 1
            if done % 50 == 0:
                conn.commit()
                print(f"  {done} tagged, ${tagger.cost_usd:.3f} so far", flush=True)
        conn.commit()

    print(f"Tagged {done}, failed {failed}. Tokens: {tagger.input_tokens:,} in, "
          f"{tagger.output_tokens:,} out. Cost: ${tagger.cost_usd:.3f}")
    return 1 if failed and not done else 0


if __name__ == "__main__":
    sys.exit(main())
```

- The query picks postings with `themes_llm is null`: everything not tagged yet. Because Module 5's deduplication keeps one row per job, a job seen again next month is already tagged and costs nothing. You only ever pay once per job.
- `limit %s` with `None` becomes `limit NULL` in SQL, which Postgres reads as "no limit". So `--limit` is optional with no extra code.
- `order by first_seen_at desc` tags the newest postings first, so a limited run covers the current month.
- One failed request (a network blip, a rate limit) is printed and skipped; the posting stays `NULL` and is retried next run. Five failures in a row usually mean something systematic, like a wrong key or empty credit, so the script stops instead of printing thousands of errors.
- It commits every 50 postings, so a crash halfway keeps the work done so far.

**Checkpoint, a small test run (about $0.002):**

```bash
uv run python -m projects.linkedin_jobs.llm_tag --limit 10
```

Expect something like:

```text
10 postings to tag with claude-haiku-5-5
Tagged 10, failed 0. Tokens: 15,230 in, 412 out. Cost: $0.002
```

Then look at what it chose next to the keyword themes, in the SQL Editor:

```sql
select title, themes, themes_llm
from jobs.postings
where themes_llm is not null
limit 10;
```

Read two or three of the descriptions where the two disagree. If the LLM keeps misreading a theme, the fix is usually a clearer theme name or better example phrases in `themes.yaml`, which both taggers use.

When you're happy, tag everything already stored:

```bash
uv run python -m projects.linkedin_jobs.llm_tag
```

### 10.6 Tests

Create `tests/test_llm_tagger.py`:

```python
"""Tests for the optional LLM tagger (Module 10). No API calls: a fake client stands in."""
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.llm_tagger import LLMTagger

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "projects/linkedin_jobs/themes.yaml"


class FakeMessages:
    """Records the request and returns a canned reply shaped like the real one."""

    def __init__(self, reply: str):
        self.reply = reply
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.reply)],
            usage=SimpleNamespace(input_tokens=1500, output_tokens=40),
        )


def fake_client(reply: str):
    return SimpleNamespace(messages=FakeMessages(reply))


def test_tag_keeps_only_known_themes_in_yaml_order():
    client = fake_client('{"themes": ["dashboards & BI", "Generative AI & LLMs", "Underwater basket weaving"]}')
    tagger = LLMTagger.from_yaml(THEMES, client=client)
    assert tagger.tag("Senior analyst: Power BI, some LLM work") == ["Generative AI & LLMs", "Dashboards & BI"]


def test_request_is_cheap_and_structured():
    client = fake_client('{"themes": []}')
    tagger = LLMTagger.from_yaml(THEMES, client=client)
    tagger.tag("x" * 20000)
    req = client.messages.last_request
    assert req["model"] == "claude-haiku-5-5"
    assert req["thinking"] == {"type": "disabled"}
    assert req["output_config"]["effort"] == "low"
    assert req["output_config"]["format"]["schema"]["properties"]["themes"]["items"]["enum"] == tagger.names
    assert len(req["messages"][0]["content"]) == 8000  # long text is cut


def test_cost_tracking():
    tagger = LLMTagger.from_yaml(THEMES, client=fake_client('{"themes": []}'))
    tagger.tag("a")
    tagger.tag("b")
    assert (tagger.input_tokens, tagger.output_tokens) == (3000, 80)
    assert tagger.cost_usd == pytest.approx(3000 / 1e6 * 0.10 + 80 / 1e6 * 0.50)


def test_empty_text_makes_no_call():
    client = fake_client("not used")
    assert LLMTagger.from_yaml(THEMES, client=client).tag("") == []
    assert client.messages.last_request is None


DB = os.environ.get("TEST_DB_URL")


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_llm_tag_script_tags_only_untagged(monkeypatch):
    import json

    import psycopg

    from core import db
    from projects.linkedin_jobs import llm_tag, load
    from projects.linkedin_jobs.transform import merge_items, to_row
    from core.text import ThemeTagger

    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    items = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text(encoding="utf-8"))
    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.commit()
        db.migrate(conn)
        run_id = conn.execute("insert into core.run_log (project) values ('t') returning run_id").fetchone()[0]
        merged = merge_items({"data analyst": items})
        rows = [to_row(i, t, ThemeTagger.from_yaml(THEMES)) for i, t in merged.values()]
        load.upsert_postings(conn, run_id, rows, __import__("datetime").date(2026, 10, 1))
        conn.execute("update jobs.postings set themes_llm = '{}' where job_id = '4100000003'")  # already tagged
        conn.commit()

    fake = LLMTagger.from_yaml(THEMES, client=fake_client('{"themes": ["Product analytics"]}'))
    monkeypatch.setattr(llm_tag.LLMTagger, "from_yaml", classmethod(lambda cls, path: fake))
    assert llm_tag.main([]) == 0

    with psycopg.connect(DB) as conn:
        tagged = dict(conn.execute("select job_id, themes_llm from jobs.postings").fetchall())
        assert tagged == {"4100000001": ["Product analytics"], "4100000002": ["Product analytics"], "4100000003": []}
        # Views now prefer the LLM themes
        themes = {t for (t,) in conn.execute("select distinct theme from jobs.posting_themes")}
        assert themes == {"Product analytics"}
```

- `SimpleNamespace` builds a quick object with whatever attributes you give it, here shaped like the SDK's response (`.content`, `.usage`). The fake client never contacts Anthropic, so the tests are free and work offline.
- The first test checks that unknown names are dropped, capitalization is fixed, and results follow `themes.yaml` order.
- The second checks the request itself: the cheap model, thinking off, low effort, the schema built from your themes, and the text cut at 8,000 characters. If someone later changes these by accident, the test catches it before it costs money.
- The database test runs the script against the throwaway database with a fake tagger. It checks that only untagged postings are tagged (job 3 already had `'{}'`) and that the views switch to the LLM's themes.

**Run in the terminal:**

```bash
uv run pytest -v
```

**Checkpoint:** `8 passed, 3 skipped` locally; all 11 pass on GitHub.

### 10.7 Automate it, and what it costs

Add the key to GitHub: **Settings → Secrets and variables → Actions → New repository secret**, named `ANTHROPIC_API_KEY`. Then add this step at the end of `.github/workflows/linkedin-jobs.yml`, indented to line up with the `- name: Scrape and load` step above it:

```yaml
      - name: Tag new postings with an LLM
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: uv run --no-dev python -m projects.linkedin_jobs.llm_tag
```

Steps run in order and stop at the first failure, so tagging only happens after a successful scrape and load.

**The cost estimate.** Per posting:

| Part | Tokens | Notes |
| --- | --- | --- |
| Instructions and theme list | ~370 in | The system prompt; the same for every job |
| JSON format instructions | ~100–200 in | Added by the API for structured outputs (estimate) |
| Job title and description | ~1,000 in, typically | About 4,000 characters; capped at 8,000 characters (~2,000 tokens) |
| Answer | ~40 out | A short JSON list |
| **Total** | **~1,500 in, ~40 out** | |

At Haiku 5.5's prices, that's 1,500 × $0.10 / 1,000,000 + 40 × $0.50 / 1,000,000 ≈ **$0.00017 per posting**.

| Monthly volume | Haiku 5.5 (this module) | Haiku 4.5 ($1 / $5) | Sonnet 5.5 ($2 / $10) |
| --- | --- | --- | --- |
| 2,500 postings (Apify free plan, 500 per search) | ~$0.43 | ~$4.25 | ~$8.50 |
| 5,000 postings (Apify Starter, full config) | ~$0.85 | ~$8.50 | ~$17 |
| Worst case: 5,000 postings, every one at the 8,000-character cap | ~$1.40 | ~$14 | ~$28 |

Two things make the real number easy to check:

- **Almost every posting each month is new.** With `datePosted: pastMonth` and monthly runs, the overlap between months is small, so expect to tag close to your full monthly volume. A one-time cost covers tagging postings already stored.
- **The script prints the actual cost** from the token counts Anthropic reports. After the `--limit 10` run, divide by 10 for your real cost per posting and multiply by your monthly volume.

If cost ever matters more, Anthropic's **Batch API** halves the price in exchange for results arriving within hours instead of seconds, which suits a monthly job. It needs a different request flow (submit a batch, check back, collect results), so it's a reasonable next step once this version works.

**Commit:**

```bash
git add .
git commit -m "Module 10: optional LLM theme tagging"
git push
```

### Check your understanding

1. Why does the script only tag rows where `themes_llm is null`, and why does that keep the cost down?
2. What would go wrong without the JSON schema in `output_config`?
3. Why is thinking disabled?
4. After this module, which themes does `jobs.posting_themes` show for a posting the LLM hasn't tagged yet?

<details>
<summary>Answers</summary>

1. Each job is tagged once, ever. Thanks to deduplication, a job seen again next month already has `themes_llm`, so you never pay twice for the same posting.
2. The model could reply in prose, wrap the JSON in extra text, or invent theme names not in your list, and `json.loads` would fail or the analysis would fill with unexpected themes. The schema guarantees valid JSON containing only your names.
3. Thinking tokens are billed as output, at five times the input price, and choosing items from a fixed list doesn't benefit from it. Turning it off keeps each answer to a few dozen tokens.
4. Its keyword themes: `coalesce(themes_llm, themes)` falls back to `themes` while `themes_llm` is `NULL`.

</details>

---

## Module 11: A dashboard with Streamlit

The pipeline fills Supabase every month; this module puts it on screen. You'll build a small web app in Python that answers the question the project started with: what do employers ask for, and where are your gaps? Allow about 2 hours. It costs nothing to run.

What you'll build:

- Headline numbers: roles, companies, how many show a salary, the median yearly salary.
- **The gap chart:** every theme by how often employers mention it. You tick the themes you already cover, and the rest light up as gaps.
- Industries hiring, seniority mix, and a themes-by-industry heatmap.
- A searchable table of the roles themselves, with links.
- Filters for the searches and the months.

It works with whatever is in the database, even your 25-row test runs. The charts start to mean something after the first full monthly run.

### 11.1 Streamlit in five ideas

1. **An app is a Python script.** `st.title("Hi")` puts a title on the page and `st.bar_chart(data)` puts a chart there, top to bottom, in the order the lines run. There's no HTML, CSS or JavaScript to write.
2. **The whole script reruns on every click.** Change a filter and Streamlit runs your file again from the top, with the new filter value. That sounds wasteful, and it's what makes Streamlit simple: there are no event handlers, just a script that's always up to date.
3. **A widget returns its current value.** `terms = st.multiselect("Searches", ...)` draws the box *and* gives you what's selected right now, as a normal Python list.
4. **Caching stops the reruns from being slow.** Because the script reruns on every click, anything slow (like a database query) gets wrapped in `@st.cache_data`. Streamlit remembers the result for each set of arguments and skips the work next time.
5. **Deploying is connecting your GitHub repo.** Streamlit Community Cloud runs the app for free from your repo and redeploys whenever you push.

### 11.2 Install

**Run in the terminal:**

```bash
uv add streamlit pandas altair
```

| Package | Role |
| --- | --- |
| `streamlit` | The app framework: the page, the widgets, the caching, the server |
| `pandas` | Tables in memory. Streamlit's charts and tables take pandas DataFrames |
| `altair` | Charts, with more control than Streamlit's built-in ones |

Streamlit installs pandas and Altair anyway, as its own dependencies. Adding them by name records that *your* code imports them, so they can't silently disappear if Streamlit ever drops them.

**Why pandas now, when the pipeline avoids it?** In the pipeline, rows go from JSON to Postgres one by one, and lists of dicts do that job fine. In the app, the data is a table you hand to a chart, which is exactly what a DataFrame is for. Use each tool where it fits.

One side effect: the GitHub workflows run `uv sync`, so they now install Streamlit too, which adds a few seconds to each run. That's harmless.

### 11.3 The queries: `queries.py`

Keep the SQL out of the app. A separate module of plain functions is easier to read, and it can be tested without starting Streamlit. Create `projects/linkedin_jobs/queries.py`:

```python
"""SQL behind the dashboard. Every function returns plain rows: a list of dicts."""

from datetime import date

import psycopg
from psycopg.rows import dict_row

# Distinct roles (reposts collapsed) from any of the chosen searches that were
# visible at some point between the start and end months. Each query below
# starts from this, so the filters behave the same in every chart.
ROLES = """
    select p.*
    from jobs.postings_dedup p
    where p.search_terms && %(terms)s::text[]
      and date_trunc('month', p.role_first_seen_at) <= %(end)s
      and date_trunc('month', p.role_last_seen_at) >= %(start)s
"""


def _rows(conn: psycopg.Connection, sql: str, params: dict | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(sql, params).fetchall()


def filter_options(conn: psycopg.Connection) -> dict:
    """The search terms and months that exist, to fill the sidebar."""
    terms = _rows(conn, "select distinct unnest(search_terms) as term from jobs.postings order by term")
    months = _rows(conn, """
        select month from (
            select date_trunc('month', first_seen_at)::date as month from jobs.postings
            union
            select date_trunc('month', last_seen_at)::date from jobs.postings
        ) m
        order by month
    """)
    return {"terms": [r["term"] for r in terms], "months": [r["month"] for r in months]}


def dashboard(conn: psycopg.Connection, terms: list[str], start: date, end: date) -> dict:
    """Everything the dashboard shows, for one set of filters."""
    f = {"terms": terms, "start": start, "end": end}

    summary = _rows(conn, f"""
        with roles as ({ROLES})
        select count(*) as roles,
               count(distinct company_name) as companies,
               round(100.0 * count(salary_min) / nullif(count(*), 0))::float as pct_with_salary,
               percentile_cont(0.5) within group (order by (salary_min + coalesce(salary_max, salary_min)) / 2)
                   filter (where salary_period = 'yr') as median_salary
        from roles
    """, f)[0]

    themes = _rows(conn, f"""
        with roles as ({ROLES})
        select t.theme,
               count(*) as roles,
               round(100.0 * count(*) / (select count(*) from roles), 1)::float as pct
        from roles r
        join jobs.posting_themes t on t.job_id = r.job_id
        group by t.theme
        order by roles desc, t.theme
    """, f)

    industries = _rows(conn, f"""
        with roles as ({ROLES})
        select coalesce(primary_industry, 'Unknown') as industry, count(*) as roles
        from roles
        group by 1
        order by roles desc, industry
        limit 15
    """, f)

    seniority = _rows(conn, f"""
        with roles as ({ROLES})
        select coalesce(seniority_level, 'Unknown') as seniority, count(*) as roles
        from roles
        group by 1
        order by roles desc
    """, f)

    theme_by_industry = _rows(conn, f"""
        with roles as ({ROLES}),
        top as (
            select primary_industry, count(*) as n
            from roles
            where primary_industry is not null
            group by primary_industry
            order by n desc
            limit 8
        )
        select top.primary_industry as industry,
               t.theme,
               round(100.0 * count(*) / top.n, 1)::float as pct
        from roles r
        join top on top.primary_industry = r.primary_industry
        join jobs.posting_themes t on t.job_id = r.job_id
        group by top.primary_industry, top.n, t.theme
        order by industry, t.theme
    """, f)

    postings = _rows(conn, f"""
        with roles as ({ROLES})
        select r.title, r.company_name, r.primary_industry, r.seniority_level, r.location,
               r.workplace_type, r.salary_min, r.salary_max, r.salary_period,
               r.role_first_seen_at as first_seen, r.link,
               array(select t.theme from jobs.posting_themes t
                     where t.job_id = r.job_id order by t.theme) as themes
        from roles r
        order by r.role_first_seen_at desc, r.title
    """, f)

    return {
        "summary": summary,
        "themes": themes,
        "industries": industries,
        "seniority": seniority,
        "theme_by_industry": theme_by_industry,
        "postings": postings,
    }
```

**`ROLES`: one filter, used by every query.** Each query starts with `with roles as ({ROLES})`, a CTE (a named subquery, like T-SQL's `WITH`), so every chart filters the same way:

- `from jobs.postings_dedup` counts roles, not postings: a job reposted under a new ID counts once (Module 4).
- `p.search_terms && %(terms)s::text[]`: `&&` means "the two arrays overlap", that is, they share at least one element. A role found by `data analyst` matches if you picked `data analyst`, even if it was also found by `data scientist`. `::text[]` tells Postgres the parameter is a text array.
- The two `date_trunc` lines keep roles that were **visible at any point** in the chosen months: first seen no later than the end month, and last seen no earlier than the start month. `date_trunc('month', ...)` rounds a date down to the 1st of its month, so whole months compare cleanly.

**An f-string around SQL, safely.** `f"""with roles as ({ROLES}) ..."""` pastes the `ROLES` text into each query. That's safe because `ROLES` is your own constant. The values the user picks still go in through `%(terms)s`-style placeholders, which psycopg fills in safely (Module 5). Never paste user input into SQL with an f-string.

**`_rows`** runs a query and returns a list of dicts. `row_factory=dict_row` makes psycopg return each row as `{"theme": ..., "roles": ...}` instead of a tuple, so the app can use column names. The leading underscore says "used inside this module only".

**`filter_options`** finds what the sidebar should offer: every search term (`unnest` turns the arrays into rows, `distinct` drops repeats) and every month with data (`union` merges two lists and removes duplicates).

**`dashboard`** runs six queries and returns them in one dict:

| Key | What it is | SQL worth noticing |
| --- | --- | --- |
| `summary` | The four headline numbers | `count(salary_min)` counts only non-null values; `nullif(count(*), 0)` avoids dividing by zero; `percentile_cont(0.5) within group (...)` is the median, and `filter (where salary_period = 'yr')` limits it to yearly salaries |
| `themes` | Each theme's share of roles | Joins to the `jobs.posting_themes` view, which already uses the LLM's themes where they exist (Module 10). `::float` turns Postgres's exact decimals into ordinary numbers for the charts |
| `industries` | Top 15 industries | `coalesce(primary_industry, 'Unknown')` gives missing values a label |
| `seniority` | Roles per seniority level | |
| `theme_by_industry` | Theme shares within the 8 biggest industries | A second CTE, `top`, finds those industries and their sizes; each share divides by its own industry's total |
| `postings` | The roles for the table | `array(select ...)` collects each role's themes into one list column |

**Checkpoint.** Try the functions without any app at all:

```bash
uv run python -c "from core import db; from projects.linkedin_jobs import queries; print(queries.filter_options(db.connect()))"
```

You should see your search terms and months, for example `{'terms': ['data analyst', 'data scientist'], 'months': [datetime.date(2026, 10, 1)]}`.

### 11.4 The app: `app.py`

Create `projects/linkedin_jobs/app.py`:

```python
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
from projects.linkedin_jobs import queries

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
st.caption(f"{', '.join(terms)} · {start:%b %Y} to {end:%b %Y} · reposts counted once")

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
        "workplace_type": "Workplace",
        "salary_min": st.column_config.NumberColumn("Salary from", format="$%,.0f"),
        "salary_max": st.column_config.NumberColumn("Salary to", format="$%,.0f"),
        "salary_period": "Per",
        "first_seen": st.column_config.DateColumn("First seen"),
        "link": st.column_config.LinkColumn("Link", display_text="Open"),
        "themes": st.column_config.ListColumn("Themes"),
    },
)
```

Section by section:

**The `sys.path` fix.** This is the `python -m` lesson from Module 1 again. Streamlit runs your file *by path*, so `sys.path[0]` is the file's own folder, `projects/linkedin_jobs/`, and `from core import db` would fail with `ModuleNotFoundError`. `Path(__file__).resolve().parent.parent.parent` climbs three levels (file → `linkedin_jobs` → `projects` → project folder), the same anchoring trick as `SQL_DIR` in `core/db.py`, and `sys.path.insert(0, ...)` puts that folder first. The imports come after the fix, because they need it.

**Constants.** Two colors: orange for gaps, the one thing that should catch your eye, and a quiet grey for themes you cover. `THEMES` reads the theme names from `themes.yaml`, so the "Themes I already cover" box always offers the full list, in your order, whatever the filters show.

**`bars`** builds a horizontal bar chart with Altair, which the app needs twice. Altair describes a chart rather than drawing it step by step:

- `alt.Chart(df)` says "chart this table".
- `.mark_bar()` says "with bars". `cornerRadiusEnd=4` rounds the far end of each bar.
- `.encode(...)` maps columns to visual channels: `x` is the bar length (`:Q`, quantitative, a number), `y` is the category (`:N`, nominal, a name), and `tooltip` is what appears on hover. `sort="-x"` puts the longest bar first. `labelLimit` widens the space for long labels before they're cut off with "…".

**The cached loaders.** `load_options` and `load_dashboard` open a connection, call `queries`, and close it. `@st.cache_data(ttl="1h")` remembers each result for an hour per set of arguments. Change a filter and the first load runs the queries; switch back and it's instant. Your data only changes once a month, so an hour is plenty. `show_spinner` shows "Querying Supabase..." while it runs.

**The sidebar.** `st.sidebar.` puts a widget in the left panel instead of the page:

- If there are no months, there's no data yet: `st.info(...)` shows a note and `st.stop()` ends this run of the script there.
- `st.sidebar.multiselect` returns the chosen searches as a list; `default=` starts with all of them ticked.
- `st.sidebar.select_slider` with `value=(first, last)` gives a range slider and returns two values, unpacked into `start, end`. `format_func` changes how each month is shown (`Oct 2026`), not its value. With only one month, a slider makes no sense, so it shows a caption instead.

**Headline numbers.** `st.columns(4)` splits the width into four, and `c1.metric(...)` puts a big number in the first. `f"{s['roles']:,}"` formats with thousands separators (`1,234`). `s['pct_with_salary'] or 0` turns a missing value into 0, which happens when the filters match nothing.

**The gap chart** is the reason the project exists:

- `pd.DataFrame(data["themes"])` turns the list of dicts into a table.
- `themes["you"] = themes["theme"].map(...)` adds a column: `"Covered"` if you ticked the theme, `"Gap"` otherwise. `.map` runs the `lambda` on every value in the column.
- `color=alt.Color("you:N", scale=alt.Scale(domain=[...], range=[...]))` colors bars by that column: the first domain value gets the first color, and so on.
- `themes[themes["you"] == "Gap"].head(3)` keeps the gap rows, already sorted by demand, and takes the top three. `itertuples()` loops over the rows with attribute access (`r.theme`, `r.pct`).

**Who is hiring.** `with left:` puts everything indented under it into the left column. Each column gets a `bars(...)` chart.

**The heatmap.** The same Altair pattern with `mark_rect` (a rectangle per cell) and the color channel carrying the number. `scheme="blues"` runs from light to dark blue: darker means more of that industry's roles mention the theme. `stroke="white"` draws thin gaps between cells so they read as separate. `sort=all_themes` lists themes in the same order as the gap chart.

**Browse roles.** `st.selectbox` returns one choice. The theme filter runs in Python on rows already loaded, so it doesn't query the database again. `st.dataframe` shows an interactive table: click a header to sort, and use the search icon above it to find text. `column_config` renames columns and formats them: `NumberColumn` with `format="$%,.0f"` shows `$130,000`, and `LinkColumn` turns the URL into a clickable "Open".

**Run it:**

```bash
uv run streamlit run projects/linkedin_jobs/app.py
```

Streamlit isn't run with `python -m`. It's a program of its own that runs your file, which is why the `sys.path` fix is needed.

**Checkpoint:** your browser opens `http://localhost:8501` with the dashboard. Tick two or three themes in the sidebar and watch those bars turn grey and the "Your biggest gaps" line appear. Edit the code, save, and click **Rerun** in the top right (or turn on **Always rerun**) to see the change. Stop the app with Ctrl+C in the terminal.

### 11.5 A read-only database user

Locally, the app uses the `SUPABASE_DB_URL` in your `.env`: the `postgres` user, which can change or delete anything. Once the app is deployed (11.7), that connection string lives on Streamlit's servers. The app only ever reads, so give it a user that can only read. If the string ever leaked, the worst anyone could do is look at public job postings.

**1. Create the user, once.** In Supabase: **SQL Editor → New query**. Pick a long password of letters and numbers only (characters like `@`, `:`, `/` and `#` would break the connection string), and run:

```sql
create role dashboard_reader with login password 'choose-a-long-password';
```

This step is done by hand, not in a `sql/` file, because the password must never be in git.

**2. Grant it read access, in a migration.** Create `sql/900_dashboard_reader.sql`:

```sql
-- Read-only access for the dashboard (Module 11). Named 900 so it runs after every other file.
-- You create the dashboard_reader role once, by hand, in the Supabase SQL Editor,
-- because its password must never be in git. This file only grants it read access,
-- and runs on every migration because the views are dropped and rebuilt each time
-- (a rebuilt view starts with no grants). Without the role, it does nothing.
do $$
begin
    if exists (select from pg_roles where rolname = 'dashboard_reader') then
        grant usage on schema jobs to dashboard_reader;
        grant select on all tables in schema jobs to dashboard_reader;
    end if;
end
$$;
```

- `do $$ ... $$` runs a small block of procedural code, like a T-SQL batch with `IF`. `$$` is Postgres's way of quoting a block that contains its own quotes.
- `if exists (select from pg_roles where rolname = ...)` checks the user exists, so the file also runs safely on the test database, where it doesn't.
- `grant usage on schema jobs` lets the user see into the schema. `grant select on all tables in schema jobs` lets it read every table **and view** there. It can't insert, update or delete, and it can't see `core.run_log` at all.

Why a migration and not a one-off grant: every migration drops and rebuilds the views (Module 4), and a rebuilt view starts with no grants. Files run in name order, so `900` re-grants after every other file has rebuilt its views, every time. The high number leaves room: any SQL file you add later (Module 12 adds `040`) still runs before it.

Apply it, either locally or by pushing, since the **Set up database** workflow runs on any change under `sql/`:

```bash
uv run python -m core.db
```

**3. Build its connection string.** Take your Session pooler string and change the user and password:

```text
postgresql://dashboard_reader.<ref>:<its-password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

The user is `dashboard_reader.` followed by your project ref, the same `.<ref>` suffix that `postgres.<ref>` has. The pooler needs it to know which project you mean.

**Checkpoint.** Run the app once as the reader. An environment variable set on the command line wins over `.env`, because `load_dotenv()` never overrides one that's already set (Module 1):

```bash
SUPABASE_DB_URL="postgresql://dashboard_reader.<ref>:<its-password>@aws-0-<region>.pooler.supabase.com:5432/postgres" uv run streamlit run projects/linkedin_jobs/app.py
```

The dashboard should look exactly the same. `NAME=value command` sets a variable for that one command only, in Git Bash and on Mac; your `.env` is untouched.

### 11.6 Tests

Create `tests/test_dashboard.py`:

```python
"""Tests for the dashboard's queries and the app itself.

All of them need a throwaway Postgres: TEST_DB_URL=postgresql://... uv run pytest
"""

import json
import os
from datetime import date
from pathlib import Path

import psycopg
import pytest

from core.text import ThemeTagger
from projects.linkedin_jobs.transform import merge_items, to_row

ROOT = Path(__file__).resolve().parent.parent
ITEMS = json.loads((ROOT / "tests/fixtures/sample_items.json").read_text(encoding="utf-8"))
TAGGER = ThemeTagger.from_yaml(ROOT / "projects/linkedin_jobs/themes.yaml")
DB = os.environ.get("TEST_DB_URL")
OCT, NOV = date(2026, 10, 1), date(2026, 11, 1)

pytestmark = pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")


@pytest.fixture
def conn():
    """A fresh database: job 1 in October; jobs 2 and 3 (a repost of 2) in November."""
    from core import db
    from projects.linkedin_jobs import load

    with psycopg.connect(DB) as conn:
        conn.execute("drop schema if exists jobs cascade; drop schema if exists core cascade")
        conn.execute("""
            do $$ begin
                if not exists (select from pg_roles where rolname = 'dashboard_reader') then
                    create role dashboard_reader;
                end if;
            end $$;
        """)
        conn.commit()
        db.migrate(conn)
        run_id = conn.execute("insert into core.run_log (project) values ('t') returning run_id").fetchone()[0]
        for items, term, seen in [(ITEMS[:1], "data scientist", OCT), (ITEMS[1:], "data analyst", NOV)]:
            merged = merge_items({term: items})
            load.upsert_postings(conn, run_id, [to_row(i, t, TAGGER) for i, t in merged.values()], seen)
            conn.commit()
        yield conn


def test_filter_options(conn):
    from projects.linkedin_jobs import queries

    assert queries.filter_options(conn) == {"terms": ["data analyst", "data scientist"], "months": [OCT, NOV]}


def test_dashboard_counts_roles_not_reposts(conn):
    from projects.linkedin_jobs import queries

    d = queries.dashboard(conn, ["data scientist", "data analyst"], OCT, NOV)
    assert d["summary"]["roles"] == 2            # jobs 2 and 3 are one role
    assert d["summary"]["median_salary"] == 145000  # job 1: $130K-$160K/yr; job 2 is hourly
    assert len(d["postings"]) == 2
    assert {r["industry"] for r in d["industries"]} == {"Hospitals and Health Care", "Staffing and Recruiting"}
    assert all(0 < t["pct"] <= 100 for t in d["themes"])
    assert "Machine learning modeling" in d["postings"][-1]["themes"]


def test_dashboard_filters(conn):
    from projects.linkedin_jobs import queries

    october = queries.dashboard(conn, ["data scientist", "data analyst"], OCT, OCT)
    assert october["summary"]["roles"] == 1
    analysts = queries.dashboard(conn, ["data analyst"], OCT, NOV)
    assert [p["title"] for p in analysts["postings"]] == [ITEMS[1]["title"]]
    nothing = queries.dashboard(conn, ["nobody searched this"], OCT, NOV)
    assert nothing["summary"]["roles"] == 0 and nothing["themes"] == []


def test_reader_role_can_read_but_not_write(conn):
    conn.execute("set role dashboard_reader")
    assert conn.execute("select count(*) from jobs.postings_dedup").fetchone()[0] == 2
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("delete from jobs.postings")
    conn.rollback()


def test_app_runs(conn, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SUPABASE_DB_URL", DB)
    at = AppTest.from_file(str(ROOT / "projects/linkedin_jobs/app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.metric[0].value == "2"
    at.sidebar.multiselect[1].set_value(["Machine learning modeling"]).run()
    assert not at.exception
    assert "Your biggest gaps" in at.markdown[-1].value
```

- `pytestmark = pytest.mark.skipif(...)` applies the skip to every test in the file at once. They all need the throwaway database.
- `@pytest.fixture def conn():` is a **fixture**: setup code that pytest runs for any test that names `conn` as an argument. Everything before `yield` is setup (a fresh database with job 1 in October and jobs 2 and 3 in November); `yield conn` hands the connection to the test; and when the test finishes, the `with` block closes it. The test database also gets a `dashboard_reader` role (with no login), so the grants are tested.
- The commit inside the loop matters: `upsert_postings` creates a temporary staging table that's dropped at commit, so two loads need two transactions.
- `test_dashboard_counts_roles_not_reposts` checks the key promise: three postings, but jobs 2 and 3 are the same role, so 2 roles. The median is $145,000, the midpoint of job 1's $130K to $160K, because job 2's salary is hourly and is left out.
- `test_dashboard_filters` checks that the month and search filters narrow the results, and that a search with no data returns zeros instead of crashing.
- `test_reader_role_can_read_but_not_write`: `set role dashboard_reader` makes the rest of the session act as that user. Reading works; `pytest.raises(...)` asserts that deleting fails with a permission error.
- `test_app_runs` uses Streamlit's **AppTest**, which runs `app.py` without a browser. It points `SUPABASE_DB_URL` at the test database, checks there's no exception and the first metric says `2`, then ticks a theme in the sidebar (`multiselect[1]`, the second multiselect) and checks the gaps sentence appears.

**Run in the terminal:**

```bash
uv run pytest -v
```

**Checkpoint:** locally, the new tests skip, because there's no `TEST_DB_URL`: `4 passed, 7 skipped` (or `8 passed, 8 skipped` if you did Module 10). On GitHub, the Tests workflow runs them all: `11 passed` (or `16 passed`).

### 11.7 Deploy to Streamlit Community Cloud

First commit and push, since Community Cloud deploys from GitHub:

```bash
git add .
git commit -m "Module 11: Streamlit dashboard"
git push
```

Then:

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub. Allow it to see your repositories, including private ones if your repo is private.
2. Click **Create app → Deploy a public app from GitHub** (the wording may differ slightly).
3. Fill in:

| Field | Value |
| --- | --- |
| Repository | `<your-username>/JobMarketTracker` |
| Branch | `main` |
| Main file path | `projects/linkedin_jobs/app.py` |
| App URL | Optional: pick a short name |

4. Open **Advanced settings**:
   - **Python version:** 3.12, to match `.python-version`.
   - **Secrets:** paste one line, with the **reader's** connection string:

```toml
SUPABASE_DB_URL = "postgresql://dashboard_reader.<ref>:<its-password>@aws-0-<region>.pooler.supabase.com:5432/postgres"
```

5. Click **Deploy**. The first build takes a few minutes.

Things worth knowing:

- **This secret has quotes; `.env` doesn't.** Streamlit's secrets box is TOML, the same format as `pyproject.toml`, where text values must be quoted. `.env` files take raw values.
- **No code change for secrets.** Streamlit also exposes each top-level secret as an environment variable, so `settings.get("SUPABASE_DB_URL")` reads it exactly as it reads `.env` locally and GitHub Secrets in Actions. Three hosts, one line of code.
- **Dependencies come from `uv.lock`.** Community Cloud looks for a dependency file next to the main file, then at the repo root, and it understands `uv.lock`. Keep only one dependency file in the repo, or it uses the first one it finds.
- **Who can see it.** An app deployed from a public repo is public: anyone with the link can view it. From a private repo, only you can, and you can invite viewers by email with **Share**. The free plan allows one private app at a time. The data is public job postings, so either is fine, and the reader user keeps the database safe both ways.
- **It sleeps when idle.** After a period with no visitors (12 hours as of 2025), the app goes to sleep. The next visitor sees a button to wake it, which takes about a minute.
- **Every push redeploys.** Change `app.py`, push, and the live app updates by itself.

**Checkpoint:** the app opens at its `streamlit.app` address and shows the same numbers as your local copy.

### Check your understanding

1. You change a filter. What happens to the script, and why doesn't the database get queried every time?
2. Why does `app.py` need the `sys.path` fix, when `run.py` doesn't?
3. Why is the grant in a migration file, rather than run once by hand like the `create role`?
4. Why does the reader's connection string need quotes in Streamlit's secrets box but not in `.env`?

<details>
<summary>Answers</summary>

1. The whole script reruns from the top with the new filter value. `load_dashboard` is cached per set of arguments, so it queries the database only the first time it sees a combination, and only after the hour-long cache expires.
2. `run.py` is started with `python -m` from the project folder, which puts the project folder on `sys.path`. Streamlit runs `app.py` by path, which puts `projects/linkedin_jobs/` there instead, so `core` can't be found without the fix.
3. Every migration drops and rebuilds the views, and a rebuilt view starts with no grants. Re-granting in `900`, which runs after every other file, restores access every time. The role itself is created by hand because its password can't go in git.
4. The secrets box is TOML, where text values must be quoted. `.env` takes each value as raw text up to the end of the line.

</details>

### Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'core'` | The `sys.path` lines are missing, or come after the imports | Put the fix above `from core import db` |
| `permission denied for schema jobs` (or `for view ...`) | The grants haven't run since the role was created | Run `uv run python -m core.db`, or the **Set up database** workflow |
| `password authentication failed for user "dashboard_reader"` | The user is missing its `.<ref>` suffix, or the password differs | Use `dashboard_reader.<ref>` and check the password; reset it with `alter role dashboard_reader with password '...';` |
| New monthly data doesn't show up | The 1-hour cache | Wait, or open the ⋮ menu (top right) → **Clear cache**, then rerun |
| The deployed app fails while installing packages | `uv.lock` is out of date, or there's a second dependency file | Run `uv lock`, commit `uv.lock`, and remove any stray `requirements.txt` |

---

## Module 12 (optional): Skills by category with an LLM

Themes (Modules 3 and 10) answer "what kind of work is this?". This module answers a sharper question: **which skills do employers ask for, technical and non-technical, and how often?** Every skill gets one of four categories:

| Category | What counts | Examples |
| --- | --- | --- |
| Technical | Tools, languages, methods, engineering practice | SQL, A/B testing, model monitoring |
| Communication | Presenting, writing, explaining, influencing, collaborating | Presenting to leadership, data storytelling |
| Business | Domain knowledge, metrics, product and commercial judgment | Metric definition and KPI design, problem sizing |
| Leadership | Ownership, mentoring, handling ambiguity, driving work forward | Mentoring, scoping open-ended problems |

The dashboard gets a tab for each category, with your gaps highlighted, plus a list of **emerging skills**: ones employers ask for that aren't on your list yet.

This module builds on Module 10: you need its API key (10.1), the `anthropic` package (10.2) and `core/llm_tagger.py` (10.4), whose model and price constants it reuses. Allow about 2 hours. It costs about $0.15 to discover the skill list, about $2 to tag 5,000 postings you already have, and about $2 a month after that (see 12.8).

### 12.1 Why two passes

You can't hand all 5,000 postings to the LLM and ask for statistics. They don't fit in one request (about 5 million tokens), and even when text fits, a model's sense of "most postings ask for X" is an impression, not a count. So, as in Module 10, the LLM reads **one posting at a time**, and **SQL does the counting**.

That raises a naming problem. Asked freely, the LLM calls the same skill "stakeholder management" in one posting and "working with business partners" in the next, and you can't count those together. The fix is two passes:

1. **Discover** (once, then every few months): the LLM reads a sample of about 500 postings freely, and one more request groups the thousands of raw phrases into a list of 40 to 60 named skills. **You review the list** and save it as `skills.yaml`.
2. **Tag** (every posting, then new ones each month): the LLM picks skills only from `skills.yaml`, and marks each as required or preferred. Anything new goes into a separate "other skills" list, which is where emerging skills come from.

### 12.2 The skills code: `core/skills.py`

Create `core/skills.py`:

```python
"""Skills by category with an LLM (Module 12): discover a skill list, then tag postings against it."""
import json
from collections import Counter
from pathlib import Path

import anthropic
import yaml

from core import settings
from core.llm_tagger import MAX_TEXT_CHARS, MODEL, PRICE_IN, PRICE_OUT

CATEGORIES = ["technical", "communication", "business", "leadership"]
LEVELS = ["required", "preferred"]
MAX_OTHER = 5  # new skills kept per posting

CATEGORY_HELP = (
    "Categories:\n"
    "- technical: tools, languages, methods and engineering practices\n"
    "- communication: presenting, writing, explaining, influencing, collaborating\n"
    "- business: domain knowledge, metrics, product and commercial judgment\n"
    "- leadership: ownership, mentoring, managing ambiguity, driving work forward"
)
IGNORE = (
    "Ignore the company description, benefits, pay, legal and equal-opportunity text. "
    "Do not count education, years of experience or work authorization as skills."
)


class Claude:
    """Sends one request that must return JSON in a given shape, and keeps a running cost."""

    def __init__(self, client=None, model: str = MODEL):
        self.client = client or anthropic.Anthropic(api_key=settings.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0

    def ask(self, *, system: str, content: str, schema: dict, max_tokens: int, effort: str = "low") -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            thinking={"type": "disabled"},
        )
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        return json.loads(next(block.text for block in response.content if block.type == "text"))

    @property
    def cost_usd(self) -> float:
        return self.input_tokens / 1e6 * PRICE_IN + self.output_tokens / 1e6 * PRICE_OUT


# ---------- Pass 1: discover the skill list ----------

OPEN_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "category": {"type": "string", "enum": CATEGORIES}},
                "required": ["name", "category"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["skills"],
    "additionalProperties": False,
}

LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "definition": {"type": "string"},
                },
                "required": ["skill", "category", "definition"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["skills"],
    "additionalProperties": False,
}


def extract_open(claude: Claude, text: str) -> list[dict]:
    """Every skill a posting asks for, in short words of the model's choosing."""
    if not text:
        return []
    system = (
        "You extract skills from job postings for a labor-market analysis. List every skill the "
        "posting asks for, as a short noun phrase (2 to 6 words), with its category. Include "
        f"non-technical skills as well as technical ones. {IGNORE}\n\n{CATEGORY_HELP}"
    )
    reply = claude.ask(system=system, content=text[:MAX_TEXT_CHARS], schema=OPEN_SCHEMA, max_tokens=800)
    return reply["skills"]


def build_list(claude: Claude, counts: Counter, size: str = "40 to 60") -> list[dict]:
    """Group raw phrases (with how often each appeared) into one list of named, categorized skills."""
    lines = "\n".join(f"{n} | {category} | {phrase}" for (phrase, category), n in counts.most_common(400))
    system = (
        "You design a skill taxonomy for a labor-market analysis of data jobs. You get skill phrases "
        "extracted from job postings, with how many postings used each. Merge phrases that mean the "
        f"same thing into one skill, and return a list of {size} skills that covers the frequent "
        "phrases. Give each skill a clear name (2 to 6 words), one category, and a one-sentence "
        "definition that says what counts as this skill.\n\n" + CATEGORY_HELP
    )
    reply = claude.ask(system=system, content="count | category | phrase\n" + lines,
                       schema=LIST_SCHEMA, max_tokens=8000, effort="medium")
    return reply["skills"]


# ---------- Pass 2: tag postings against the list ----------

class SkillTagger:
    """Finds which skills from skills.yaml a posting asks for, and whether each is required."""

    def __init__(self, skills: list[dict], claude: Claude | None = None):
        self.skills = skills
        self.names = [s["skill"] for s in skills]
        self.claude = claude or Claude()

        by_category = []
        for category in CATEGORIES:
            lines = [f"- {s['skill']}: {s['definition']}" for s in skills if s["category"] == category]
            if lines:
                by_category.append(f"{category.capitalize()}:\n" + "\n".join(lines))
        self.system = (
            "You tag job postings for a labor-market analysis. From the skill list below, choose "
            "every skill the posting asks for, and mark each 'required', or 'preferred' when the "
            "posting calls it a plus, a bonus, nice to have or preferred. Choose a skill only if "
            "the posting asks for it; a passing mention is not enough.\n"
            f"Then list up to {MAX_OTHER} other skills the posting asks for that none of the listed "
            f"skills cover, as short noun phrases. {IGNORE}\n\n" + "\n\n".join(by_category)
        )
        self.schema = {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string", "enum": self.names},
                            "level": {"type": "string", "enum": LEVELS},
                        },
                        "required": ["skill", "level"],
                        "additionalProperties": False,
                    },
                },
                "other_skills": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["skills", "other_skills"],
            "additionalProperties": False,
        }

    @classmethod
    def from_yaml(cls, path: str | Path, **kwargs) -> "SkillTagger":
        return cls(yaml.safe_load(Path(path).read_text(encoding="utf-8")), **kwargs)

    def tag(self, text: str | None) -> tuple[dict[str, str], list[str]]:
        """Return ({skill: level}, [other skills]) for one posting."""
        if not text:
            return {}, []
        reply = self.claude.ask(system=self.system, content=text[:MAX_TEXT_CHARS],
                                schema=self.schema, max_tokens=1000)
        known = {n.lower(): n for n in self.names}
        found: dict[str, str] = {}
        for item in reply["skills"]:
            name = known.get(item["skill"].lower())
            if name and found.get(name) != "required":   # if listed twice, "required" wins
                found[name] = item["level"]
        other = []
        for phrase in reply["other_skills"]:
            phrase = " ".join(phrase.lower().split())
            if phrase and phrase not in other and phrase not in known:
                other.append(phrase)
        return found, other[:MAX_OTHER]
```

**The constants.** `CATEGORIES` and `LEVELS` are the only values allowed; the JSON schemas below use them as `enum`s, so the model can't invent a fifth category. `CATEGORY_HELP` and `IGNORE` are prompt text shared by both passes. `IGNORE` matters for postings like DoorDash's, where two-thirds of the text is benefits and legal notices.

**`Claude`** wraps the request settings from Module 10 (Haiku, low effort, thinking off, a JSON schema) and the token bookkeeping, so the three kinds of request below don't each repeat them. `ask(...)` sends one request and returns the parsed JSON. The `*` in `def ask(self, *, system, ...)` makes every argument after it **keyword-only**: you must write `ask(system=..., content=...)`, which keeps calls with several similar strings readable and hard to mix up.

**Pass 1: `extract_open` and `build_list`.**

- `OPEN_SCHEMA` asks for a list of `{name, category}` objects. The name is free text; only the category is fixed.
- `build_list` sends the phrases with their counts, one per line (`7 | communication | stakeholder management`), and asks for a merged list. `counts.most_common(400)` sends the 400 most frequent: rare phrases add tokens without changing the list. `effort="medium"` gives this one harder request a little more thought; it runs once, so the extra cost is a fraction of a cent.

**Pass 2: `SkillTagger`.**

- `__init__` builds the system prompt from `skills.yaml`, grouped by category with each skill's definition. The definitions are what make tagging consistent: "Presenting to leadership: explaining results and recommendations to senior stakeholders" tells the model where the line is.
- The schema has two keys. `skills` is a list of `{skill, level}` objects, where `skill` must be one of your names (`"enum": self.names`) and `level` must be `required` or `preferred`. `other_skills` is free text, for skills outside the list.
- `tag()` cleans the reply. `known` maps lowercase names to your exact names, so capitalization doesn't matter. If the model lists a skill twice, `required` wins. Other skills are lowercased, with extra spaces squeezed out (`" ".join(phrase.split())`), duplicates and already-listed skills dropped, and at most five kept. Lowercasing is what lets SQL count "Causal ML" and "causal ML" as one.
- It returns a tuple: a dict like `{"SQL": "required", "Mentoring": "preferred"}` and a list like `["marketplace analytics"]`.

### 12.3 Discover your skill list

Create `projects/linkedin_jobs/skill_discover.py`:

```python
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
    ap = argparse.ArgumentParser(description="Draft a skill list from a sample of postings")
    ap.add_argument("--sample", type=int, default=500, help="postings to read (default: 500)")
    ap.add_argument("--out", type=Path, default=HERE / "skills_draft.yaml")
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
    print(f"Reading {len(rows)} postings with {claude.model}", flush=True)

    counts: Counter = Counter()
    failed = 0
    for i, (title, description) in enumerate(rows, start=1):
        try:
            found = extract_open(claude, f"{title}\n\n{description}")
        except Exception as e:
            failed += 1
            print(f"  skipped one: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            continue
        # Count each phrase once per posting, so one wordy posting can't dominate.
        counts.update({(" ".join(s["name"].lower().split()), s["category"]) for s in found})
        if i % 50 == 0:
            print(f"  {i} read, ${claude.cost_usd:.3f} so far", flush=True)

    if not counts:
        print("No skills found; nothing written.", file=sys.stderr)
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
```

- It samples from `jobs.postings_dedup`, so a role reposted three times can't count three times. `order by random()` takes a random sample, so the list reflects the whole month rather than the newest postings.
- `counts.update({...})` adds a **set** of `(phrase, category)` pairs per posting. A set holds each pair once, so a posting that says "SQL" five times still counts once.
- It writes `skills_draft.yaml`, not `skills.yaml`, so it never overwrites a list you've already edited. `yaml.safe_dump(..., sort_keys=False)` keeps the keys in the order `skill, category, definition`.

**Checkpoint, a quick look (about $0.01):**

```bash
uv run python -m projects.linkedin_jobs.skill_discover --sample 20
```

Open `projects/linkedin_jobs/skills_draft.yaml`. With 20 postings the list is rough, but you'll see the shape:

```yaml
- skill: SQL
  category: technical
  definition: Writing queries to extract, join and transform data.
- skill: Presenting to leadership
  category: communication
  definition: Explaining findings and recommendations to senior stakeholders.
```

**Then the real run (about $0.15, a few minutes):**

```bash
uv run python -m projects.linkedin_jobs.skill_discover
```

**Review the draft. This is the step that matters most.** The list decides what gets measured, so spend 20 minutes on it:

- **Merge** near-duplicates the model kept apart ("Stakeholder management" and "Cross-functional collaboration" may be one skill for your purposes, or two).
- **Split** skills too broad to act on ("Statistics" might become "Hypothesis testing" and "Regression modeling").
- **Recategorize** where you disagree. The categories are yours, not the model's.
- **Sharpen definitions**: they're what the tagger reads when deciding.
- **Add** skills you care about that the sample missed, such as your own strengths, so you can see how much demand there is for them.

Save the result as `projects/linkedin_jobs/skills.yaml` and commit it. Delete the draft.

### 12.4 The tables: `sql/040_skills.sql`

**Add a column first.** In `sql/010_linkedin_jobs.sql`, right below Module 10's `themes_llm` line, add:

```sql
-- Module 12: skills found outside skills.yaml. NULL = skills not extracted yet.
alter table jobs.postings add column if not exists other_skills text[];
```

It goes in `010`, not in the new file, for the same reason as `themes_llm`: the views select `p.*`, and a column added after the views are built would be missing from them until the next migration.

Then create `sql/040_skills.sql`:

```sql
-- Module 12: skills by category. (The other_skills column on jobs.postings is added in
-- 010_linkedin_jobs.sql, before the views that select p.*, so the views include it.)

-- The skill list, copied from skills.yaml on every tagging run. Each skill's category lives here, once.
create table if not exists jobs.skills (
    skill      text primary key,
    category   text not null check (category in ('technical', 'communication', 'business', 'leadership')),
    definition text
);

-- One row per posting per skill it asks for.
create table if not exists jobs.posting_skills (
    job_id text not null references jobs.postings (job_id),
    skill  text not null references jobs.skills (skill),
    level  text not null check (level in ('required', 'preferred')),
    primary key (job_id, skill)
);

create index if not exists posting_skills_skill_idx on jobs.posting_skills (skill);

-- Skills per role (reposts collapsed), with the category attached. 010 drops this view
-- (cascade) whenever it rebuilds postings_dedup, so it is recreated here every time.
create or replace view jobs.role_skills as
select p.job_id, p.primary_industry, p.seniority_level, s.category, ps.skill, ps.level
from jobs.postings_dedup p
join jobs.posting_skills ps on ps.job_id = p.job_id
join jobs.skills s on s.skill = ps.skill;
```

This is a **dimension and fact** design, as in a Power BI model:

- `jobs.skills` is the dimension: one row per skill, holding its **category**. The category lives here once, not on every posting.
- `jobs.posting_skills` is the fact table: one row per posting per skill it asks for, with the level. Its primary key `(job_id, skill)` stops a skill being counted twice for one posting.
- The `references` clauses are foreign keys: Postgres refuses a `posting_skills` row for a job or skill that doesn't exist.
- `check (category in (...))` refuses any other category, so a typo in `skills.yaml` fails loudly instead of creating a fifth category.
- `jobs.role_skills` joins the three: one row per role per skill, with the category attached, and reposts collapsed through `postings_dedup`.

Because the category sits in `jobs.skills`, recategorizing is cheap: change one line in `skills.yaml`, and the next tagging run updates `jobs.skills`. Every chart follows, and nothing is re-tagged.

This is also why the dashboard's grants file is numbered `900` (Module 11): it runs after `040`, so the read-only user can read the new tables and view.

Apply it:

```bash
uv run python -m core.db
```

### 12.5 Tag your postings: `skill_tag.py`

Create `projects/linkedin_jobs/skill_tag.py`:

```python
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


def sync_skills(conn: psycopg.Connection, skills: list[dict]) -> None:
    """Make jobs.skills match skills.yaml: add new skills, update categories, remove deleted ones."""
    names = [s["skill"] for s in skills]
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
    ap = argparse.ArgumentParser(description="Tag postings with skills from skills.yaml")
    ap.add_argument("--limit", type=int, help="tag at most this many postings (default: all)")
    ap.add_argument("--retag", metavar="TEXT", help="first mark postings whose description mentions TEXT as untagged")
    ap.add_argument("--retag-all", action="store_true", help="first mark every posting as untagged")
    args = ap.parse_args(argv)

    path = HERE / "skills.yaml"
    if not path.exists():
        print("No skills.yaml yet. Run skill_discover, review skills_draft.yaml, then save it as skills.yaml.",
              file=sys.stderr)
        return 1
    tagger = SkillTagger.from_yaml(path)

    with db.connect() as conn:
        sync_skills(conn, tagger.skills)
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
        print(f"{len(rows)} postings to tag against {len(tagger.names)} skills with {tagger.claude.model}",
              flush=True)

        done, failed, in_a_row = 0, 0, 0
        for job_id, title, description in rows:
            try:
                found, other = tagger.tag(f"{title}\n\n{description}")
            except Exception as e:
                failed += 1
                in_a_row += 1
                print(f"  {job_id}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
                if in_a_row >= MAX_FAILURES_IN_A_ROW:
                    print("Stopping: too many failures in a row.", file=sys.stderr)
                    break
                continue
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
```

- **`sync_skills`** makes the database match `skills.yaml` at the start of every run. The upsert adds new skills and updates categories and definitions (`excluded.` is the incoming row, as in Module 5). Then `skill <> all(%s)` ("not equal to every name in the list") deletes skills you removed from the YAML, first from `posting_skills` because of the foreign key, then from `skills`.
- **What's left to tag** is every posting where `other_skills is null`, the same `NULL` means "not yet" pattern as Module 10. Each tagged posting gets a list, even an empty `'{}'`, so it isn't tagged again.
- **Writing one posting:** delete its old skill rows, insert the new ones with `executemany`, and store `other_skills`. Deleting first is what makes re-tagging safe.
- **`--retag TEXT`** sets `other_skills` back to `NULL` for postings whose description contains the text (`ilike` is a case-insensitive `like`; `%` matches anything). `--retag-all` does it for every posting. The tagging loop then picks them up as usual.
- Failures, commits every 50 and the cost line work exactly as in Module 10.

**Checkpoint, a small run (about $0.005):**

```bash
uv run python -m projects.linkedin_jobs.skill_tag --limit 10
```

Then look at what it found, in the SQL Editor:

```sql
select p.title, s.category, ps.skill, ps.level
from jobs.posting_skills ps
join jobs.skills s using (skill)
join jobs.postings p using (job_id)
order by p.title, s.category, ps.skill;
```

**Spot-check before trusting the numbers.** Open three or four of those postings and compare. If the tagger keeps missing a skill or over-applying one, sharpen that skill's definition in `skills.yaml` and re-run with `--retag-all --limit 10`. When you're happy, tag everything:

```bash
uv run python -m projects.linkedin_jobs.skill_tag
```

### 12.6 The statistics

Skill share by category, across everything tagged:

```sql
select s.category, s.skill,
       count(rs.job_id) as roles,
       round(100.0 * count(rs.job_id) / (select count(*) from jobs.postings_dedup where other_skills is not null), 1) as pct,
       round(100.0 * count(rs.job_id) filter (where rs.level = 'required')
             / nullif(count(rs.job_id), 0), 0) as pct_of_mentions_required
from jobs.skills s
left join jobs.role_skills rs using (skill)
group by s.category, s.skill
order by s.category, roles desc;
```

The `left join` keeps skills that no role asked for, with 0, which is a finding too. The denominator counts only **tagged** roles, so the shares are right even while tagging is half done.

Other questions the same tables answer:

```sql
-- What do senior roles ask for more than others?
select skill, seniority_level, count(*) from jobs.role_skills group by 1, 2 order by 1, 2;

-- Emerging: skills outside your list, most frequent first
select o.phrase, count(*) as roles
from jobs.postings_dedup p
cross join lateral unnest(p.other_skills) as o(phrase)
group by o.phrase
order by roles desc
limit 25;
```

### 12.7 On the dashboard

Create `projects/linkedin_jobs/skill_queries.py`:

```python
"""SQL behind the dashboard's skills section (Module 12). Same filters as queries.py."""

from datetime import date

import psycopg

from projects.linkedin_jobs.queries import ROLES, _rows


def has_skills(conn: psycopg.Connection) -> bool:
    """True once Module 12 is set up and at least one posting has been tagged."""
    if conn.execute("select to_regclass('jobs.role_skills')").fetchone()[0] is None:
        return False
    return conn.execute("select exists (select 1 from jobs.posting_skills)").fetchone()[0]


def skills_dashboard(conn: psycopg.Connection, terms: list[str], start: date, end: date,
                     min_mentions: int = 3) -> dict:
    f = {"terms": terms, "start": start, "end": end, "min": min_mentions}

    # Share of tagged roles asking for each skill, split into required and preferred.
    skills = _rows(conn, f"""
        with roles as ({ROLES} and p.other_skills is not null),
        total as (select count(*) as n from roles)
        select s.category, s.skill,
               count(rs.job_id) as roles,
               round(100.0 * count(rs.job_id) / nullif(total.n, 0), 1)::float as pct,
               round(100.0 * count(rs.job_id) filter (where rs.level = 'required')
                     / nullif(total.n, 0), 1)::float as pct_required
        from jobs.skills s
        cross join total
        left join jobs.role_skills rs
               on rs.skill = s.skill and rs.job_id in (select job_id from roles)
        group by s.category, s.skill, total.n
        order by s.category, roles desc, s.skill
    """, f)

    # Skills found outside the list, most frequent first: candidates for skills.yaml.
    emerging = _rows(conn, f"""
        with roles as ({ROLES})
        select o.phrase, count(*) as roles
        from roles r
        cross join lateral unnest(r.other_skills) as o(phrase)
        group by o.phrase
        having count(*) >= %(min)s
        order by roles desc, o.phrase
        limit 25
    """, f)

    tagged = _rows(conn, f"with roles as ({ROLES}) select count(*) filter (where other_skills is not null) as n "
                         "from roles", f)[0]["n"]
    return {"skills": skills, "emerging": emerging, "tagged_roles": tagged}
```

- It imports `ROLES` and `_rows` from `queries.py`, so the skills section filters exactly like the rest of the dashboard. The underscore in `_rows` means "internal to this project", and this file is part of the same project.
- `has_skills` returns `False` until Module 12 is set up: `to_regclass('jobs.role_skills')` returns `NULL` when the view doesn't exist. That keeps the dashboard working for anyone who skips this module.
- In `skills_dashboard`, `cross join total` attaches the total number of tagged roles to every row, for the percentage. `filter (where rs.level = 'required')` counts only the required mentions. Emerging skills need at least `min_mentions` roles (3 by default), so one-off phrases don't clutter the list.

Create `projects/linkedin_jobs/app_skills.py`:

```python
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
```

- `show()` draws the whole section, so `app.py` only needs one new line to call it.
- `st.tabs([...])` creates a tab per category and returns one container per tab; `with tab:` puts the chart inside it. `zip(tabs, CATEGORIES)` pairs each tab with its category.
- The "Skills I already have" box works like "Themes I already cover": anything you don't tick is a gap. The tooltip shows how often each skill is *required*, which separates must-haves from nice-to-haves.

Now the two-line change to `app.py`. Change the import line to:

```python
from projects.linkedin_jobs import app_skills, queries
```

and add this just above the `# ---------- Who is hiring ----------` line:

```python
# ---------- Skills by category (Module 12) ----------
app_skills.show(terms, start, end)
```

**Checkpoint:** run the app (`uv run streamlit run projects/linkedin_jobs/app.py`). Below the themes chart there's a **Skills by category** section with four tabs, and an **Emerging skills** table. If it doesn't appear, the dashboard's 1-hour cache may still say "no skills yet": use ⋮ → **Clear cache**.

### 12.8 Tests, automation and cost

Create `tests/fixtures/skills.yaml`, a small list the tests use instead of your real one:

```yaml
# A small skill list for the tests (Module 12).
- skill: Python
  category: technical
  definition: Writing Python for analysis, modeling or production.
- skill: SQL
  category: technical
  definition: Querying and shaping data with SQL.
- skill: A/B testing
  category: technical
  definition: Designing and analyzing controlled experiments.
- skill: Presenting to leadership
  category: communication
  definition: Explaining results and recommendations to senior stakeholders.
- skill: Metric definition and KPI design
  category: business
  definition: Choosing and defining the metrics that measure success.
- skill: Mentoring
  category: leadership
  definition: Coaching and developing other analysts or scientists.
```

Create `tests/test_skills.py`:

```python
"""Tests for skills by category (Module 12). No API calls: a fake client stands in."""
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


DB = os.environ.get("TEST_DB_URL")


@pytest.mark.skipif(not DB, reason="set TEST_DB_URL to a throwaway Postgres to run")
def test_skill_tag_script_and_queries(monkeypatch, tmp_path):
    import psycopg
    import yaml

    from core import db
    from core.text import ThemeTagger
    from projects.linkedin_jobs import load, skill_queries, skill_tag
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

        d = skill_queries.skills_dashboard(conn, ["data scientist"], date(2026, 10, 1), date(2026, 10, 1), 2)
        sql = next(r for r in d["skills"] if r["skill"] == "SQL")
        assert (sql["category"], sql["roles"], sql["pct"], sql["pct_required"]) == ("technical", 2, 100.0, 100.0)
        mentoring = next(r for r in d["skills"] if r["skill"] == "Mentoring")
        assert (mentoring["category"], mentoring["pct_required"]) == ("leadership", 0.0)
        assert d["emerging"] == [{"phrase": "marketplace analytics", "roles": 2}]
        assert d["tagged_roles"] == 2

    # The dashboard shows the new section (after the two-line change to app.py)
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    st.cache_data.clear()  # an earlier test may have cached "no skills yet"
    at = AppTest.from_file(str(ROOT / "projects/linkedin_jobs/app.py"), default_timeout=30).run()
    assert not at.exception
    assert "Skills by category" in [h.value for h in at.subheader]
    assert [t.label for t in at.tabs] == ["Technical", "Communication", "Business", "Leadership"]

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
```

- `FakeMessages` now takes several replies and returns them in turn, because discovery makes two kinds of request.
- `test_tag_cleans_the_reply` feeds in a messy reply (a duplicate, an unknown skill, odd spacing) and checks what comes out.
- The database test runs `skill_tag.main()` for real against the throwaway database, with a fake model. It points the script at a temporary folder with `monkeypatch.setattr(skill_tag, "HERE", tmp_path)`; `tmp_path` is a fresh empty folder pytest creates for each test. It checks the counts and percentages, that reposts are collapsed, that the dashboard section appears, and that recategorizing and deleting skills in the YAML work without re-tagging.
- `st.cache_data.clear()` empties Streamlit's cache first, since an earlier test may have cached "no skills yet".

**Run in the terminal:** `uv run pytest -v`. **Checkpoint:** `12 passed, 10 skipped` locally; all 22 pass on GitHub.

**Automate it.** `skills.yaml` must be committed, because GitHub's runner only has what's in the repo. Then add this step to the end of `.github/workflows/linkedin-jobs.yml`, after Module 10's step:

```yaml
      - name: Tag skills
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
        run: uv run --no-dev python -m projects.linkedin_jobs.skill_tag
```

**What it costs.** Tagging sends the skill list with every posting, so it costs more per posting than Module 10:

| Part | Tokens per posting |
| --- | --- |
| Instructions and a 50-skill list with definitions | ~1,800 in |
| Job title and description | ~1,000 in, typically |
| JSON format instructions | ~200 in (estimate) |
| Answer: about 15 skills plus a few others | ~300 out |
| **Total** | **~3,000 in, ~300 out** |

That's 3,000 × $0.10 / 1M + 300 × $0.50 / 1M ≈ **$0.00045 per posting**:

| Job | Cost |
| --- | --- |
| Discovery: 500 postings plus one grouping request | ~$0.15, each time you run it |
| Tagging the 5,000 postings you already have | ~$2.25, once |
| Each month after: ~5,000 new postings | ~$2.25 |
| Adding a skill and re-tagging the postings that mention it (`--retag`) | Usually a few cents |

As in Module 10, the script prints the real cost. Run `--limit 10` first and scale up from it. If the cost ever matters, the Batch API halves it.

**Commit:**

```bash
git add .
git commit -m "Module 12: skills by category"
git push
```

### 12.9 When a new skill appears

Nothing new is lost. A skill that isn't on your list lands in `other_skills`, in the posting's own words, and shows up in the dashboard's **Emerging skills** table once three or more roles mention it. When a phrase there looks real and keeps growing:

1. **Add it to `skills.yaml`**, with a category and a clear definition.
2. **Re-tag the postings that likely mention it**, so it's counted in past months too:

```bash
uv run python -m projects.linkedin_jobs.skill_tag --retag "agent"
```

That re-tags only postings whose description contains "agent", usually a few hundred, for a few cents. The descriptions are already stored, so the new skill's history starts with your first month of data, not the day you added it. If a change affects many skills, use `--retag-all` instead (about $2.25 per 5,000 postings).

Every few months, re-run `skill_discover` and compare the draft with your list. It's a quick way to catch shifts you haven't noticed in the emerging table.

### Check your understanding

1. Why does each skill's category live in `jobs.skills` and not on each `posting_skills` row?
2. What does `other_skills is null` mean, and how is that different from `'{}'`?
3. Why does discovery use a random sample from `postings_dedup` rather than the newest postings?
4. You add "AI agent evaluation" to `skills.yaml`. What two things happen on the next `skill_tag --retag "agent"` run?

<details>
<summary>Answers</summary>

1. So a category is stored once. Changing it means editing one line in `skills.yaml`, and the next run updates one row; with the category on every posting row, the same change would mean updating thousands of rows, or re-tagging.
2. `NULL` means the posting hasn't been tagged yet, so the next run will tag it. `'{}'` means it was tagged and asked for nothing beyond your list, so it won't be tagged again.
3. Random sampling represents the whole period rather than just the latest few days, and `postings_dedup` stops a role reposted several times from counting several times.
4. `sync_skills` adds the new skill to `jobs.skills`. Then every posting whose description contains "agent" is marked untagged and tagged again against the updated list, so the new skill is counted in past months too.

</details>

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
| Tag new postings with the LLM (Module 10) | `uv run python -m projects.linkedin_jobs.llm_tag` |
| Start the dashboard (Module 11) | `uv run streamlit run projects/linkedin_jobs/app.py` |
| Draft a skill list (Module 12) | `uv run python -m projects.linkedin_jobs.skill_discover` |
| Tag new postings with skills (Module 12) | `uv run python -m projects.linkedin_jobs.skill_tag` |
| Re-tag postings mentioning a word (Module 12) | `uv run python -m projects.linkedin_jobs.skill_tag --retag "word"` |
| Run tests | `uv run pytest -v` |
| Add a package | `uv add <package>` (then commit `pyproject.toml` and `uv.lock`) |
| Upgrade all packages | `uv lock --upgrade`, then `uv run pytest`, then commit |

Monthly running cost: $0 with `limit_per_search: 500` on Apify's free plan, or $19 on Apify Starter for the full 5,000. Supabase, GitHub Actions and uv are free at this scale. The optional LLM tagging (Module 10) adds about $1 a month at 5,000 postings. The dashboard (Module 11) is free on Streamlit Community Cloud. Skills by category (Module 12) adds about $2 a month at 5,000 postings.
