"""Basic import and version tests."""

import jobradar


def test_version() -> None:
    assert jobradar.__version__ == "0.1.0"


def test_public_api() -> None:
    """All public symbols are importable."""
    assert callable(jobradar.observe)
    assert callable(jobradar.observe_context)
    assert callable(jobradar.configure)
