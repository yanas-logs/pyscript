from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseIngestionClient(ABC):
    """Abstract base class defining the standard interface for all data clients."""

    def __init__(self, source_alias: str, base_url: str) -> None:
        self.source_alias = source_alias
        self.base_url = base_url

    @abstractmethod
    def extract(self, target_ids: List[Any]) -> List[Dict[str, Any]]:
        """
        Execute data extraction for a list of target identifiers.

        Args:
            target_ids: List of item IDs, queries, or parameters to fetch.

        Returns:
            List of standardized dictionary records.
        """
        pass
