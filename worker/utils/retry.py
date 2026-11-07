"""Retry decorator with exponential backoff.

Usage:
    from worker.utils.retry import retry

    @retry(times=3, backoff=2.0)
    def scrape(url):
        ...
"""

import time
import functools
from worker.utils.logger import get_logger

log = get_logger("retry")


def retry(times=3, backoff=2.0, initial_delay=1.0):
    """Retry a function on exception with exponential backoff.

    Args:
        times: total attempts (including the first one)
        backoff: multiplier applied to the delay after each failure
        initial_delay: seconds to wait before the first retry
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    if attempt == times:
                        log.error(
                            f"{fn.__name__}_giving_up",
                            extra={"extra": {
                                "attempts": times,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }},
                        )
                        raise
                    log.warning(
                        f"{fn.__name__}_retrying",
                        extra={"extra": {
                            "attempt": attempt,
                            "next_delay_s": delay,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }},
                    )
                    time.sleep(delay)
                    delay *= backoff

        return wrapper

    return decorator