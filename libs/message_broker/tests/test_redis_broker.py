from message_broker.redis_broker import RedisStreamsBroker


async def test_publish_then_consume_delivers_and_acks(redis_connection_kwargs, topic):
    broker = RedisStreamsBroker(**redis_connection_kwargs)
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


async def test_multiple_messages_delivered_in_order(redis_connection_kwargs, topic):
    broker = RedisStreamsBroker(**redis_connection_kwargs)
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
