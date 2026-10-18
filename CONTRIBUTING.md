# Contributing

Use Python 3.10+ and a virtual environment. Install with:

```sh
python -m pip install -e ".[dev]" -c constraints-dev.txt
ruff check .
ruff format --check .
mypy
pytest
```

Keep changes scoped to one milestone. Include behavior tests and update docs.
Schema/architecture changes need an ADR and compatibility decision. Never use
shell=True for user commands, capture all environment variables by default, or
silently require root. Keep raw evidence separate from normalized data.

Use feat:, fix:, test:, or docs: commit prefixes. PRs should explain What, Why,
How, Tests, and Risks. M1's next issue is tracked in docs/backlog.md.
