# Contributing

## Workflow (GitHub Flow)

1. Open an issue describing the bug or feature.
2. Create a branch from `main`: `feature/<short-name>` or `fix/<short-name>`.
3. Commit in small steps using [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: …`, `fix: …`, `test: …`, `docs: …`, `ci: …`, `refactor: …`.
4. Push and open a pull request that references the issue (`Closes #12`).
5. CI must be green (lint, tests on all Python versions, build) before merging.
6. Merge into `main`; delete the branch.

## Local checks before pushing

```bash
ruff format .
ruff check .
pytest --cov
```

## Releases

Versions follow [Semantic Versioning](https://semver.org/). To release:

1. Update `version` in `pyproject.toml` and `__version__` in `src/tsanalyzer/__init__.py`.
2. Add an entry to `CHANGELOG.md`.
3. `git tag vX.Y.Z && git push origin vX.Y.Z` — the Release workflow does the rest.
