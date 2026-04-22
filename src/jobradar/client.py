"""HTTP client for jobradar backend communication."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("jobradar")

_DEFAULT_ENDPOINT = "https://in.jobradar.dev/v1"


class JobRadarClient:
    """Sends job run events to the jobradar backend."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.api_key = api_key or os.getenv("JOBRADAR_API_KEY")
        self.endpoint = endpoint or os.getenv("JOBRADAR_ENDPOINT", _DEFAULT_ENDPOINT)
        self.timeout = timeout
        self._dry_run = not self.api_key

        if self._dry_run:
            logger.debug(
                "jobradar: no API key found — running in dry-run mode. "
                "Set JOBRADAR_API_KEY to send events."
            )

    def send_event(self, payload: dict[str, Any]) -> None:
        """Send a job run event. Never raises — failures are logged, not propagated."""
        if self._dry_run:
            logger.debug("jobradar [dry-run] event: %s", payload)
            return

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.endpoint}/events",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "jobradar-python/0.1.0",
                    },
                )
                response.raise_for_status()
                logger.debug("jobradar: event sent — status %s", response.status_code)
        except httpx.TimeoutException:
            logger.warning("jobradar: event send timed out (job not affected)")
        except httpx.HTTPStatusError as e:
            logger.warning(
                "jobradar: backend returned %s (job not affected)",
                e.response.status_code,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("jobradar: failed to send event: %s (job not affected)", e)


# Module-level default client — lazy initialized
_default_client: JobRadarClient | None = None


def get_default_client() -> JobRadarClient:
    """Return the module-level default client, creating it if needed."""
    global _default_client
    if _default_client is None:
        _default_client = JobRadarClient()
    return _default_client


def configure(
    api_key: str,
    endpoint: str | None = None,
    timeout: float = 5.0,
) -> None:
    """Configure the default jobradar client.

    Call this once at app startup:
        import jobradar
        jobradar.configure(api_key="jr_live_xxx")
    """
    global _default_client
    _default_client = JobRadarClient(
        api_key=api_key, endpoint=endpoint, timeout=timeout
    )
