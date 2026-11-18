import logging
from typing import Any, Dict, List
import requests

from script.ingestion.clients.base import BaseIngestionClient
from script.ingestion.utils import RateLimiter, retry_with_backoff

logger = logging.getLogger("ClientA")


class ClientA(BaseIngestionClient):
    """Ingestion client for OAuth2-authenticated REST APIs using requests.Session."""

    def __init__(
        self,
        source_alias: str,
        base_url: str,
        auth_url: str,
        client_id: str,
        client_secret: str,
        max_calls_per_sec: int = 10,
        timeout: float = 10.0,
    ) -> None:
        super().__init__(source_alias, base_url.rstrip("/"))
        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout

        # Inisialization RateLimiter and Session HTTP
        self.rate_limiter = RateLimiter(max_calls=max_calls_per_sec, period=1.0)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        # Auth and placing token to header Session
        self.token = self._authenticate()
        self._update_auth_header(self.token)

    def _update_auth_header(self, token: str) -> None:
        """Update Authorization Bearer header on the active HTTP session."""
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(requests.RequestException, TimeoutError),
    )
    def _authenticate(self) -> str:
        """Obtain bearer token from the configured OAuth2 endpoint."""
        logger.info(f"[{self.source_alias}] Authenticating via OAuth2...")

        # --- IMPLEMENTATION (When endpoint OAuth2 ready) ---
        # payload = {
        #     "grant_type": "client_credentials",
        #     "client_id": self.client_id,
        #     "client_secret": self.client_secret,
        # }
        # response = self.session.post(
        #     self.auth_url, data=payload, timeout=self.timeout
        # )
        # response.raise_for_status()
        # return response.json()["access_token"]

        # --- MOCK TOKEN ---
        return "abstract_bearer_token"

    @retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        exceptions=(requests.RequestException, TimeoutError),
    )
    def _fetch_single(self, item_id: str) -> Dict[str, Any]:
        """Fetch a single resource record from the target endpoint."""
        self.rate_limiter.wait_if_needed()

        url = f"{self.base_url}/{item_id}"
        logger.debug(f"[{self.source_alias}] Fetching URL: {url}")

        # --- IMPLEMENTATION (When endpoint API ready) ---
        # response = self.session.get(url, timeout=self.timeout)
        #
        # # Auto-refresh token (HTTP 401 Unauthorized)
        # if response.status_code == 401:
        #     logger.warning(f"[{self.source_alias}] Token expired (401). Refreshing...")
        #     self.token = self._authenticate()
        #     self._update_auth_header(self.token)
        #     response = self.session.get(url, timeout=self.timeout)
        #
        # response.raise_for_status()
        # raw_data = response.json()
        # return self._normalize(item_id, raw_data)

        # --- MOCK DATA ---
        return {
            "source": self.source_alias,
            "item_id": item_id,
            "metrics": {"score": 85, "attribute_1": 0.74},
        }

    def _normalize(self, item_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map raw API response fields into the standardized ingestion schema."""
        return {
            "source": self.source_alias,
            "item_id": item_id,
            "metrics": {
                "score": raw_data.get("score", 0),
                "attribute_1": raw_data.get("attribute_1", 0.0),
            },
        }

    def extract(self, target_ids: List[Any]) -> List[Dict[str, Any]]:
        """Execute extraction for all target IDs."""
        logger.info(f"[{self.source_alias}] Extracting {len(target_ids)} items...")
        return [self._fetch_single(str(tid)) for tid in target_ids]
