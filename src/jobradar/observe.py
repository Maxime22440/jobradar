"""Core @observe decorator and observe_context manager for jobradar."""

from __future__ import annotations

import functools
import logging
import time
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, TypeVar, cast

from typing_extensions import ParamSpec

from jobradar.client import get_default_client

logger = logging.getLogger("jobradar")

P = ParamSpec("P")
R = TypeVar("R")


def _build_payload(
    job: str,
    status: str,
    started_at: float,
    finished_at: float,
    output: Any = None,
    error: str | None = None,
    expect_output: bool = False,
    min_output: int | None = None,
) -> dict[str, Any]:
    """Build the event payload to send to the backend."""
    duration_ms = int((finished_at - started_at) * 1000)

    payload: dict[str, Any] = {
        "job": job,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
    }

    if error:
        payload["error"] = error

    # Output analysis — the core "wow" feature
    if output is not None:
        output_value: int | None = None

        # Support int directly or any sized object (list, queryset, etc.)
        if isinstance(output, int):
            output_value = output
        else:
            try:
                output_value = len(output)
            except TypeError:
                pass

        if output_value is not None:
            payload["output_count"] = output_value

            # Silent failure detection
            if expect_output and output_value == 0:
                payload["anomaly"] = {
                    "type": "empty_output",
                    "message": (
                        f"Job '{job}' succeeded but produced 0 output."
                        " Expected non-zero."
                    ),
                    "severity": "high",
                }
                logger.warning(
                    "jobradar ⚠ SILENT FAILURE DETECTED — "
                    "job '%s' succeeded but output is 0",
                    job,
                )

            # Below minimum threshold
            elif min_output is not None and output_value < min_output:
                payload["anomaly"] = {
                    "type": "low_output",
                    "message": (
                        f"Job '{job}' produced {output_value} items, "
                        f"expected at least {min_output}."
                    ),
                    "severity": "medium",
                    "expected_min": min_output,
                    "actual": output_value,
                }
                logger.warning(
                    "jobradar ⚠ LOW OUTPUT — job '%s' produced %d/%d expected items",
                    job,
                    output_value,
                    min_output,
                )

    return payload


def observe(
    job: str,
    *,
    expect_output: bool = False,
    min_output: int | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to observe a job function.

    Args:
        job: Unique name for this job (e.g. "sync-stocks", "send-daily-emails").
        expect_output: If True, alert when the function returns 0 or empty.
        min_output: Alert when return value (or len of return value) is below this.

    Example:
        @observe(job="sync-stocks", expect_output=True, min_output=1000)
        def sync_stocks():
            rows = fetch_and_insert()
            return rows  # 0 rows → jobradar detects silent failure
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            client = get_default_client()
            started_at = time.time()
            output: Any = None
            error: str | None = None
            status = "success"

            try:
                output = func(*args, **kwargs)
                return cast(R, output)
            except Exception:
                status = "error"
                error = traceback.format_exc()
                logger.error("jobradar: job '%s' raised an exception", job)
                raise
            finally:
                finished_at = time.time()
                payload = _build_payload(
                    job=job,
                    status=status,
                    started_at=started_at,
                    finished_at=finished_at,
                    output=output,
                    error=error,
                    expect_output=expect_output,
                    min_output=min_output,
                )
                client.send_event(payload)

        return wrapper

    return decorator


class ObserveContext:
    """Context object available inside observe_context to set output manually."""

    def __init__(self) -> None:
        self._output: Any = None

    def set_output(self, value: Any) -> None:
        """Manually set the output value for anomaly detection."""
        self._output = value

    @property
    def output(self) -> Any:
        return self._output


@contextmanager
def observe_context(
    job: str,
    *,
    expect_output: bool = False,
    min_output: int | None = None,
) -> Generator[ObserveContext, None, None]:
    """Context manager version of @observe.

    Example:
        with observe_context(job="send-emails", expect_output=True) as obs:
            count = send_all_emails()
            obs.set_output(count)
    """
    client = get_default_client()
    ctx = ObserveContext()
    started_at = time.time()
    error: str | None = None
    status = "success"

    try:
        yield ctx
    except Exception:
        status = "error"
        error = traceback.format_exc()
        raise
    finally:
        finished_at = time.time()
        payload = _build_payload(
            job=job,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            output=ctx.output,
            error=error,
            expect_output=expect_output,
            min_output=min_output,
        )
        client.send_event(payload)
