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
