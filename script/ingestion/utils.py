import functools
import logging
import random
import time
from typing import Any, Callable, List, Tuple, Type

logger = logging.getLogger("IngestionUtils")


class RateLimiter:
    """Thread-safe sliding window rate limiter to prevent API throttling."""

    def __init__(self, max_calls: int, period: float = 1.0) -> None:
        self.max_calls = max_calls
        self.period = period
        self.calls: List[float] = []

    def wait_if_needed(self) -> None:
        """Pause execution if the maximum number of calls in the current period is reached."""
        now = time.monotonic()
        self.calls = [t for t in self.calls if now - t < self.period]

        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls)
            if sleep_time > 0:
                logger.debug(
                    f"Rate limit reached. Sleeping for {sleep_time:.2f}s..."
                )
                time.sleep(sleep_time)

        self.calls.append(time.monotonic())


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator that retries a function using exponential backoff with jitter.

    Args:
        max_retries: Maximum number of retry attempts before raising the
          exception.
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Maximum upper bound for delay in seconds.
        exceptions: Tuple of exception classes that trigger a retry.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    if attempt > max_retries:
                        logger.error(
                            f"[{func.__name__}] Max retries ({max_retries}) exceeded."
                        )
                        raise exc

                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    jitter = random.uniform(0, 0.5 * delay)
                    total_sleep = delay + jitter

                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_retries} failed "
                        f"({exc.__class__.__name__}: {exc}). Retrying in {total_sleep:.2f}s..."
                    )
                    time.sleep(total_sleep)

        return wrapper

    return decorator
