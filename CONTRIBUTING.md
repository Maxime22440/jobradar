# Contributing to jobradar

Thanks for your interest! Here's how to get started in 10 minutes.

## Setup

```bash
git clone https://github.com/Maxime22440/jobradar
cd jobradar
pip install -e ".[dev]"
pre-commit install
```

## Running tests

```bash
pytest
```

## Submitting a PR

- One feature or fix per PR
- Add tests for new behaviour
- Run `ruff check` and `mypy` before pushing
- Update `CHANGELOG.md` under `[Unreleased]`
