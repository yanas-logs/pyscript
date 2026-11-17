import logging
from typing import Any, Dict, List, Optional
import requests

from script.ingestion.clients.base import BaseIngestionClient
from script.ingestion.utils import RateLimiter, retry_with_backoff

logger = logging.getLogger("ClientB")


class ClientB(BaseIngestionClient):
    """Ingestion client for API Key-authenticated REST APIs with rate limiting."""

    def __init__(
        self,
        source_alias: str,
        base_url: str,
        api_key: str,
        api_key_header: str = "X-API-Key",
        max_calls_per_sec: int = 5,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(source_alias, base_url.rstrip("/"))
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.timeout = timeout

        self.rate_limiter = RateLimiter(max_calls=max_calls_per_sec, period=1.0)

        self.session = requests.Session()
        self.session.headers.update(
            {
                self.api_key_header: self.api_key,
                "Accept": "application/json",
            }
        )

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.5,
        exceptions=(requests.RequestException, TimeoutError),
    )
    def _fetch_single(self, item_id: str) -> Dict[str, Any]:
        """Fetch and normalize a single resource record with rate limiting."""
        
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}/{item_id}"
        logger.debug(f"[{self.source_alias}] Fetching URL: {url}")

        # response = self.session.get(url, timeout=self.timeout)
        # response.raise_for_status()
        # raw_data = response.json()
        # return self._normalize(item_id, raw_data)

        # --- MOCK DATA ---
        return {
            "source": self.source_alias,
            "item_id": item_id,
            "metrics": {
                "score": 92,
                "attribute_1": 0.81,
            },
        }

    def _normalize(self, item_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map raw API response fields into the standardized ingestion schema."""
        return {
            "source": self.source_alias,
            "item_id": item_id,
            "metrics": {
                "score": raw_data.get("rating", 0),
                "attribute_1": raw_data.get("confidence", 0.0),
            },
        }

    def extract(self, target_ids: List[Any]) -> List[Dict[str, Any]]:
        """Execute extraction for all target IDs sequentially with rate limiting."""
        logger.info(
            f"[{self.source_alias}] Extracting {len(target_ids)} items via API Key..."
        )
        results: List[Dict[str, Any]] = []

        for tid in target_ids:
            record = self._fetch_single(str(tid))
            results.append(record)

        logger.info(
            f"[{self.source_alias}] Successfully extracted {len(results)} records."
        )
        return results
