import json
import logging
import os
from typing import Any, Dict, List
import psycopg
from dotenv import load_dotenv

from script.ingestion import ingest_all

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("MainPipeline")


def ensure_table(conn: psycopg.Connection) -> None:
    """Create target ingestion table if it does not exist."""
    query = """
    CREATE TABLE IF NOT EXISTS ingested_records (
        source TEXT NOT NULL,
        item_id TEXT NOT NULL,
        metrics JSONB NOT NULL,
        ingested_at TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (source, item_id)
    );
    """
    with conn.cursor() as cur:
        cur.execute(query)
    conn.commit()


def save_records(conn: psycopg.Connection, records: List[Dict[str, Any]]) -> None:
    """Upsert normalized records into PostgreSQL."""
    if not records:
        logger.info("No records to save.")
        return

    query = """
    INSERT INTO ingested_records (source, item_id, metrics)
    VALUES (%s, %s, %s::jsonb)
    ON CONFLICT (source, item_id)
    DO UPDATE SET
        metrics = EXCLUDED.metrics,
        ingested_at = NOW();
    """
    rows = [
        (rec["source"], str(rec["item_id"]), json.dumps(rec.get("metrics", {})))
        for rec in records
    ]

    with conn.cursor() as cur:
        cur.executemany(query, rows)
    conn.commit()
    logger.info(f"Saved {len(rows)} records to PostgreSQL.")


def get_db_dsn() -> str:
    """Build PostgreSQL connection string from environment variables."""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    dbname = os.getenv("PGDATABASE", "ingestion_db")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def main() -> None:
    """Run ingestion across sources and persist results."""
    tasks = {
        "client_a": ["101", "102"],
        "client_b": ["201", "202"],
    }

    records = ingest_all(tasks=tasks, ignore_errors=True)
    logger.info(f"Total extracted records: {len(records)}")

    with psycopg.connect(get_db_dsn()) as conn:
        ensure_table(conn)
        save_records(conn, records)


if __name__ == "__main__":
    main()
