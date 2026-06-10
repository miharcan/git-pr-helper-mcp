# Contributing

Thanks for considering a contribution.

Git PR Helper MCP is intentionally small. Changes should preserve the two-phase
safety model:

1. Read-only inspection.
2. Read-only planning.
3. Explicitly confirmed execution.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks

Run these before opening a pull request:

```bash
pytest -q
ruff check .
```

## Design Guidelines

- Prefer read-only tools when possible.
- Keep side effects behind `execute_plan`.
- Make every mutating command visible in the returned plan.
- Add tests for Git behavior using temporary repositories.
- Avoid broad workflow automation that hides Git state from the user.

## Good First Issues

- Persist plan audit logs.
- Add optional pre-commit/test commands before commit.
- Support GitHub API PR creation without requiring GitHub CLI.
- Add richer commit and PR title suggestions.
