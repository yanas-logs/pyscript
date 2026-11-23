import logging
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from script.ingestion.clients import BaseIngestionClient, ClientA, ClientB

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger("IngestionManager")


def get_client(
    source_name: str, config: Optional[Dict[str, Any]] = None
) -> BaseIngestionClient:
    """Instantiate a client by source name using config or env vars."""
    cfg = config or {}
    source_key = source_name.lower().strip()

    if source_key == "client_a":
        return ClientA(
            source_alias=cfg.get("source_alias", "source_a"),
            base_url=cfg.get("base_url") or os.getenv("CLIENT_A_BASE_URL", "https://api.source-a.com/v1/items"),
            auth_url=cfg.get("auth_url") or os.getenv("CLIENT_A_AUTH_URL", "https://api.source-a.com/oauth/token"),
            client_id=cfg.get("client_id") or os.getenv("CLIENT_A_ID", ""),
            client_secret=cfg.get("client_secret") or os.getenv("CLIENT_A_SECRET", ""),
            max_calls_per_sec=cfg.get("max_calls_per_sec", 10),
        )

    if source_key == "client_b":
        return ClientB(
            source_alias=cfg.get("source_alias", "source_b"),
            base_url=cfg.get("base_url") or os.getenv("CLIENT_B_BASE_URL", "https://api.source-b.com/v1/records"),
            api_key=cfg.get("api_key") or os.getenv("CLIENT_B_API_KEY", ""),
            api_key_header=cfg.get("api_key_header", "X-API-Key"),
            max_calls_per_sec=cfg.get("max_calls_per_sec", 5),
        )

    raise ValueError(f"Unknown source '{source_name}'. Valid options: ['client_a', 'client_b']")


def ingest_from_source(
    source_name: str,
    target_ids: List[Any],
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Extract records from a single data source."""
    if not target_ids:
        logger.warning(f"[{source_name}] Empty target_ids, skipping.")
        return []

    client = get_client(source_name, config=config)
    return client.extract(target_ids)


def ingest_all(
    tasks: Dict[str, List[Any]],
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ignore_errors: bool = False,
) -> List[Dict[str, Any]]:
    """Extract and combine records across multiple sources."""
    all_records: List[Dict[str, Any]] = []
    configs = configs or {}

    for source_name, target_ids in tasks.items():
        try:
            records = ingest_from_source(
                source_name=source_name,
                target_ids=target_ids,
                config=configs.get(source_name),
            )
            all_records.extend(records)
        except Exception as exc:
            logger.error(f"Failed to ingest from '{source_name}': {exc}")
            if not ignore_errors:
                raise

    return all_records
