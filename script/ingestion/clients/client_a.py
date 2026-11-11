import logging
from typing import List, Dict, Any
from script.ingestion.clients.base import BaseIngestionClient
from script.ingestion.utils import retry_with_backoff

logger = logging.getLogger("ClientA")


class ClientA(BaseIngestionClient):
    """Generic ingestion client for OAuth2-authenticated REST APIs."""

    def __init__(
        self,
        source_alias: str,
        base_url: str,
        auth_url: str,
        client_id: str,
        client_secret: str
    ) -> None:
        super().__init__(source_alias, base_url)
        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = self._authenticate()

    def _authenticate(self) -> str:
        """Obtain bearer token from the configured OAuth2 endpoint."""
        logger.info(f"[{self.source_alias}] Authenticating via OAuth2...")
        # TODO: Implement requests.post(self.auth_url, ...)
        return "abstract_bearer_token"

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def _fetch_single(self, item_id: str) -> Dict[str, Any]:
        """Fetch a single resource record from the target endpoint."""
        # TODO: Implement requests.get(f"{self.base_url}/{item_id}", headers=...)
        return {
            "source": self.source_alias,
            "item_id": item_id,
            "metrics": {"score": 85, "attribute_1": 0.74}
        }

    def extract(self, target_ids: List[Any]) -> List[Dict[str, Any]]:
        logger.info(f"[{self.source_alias}] Extracting {len(target_ids)} items...")
        return [self._fetch_single(str(tid)) for tid in target_ids]
