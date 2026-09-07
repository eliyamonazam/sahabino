from message_broker.kafka_broker import KafkaBroker


async def test_publish_then_consume_delivers_and_acks(kafka_bootstrap_servers, topic):
    broker = KafkaBroker(bootstrap_servers=kafka_bootstrap_servers)
    await broker.connect()
    try:
        await broker.publish(topic, {"package_name": "com.whatsapp", "score": 4.3})

        received = []
        async for message in broker.consume(topic, group="test-group", consumer_name="test-consumer"):
            received.append(message)
            await broker.ack(topic, "test-group", message)
            break

        assert len(received) == 1
        assert received[0].topic == topic
        assert received[0].payload == {"package_name": "com.whatsapp", "score": 4.3}
    finally:
        await broker.close()


async def test_multiple_messages_delivered_in_order(kafka_bootstrap_servers, topic):
    broker = KafkaBroker(bootstrap_servers=kafka_bootstrap_servers)
    await broker.connect()
    try:
        for i in range(3):
            await broker.publish(topic, {"seq": i})

        received = []
        async for message in broker.consume(topic, group="order-group", consumer_name="order-consumer"):
            received.append(message.payload["seq"])
            await broker.ack(topic, "order-group", message)
            if len(received) == 3:
                break

        assert received == [0, 1, 2]
    finally:
        await broker.close()


async def test_ack_without_active_consumer_raises(kafka_bootstrap_servers, topic):
    from message_broker.base import BrokerMessage

    broker = KafkaBroker(bootstrap_servers=kafka_bootstrap_servers)
    await broker.connect()
    try:
        message = BrokerMessage(id="0-0", topic=topic, payload={})
        try:
            await broker.ack(topic, "no-such-group", message)
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
    finally:
        await broker.close()
