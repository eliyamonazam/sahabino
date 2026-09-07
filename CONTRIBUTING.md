# Contributing

A few conventions this project follows. Please read before opening a PR.

## Branching and merging

- Never force-push to `main`.
- All work happens on a feature branch and is merged into `main` via Pull Request — never a direct push to `main`.

## Commits

- Refactor before you commit, not in a follow-up commit. Each commit should represent one clean, complete unit of work rather than "add feature" followed by "clean up feature."

## Service boundaries

- Each service under `services/` is independent. If one service needs something from another, talk to it over that service's HTTP API, or route through the shared `libs/message_broker` package — never by importing another service's internal code directly.

## Local setup

- After cloning, run `pre-commit install` once so lint and format checks run automatically on every commit (see the "Linting and formatting" section in `README.md`).
