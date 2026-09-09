# message_broker

Shared message broker abstraction with two implementations behind the same
interface: Kafka and Redis Streams, selectable via the `MESSAGE_BROKER_TYPE`
environment variable (`redis` or `kafka`, default `kafka`).

**Kafka is the broker actually used in the deployed stack** (`docker-compose.yml`
only runs a `kafka` container, not `redis`) — the project's own bonus criteria
frame the choice as "Kafka instead of Redis," and running two message brokers
in parallel indefinitely for the same job isn't worth the extra always-on
service and doubled testing surface it implies.

The Redis Streams implementation (`redis_broker.py`) is kept in the codebase
and still has its own test suite (`tests/test_redis_broker.py`) — it
demonstrates the same interface working against a different backend and
required real work to build, so it's worth keeping even though it's not part
of the deployed stack. To run its tests locally, spin up a standalone Redis
container:

```bash
docker run --rm -p 6379:6379 redis:7
```

then run `pytest tests/test_redis_broker.py` — the tests default to
`REDIS_HOST=localhost`/`REDIS_PORT=6379`, matching that container's mapped
port, so no extra environment variables are needed.

## Interface

Both backends implement `MessageBroker` (`message_broker/base.py`):

- `publish(topic, payload: dict) -> str` — publish a JSON-serializable payload, returns a broker-assigned message id.
- `consume(topic, group, consumer_name) -> AsyncIterator[BrokerMessage]` — yields messages for a named consumer group, so multiple consumer processes can share a topic's workload.
- `ack(topic, group, message)` — acknowledge a message so it isn't redelivered. Delivery is at-least-once: consumers must tolerate redelivery of a message they started but never acked.

```python
from message_broker import get_broker

async with get_broker() as broker:  # reads MESSAGE_BROKER_TYPE from the environment
    await broker.publish("playstore-app-stats", {"package_name": "com.whatsapp", "score": 4.3})

    async for message in broker.consume(
        "playstore-app-stats", group="storage-consumer", consumer_name="worker-1"
    ):
        persist(message.payload)
        await broker.ack("playstore-app-stats", "storage-consumer", message)
```

## Connection settings

Read from the environment (matching the rest of the stack's `.env`):

| Backend | Variables |
|---|---|
| redis | `REDIS_HOST` (default `redis`), `REDIS_PORT` (default `6379`) |
| kafka | `KAFKA_BOOTSTRAP_SERVERS` (default `kafka:9092`) |

## Using this library from a service

Add it to a service's `requirements.txt` as an editable path dependency:

```
-e ../../libs/message_broker
```

and make sure the service's Dockerfile `COPY`s `libs/message_broker` into the
image (build context must be the repo root, or the lib copied in separately)
before `pip install -r requirements.txt`.

## Tests

Integration tests run against real Redis and Kafka (no mocks), matching this
repo's convention for the app-list-api services.

The Kafka tests need the `kafka` container from the root `docker-compose.yml`
up and reachable, e.g.:

```bash
docker compose up -d kafka
docker compose run --rm -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 app-list-api-fastapi \
  sh -c "pip install -r /app/../../libs/message_broker/requirements-dev.txt && pytest /app/../../libs/message_broker/tests/test_kafka_broker.py"
```

or more simply, from a Python 3.13 venv on the host once
`KAFKA_BOOTSTRAP_SERVERS=localhost:9092` is exported to match the port
mapped in `.env`.

The Redis tests aren't part of the main stack anymore (see above), so they
need a standalone `redis` container (`docker run --rm -p 6379:6379 redis:7`)
rather than anything from the root `docker-compose.yml`, then
`pytest tests/test_redis_broker.py` against it (defaults to
`REDIS_HOST=localhost`).
