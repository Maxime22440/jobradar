# Changelog

All notable changes to this project will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `@observe` decorator for synchronous job functions
- `observe_context` context manager for manual output tracking
- Silent failure detection (`expect_output=True`)
- Low output anomaly detection (`min_output=N`)
- `JobRadarClient` HTTP client with dry-run mode when no API key
- `configure()` for programmatic client setup
- Full type hints (mypy strict)
