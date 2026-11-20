import time
from unittest.mock import MagicMock, patch
import pytest
import requests

from script.ingestion import (
    ClientA,
    ClientB,
    get_client,
    ingest_all,
    ingest_from_source,
)
from script.ingestion.utils import RateLimiter, retry_with_backoff

# Utils Tests: RateLimiter & retry_with_backoff
def test_rate_limiter_enforces_delay():
    """Verify RateLimiter sleeps when max_calls within period is exceeded."""
    limiter = RateLimiter(max_calls=2, period=0.3)

    start = time.monotonic()
    limiter.wait_if_needed()
    limiter.wait_if_needed()
    limiter.wait_if_needed()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.25


def test_retry_with_backoff_succeeds_after_transient_failures():
    """Verify decorator retries on specified exceptions and returns result."""
    mock_fn = MagicMock(side_effect=[ValueError("fail 1"), ValueError("fail 2"), "ok"])

    @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
    def flaky_call():
        return mock_fn()

    assert flaky_call() == "ok"
    assert mock_fn.call_count == 3


def test_retry_with_backoff_raises_after_max_retries():
    """Verify original exception is raised once max_retries is exhausted."""
    mock_fn = MagicMock(side_effect=ConnectionError("network down"))

    @retry_with_backoff(max_retries=2, base_delay=0.01, exceptions=(ConnectionError,))
    def broken_call():
        return mock_fn()

    with pytest.raises(ConnectionError):
        broken_call()

    assert mock_fn.call_count == 3

# ClientA Tests
def test_client_a_initialization_sets_bearer_header():
    """Verify ClientA authenticates on init and attaches Bearer token."""
    client = ClientA(
        source_alias="source_a",
        base_url="https://api.example.com/v1/",
        auth_url="https://api.example.com/oauth/token",
        client_id="test_id",
        client_secret="test_secret",
    )

    assert client.base_url == "https://api.example.com/v1"
    assert client.session.headers["Authorization"] == "Bearer abstract_bearer_token"


def test_client_a_extract_returns_standardized_records():
    """Verify ClientA extracts and formats records for all target IDs."""
    client = ClientA(
        source_alias="source_a",
        base_url="https://api.example.com/v1",
        auth_url="https://api.example.com/oauth/token",
        client_id="test_id",
        client_secret="test_secret",
    )

    records = client.extract(["101", "102"])

    assert len(records) == 2
    assert records[0] == {
        "source": "source_a",
        "item_id": "101",
        "metrics": {"score": 85, "attribute_1": 0.74},
    }
    assert records[1]["item_id"] == "102"


def test_client_a_normalize_maps_fields():
    """Verify _normalize transforms raw API payload into standard schema."""
    client = ClientA(
        source_alias="source_a",
        base_url="https://api.example.com",
        auth_url="https://api.example.com/auth",
        client_id="id",
        client_secret="secret",
    )

    normalized = client._normalize("55", {"score": 99, "attribute_1": 0.95})

    assert normalized == {
        "source": "source_a",
        "item_id": "55",
        "metrics": {"score": 99, "attribute_1": 0.95},
    }

# ClientB Tests
def test_client_b_initialization_sets_api_key_header():
    """Verify ClientB sets custom API key header on session."""
    client = ClientB(
        source_alias="source_b",
        base_url="https://api.source-b.com/items/",
        api_key="my_secret_key",
        api_key_header="X-Custom-Key",
    )

    assert client.base_url == "https://api.source-b.com/items"
    assert client.session.headers["X-Custom-Key"] == "my_secret_key"


def test_client_b_extract_calls_rate_limiter():
    """Verify ClientB invokes RateLimiter for each extracted item."""
    client = ClientB(
        source_alias="source_b",
        base_url="https://api.source-b.com/items",
        api_key="my_secret_key",
    )

    with patch.object(client.rate_limiter, "wait_if_needed") as mock_wait:
        records = client.extract(["A1", "A2", "A3"])

    assert len(records) == 3
    assert mock_wait.call_count == 3
    assert records[0]["source"] == "source_b"
    assert records[0]["metrics"]["score"] == 92


def test_client_b_normalize_maps_fields():
    """Verify ClientB maps rating/confidence fields to score/attribute_1."""
    client = ClientB(
        source_alias="source_b",
        base_url="https://api.source-b.com",
        api_key="key",
    )

    normalized = client._normalize("SKU-1", {"rating": 88, "confidence": 0.65})

    assert normalized == {
        "source": "source_b",
        "item_id": "SKU-1",
        "metrics": {"score": 88, "attribute_1": 0.65},
    }

# Ingestion Orchestrator Tests: get_client, ingest_from_source, ingest_all
def test_get_client_factory():
    """Verify factory instantiates correct client classes and rejects unknown ones."""
    client_a = get_client("client_a", config={"client_id": "id", "client_secret": "sec"})
    client_b = get_client("CLIENT_B", config={"api_key": "key"})

    assert isinstance(client_a, ClientA)
    assert isinstance(client_b, ClientB)

    with pytest.raises(ValueError, match="Unknown source"):
        get_client("client_unknown")


def test_ingest_from_source_skips_empty_ids():
    """Verify empty target_ids returns an empty list without instantiating a client."""
    with patch("script.ingestion.ingestion.get_client") as mock_get_client:
        result = ingest_from_source("client_a", target_ids=[])

    assert result == []
    mock_get_client.assert_not_called()


def test_ingest_all_combines_multiple_sources():
    """Verify ingest_all aggregates records from both ClientA and ClientB."""
    tasks = {
        "client_a": ["10", "20"],
        "client_b": ["X1"],
    }
    configs = {
        "client_a": {"source_alias": "alpha"},
        "client_b": {"source_alias": "beta", "api_key": "secret"},
    }

    results = ingest_all(tasks=tasks, configs=configs)

    assert len(results) == 3
    sources = [r["source"] for r in results]
    assert sources == ["alpha", "alpha", "beta"]


def test_ingest_all_error_handling():
    """Verify ignore_errors flag controls whether failures propagate."""
    tasks = {
        "client_a": ["1"],
        "client_b": ["2"],
    }

    with patch("script.ingestion.ingestion.ingest_from_source") as mock_ingest:
        mock_ingest.side_effect = [
            requests.HTTPError("500 Server Error"),
            [{"source": "source_b", "item_id": "2", "metrics": {}}],
        ]

        results = ingest_all(tasks=tasks, ignore_errors=True)
        assert len(results) == 1
        assert results[0]["item_id"] == "2"

        mock_ingest.side_effect = requests.HTTPError("500 Server Error")
        with pytest.raises(requests.HTTPError):
            ingest_all(tasks=tasks, ignore_errors=False)
