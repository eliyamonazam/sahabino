# Daily Log

## Day 1 — 2026-09-05

### Done
- Set up the repository skeleton with reserved `services/` folders for two parallel CRUD API implementations (FastAPI and Django) and separate services for the scraper, network analyzer, and storage consumer.
- Reserved a `libs/message_broker` folder for a broker abstraction that will support both Redis and Kafka.
- Wrote a `docker-compose.yml` with four infrastructure services: postgres, redis, kafka (KRaft mode, no zookeeper), and metabase, plus a matching `.env.example`.
- Wrote `scripts/setup.sh`, `scripts/run.sh`, and `scripts/stop.sh` to check prerequisites, start, and stop the stack.
- Added a git hook to keep commit messages free of tool-generated attribution lines.
- Wrote a `.gitignore` for a Python + Docker project, including local agent config files.
- Started the full stack with `docker compose up -d` and confirmed all four services reach a healthy/running state.

### Learned
<!-- TODO: do NOT fill this in. The user must fill this in themselves, in their own words, after reviewing what was actually built. -->

### Blockers / questions to raise
- Kafka in KRaft mode took roughly 10-20 seconds to report healthy on first boot; this is expected and the healthcheck has a 30s start period to account for it.
<!-- The user will add their own conceptual questions here -->

### Plan for tomorrow
- TODO
