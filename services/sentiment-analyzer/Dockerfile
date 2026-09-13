FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sentiment ./sentiment

# Batch tool, not a daemon: same convention as network-analyzer. Meant to be
# run with `docker compose run --rm sentiment-analyzer`, processing whatever
# `sentiment IS NULL` rows currently exist once and exiting, not staying up
# with the rest of the stack via `up -d`. No `alembic upgrade` step in the
# CMD (unlike the other services' Dockerfiles): this service owns no schema
# of its own to migrate (see README.md).
CMD ["python", "-m", "sentiment.main"]
