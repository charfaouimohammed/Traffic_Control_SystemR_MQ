# rabbitmq_test.py
""" test the rabbitMq it is worck and go out """
import asyncio
import aio_pika
from config import config

async def test_connection():
    try:
        connection = await aio_pika.connect_robust(
            host=config.rabbitmq.host,
            port=config.rabbitmq.port,
            virtualhost=config.rabbitmq.virtual_host,
            login=config.rabbitmq.username,
            password=config.rabbitmq.password
        )
        print("Connection to RabbitMQ established successfully.")
        await connection.close()
    except Exception as e:
        print(f"Failed to connect to RabbitMQ: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
