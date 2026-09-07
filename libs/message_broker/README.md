# message_broker

Shared message broker abstraction supporting both Redis Streams and Kafka
backends, selectable via the `MESSAGE_BROKER_TYPE` environment variable
(`redis` or `kafka`, default `redis`).

## Interface

Both backends implement `MessageBroker` (`message_broker/base.py`):

- `publish(topic, payload: dict) -> str` — publish a JSON-serializable payload, returns a broker-assigned message id.
- `consume(topic, group, consumer_name) -> AsyncIterator[BrokerMessage]` — yields messages for a named consumer group, so multiple consumer processes can share a topic's workload.
- `ack(topic, group, message)` — acknowledge a message so it isn't redelivered. Delivery is at-least-once: consumers must tolerate redelivery of a message they started but never acked.

```python
from message_broker import get_broker

async with get_broker() as broker:  # reads MESSAGE_BROKER_TYPE from the environment
    await broker.publish("playstore-app-stats", {"package_name": "com.whatsapp", "score": 4.3})

    async for message in broker.consume("playstore-app-stats", group="storage-consumer", consumer_name="worker-1"):
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
repo's convention for the app-list-api services. They need the `redis` and
`kafka` containers from the root `docker-compose.yml` up and reachable, e.g.:

```bash
docker compose up -d redis kafka
docker compose run --rm -e REDIS_HOST=redis -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 app-list-api-fastapi \
  sh -c "pip install -r /app/../../libs/message_broker/requirements-dev.txt && pytest /app/../../libs/message_broker/tests"
```

or more simply, from a Python 3.13 venv on the host once `REDIS_HOST=localhost`
and `KAFKA_BOOTSTRAP_SERVERS=localhost:9092` are exported to match the ports
mapped in `.env`.
