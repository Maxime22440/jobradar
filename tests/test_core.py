"""Core tests for jobradar."""


def test_import() -> None:
    """Package imports correctly."""
    import jobradar

    assert jobradar.__version__ == "0.1.0"
