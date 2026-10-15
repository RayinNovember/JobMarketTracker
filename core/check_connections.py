"""One-off check that Apify and Supabase both accept our credentials."""
import psycopg
from apify_client import ApifyClient

from core import settings

# Apify
apify = ApifyClient(token=settings.get("APIFY_TOKEN"))
me = apify.user().get()
print(f"Apify     OK, signed in as {me.username}")

# Supabase: ask the database for its version
with psycopg.connect(settings.get("SUPABASE_DB_URL"), connect_timeout=30) as conn:
    version = conn.execute('select version()').fetchone()[0]
print(f"Supabase  OK, version {version}")