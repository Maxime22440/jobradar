"""Tests for the @observe decorator and observe_context manager."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from jobradar.observe import ObserveContext, observe, observe_context

# jobradar.observe (function) shadows the module in the package namespace.
# Use sys.modules to get the actual module for patching.
_observe_mod = sys.modules["jobradar.observe"]

# ── Helpers ──────────────────────────────────────────────────────────────────

def make_mock_client() -> MagicMock:
    """Return a mock client that captures send_event calls."""
    return MagicMock()


# ── @observe decorator ───────────────────────────────────────────────────────

class TestObserveDecorator:
    def test_decorated_function_returns_value(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="test-job")
            def my_job() -> int:
                return 42

            assert my_job() == 42

    def test_event_sent_on_success(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="test-job")
            def my_job() -> str:
                return "done"

            my_job()

        mock_client.send_event.assert_called_once()
        payload = mock_client.send_event.call_args[0][0]
        assert payload["job"] == "test-job"
        assert payload["status"] == "success"
        assert "duration_ms" in payload

    def test_event_sent_on_exception(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="failing-job")
            def bad_job() -> None:
                raise ValueError("something broke")

            with pytest.raises(ValueError, match="something broke"):
                bad_job()

        payload = mock_client.send_event.call_args[0][0]
        assert payload["status"] == "error"
        assert "ValueError" in payload["error"]

    def test_silent_failure_detected_when_output_zero(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="sync-stocks", expect_output=True)
            def sync_stocks() -> list[str]:
                return []  # silent failure

            sync_stocks()

        payload = mock_client.send_event.call_args[0][0]
        assert payload["output_count"] == 0
        assert payload["anomaly"]["type"] == "empty_output"
        assert payload["anomaly"]["severity"] == "high"

    def test_no_anomaly_when_output_nonzero(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="sync-stocks", expect_output=True)
            def sync_stocks() -> list[str]:
                return ["row1", "row2", "row3"]

            sync_stocks()

        payload = mock_client.send_event.call_args[0][0]
        assert payload["output_count"] == 3
        assert "anomaly" not in payload

    def test_low_output_anomaly_detected(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="sync-stocks", min_output=1000)
            def sync_stocks() -> list[str]:
                return ["row1", "row2"]  # only 2, expected 1000

            sync_stocks()

        payload = mock_client.send_event.call_args[0][0]
        assert payload["anomaly"]["type"] == "low_output"
        assert payload["anomaly"]["actual"] == 2
        assert payload["anomaly"]["expected_min"] == 1000

    def test_int_return_value_tracked(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="send-emails", expect_output=True)
            def send_emails() -> int:
                return 150

            send_emails()

        payload = mock_client.send_event.call_args[0][0]
        assert payload["output_count"] == 150
        assert "anomaly" not in payload

    def test_duration_is_positive(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            @observe(job="timed-job")
            def timed_job() -> None:
                pass

            timed_job()

        payload = mock_client.send_event.call_args[0][0]
        assert payload["duration_ms"] >= 0


# ── observe_context manager ───────────────────────────────────────────────────

class TestObserveContext:
    def test_context_manager_sends_event(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            with observe_context(job="ctx-job") as obs:
                obs.set_output(99)

        mock_client.send_event.assert_called_once()
        payload = mock_client.send_event.call_args[0][0]
        assert payload["job"] == "ctx-job"
        assert payload["output_count"] == 99

    def test_context_manager_catches_exception(self) -> None:
        mock_client = make_mock_client()
        with patch.object(_observe_mod, "get_default_client", return_value=mock_client):
            with pytest.raises(RuntimeError):
                with observe_context(job="ctx-fail"):
                    raise RuntimeError("ctx error")

        payload = mock_client.send_event.call_args[0][0]
        assert payload["status"] == "error"

    def test_observe_context_default_output_is_none(self) -> None:
        ctx = ObserveContext()
        assert ctx.output is None

    def test_observe_context_set_output(self) -> None:
        ctx = ObserveContext()
        ctx.set_output(42)
        assert ctx.output == 42
