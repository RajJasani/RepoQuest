# Contributing to TaskBoard

We welcome contributions! To keep the project maintainable, reliable, and welcoming to new contributors, please follow these guidelines when opening a pull request.

## Contribution Rules

1. **Tests Required:** Every bug fix and new feature must include corresponding automated tests under `tests/`. PRs without test coverage will not be merged.
2. **Docs Updated:** Update `README.md` and inline docstrings whenever behavior, configuration, or API endpoints change.
3. **Small Focused PRs:** Keep PRs small and focused on a single change. Avoid giant refactorings or mixing multiple features into one diff.
4. **Link an Issue:** Every PR must link to an existing tracked issue (e.g., `Closes #12` or `Fixes #45`) explaining the motivation and context.
5. **No Secrets or Credentials:** Never commit credentials, tokens, or private keys to the repository.

## Development Workflow

1. Fork and clone the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Write clean, modular code following the existing structure.
4. Run tests locally: `python -m unittest discover -s tests`.
5. Submit a pull request with a descriptive title and summary.

