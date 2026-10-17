from pathlib import Path

import psycopg

from core import settings

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

def connect() -> psycopg.Connection:
    """Connect to the Supabase database using our URL from settings."""
    return psycopg.connect(
        settings.get("SUPABASE_DB_URL"), connect_timeout=30, prepare_threshold=None
    )

def migrate(conn: psycopg.Connection) -> list[str]:
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


