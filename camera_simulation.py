# camera_simulation.py
import random
import time
import asyncio
from datetime import datetime
from config import config
import aio_pika
import json

RABBITMQ_EXCHANGE = "camera_events"

async def generate_license_number():
    return f"ABC-{random.randint(1110, 1120)}"

async def setup_rabbitmq():
    connection = await aio_pika.connect_robust(
        host=config.rabbitmq.host,
        port=config.rabbitmq.port,
        virtualhost=config.rabbitmq.virtual_host,
        login=config.rabbitmq.username,
        password=config.rabbitmq.password
    )
    channel = await connection.channel()
    
    # Declare exchange
    exchange = await channel.declare_exchange(RABBITMQ_EXCHANGE, aio_pika.ExchangeType.DIRECT)
    
    # Declare queues
    entry_queue = await channel.declare_queue("entry_cam_queue", durable=True)
    exit_queue = await channel.declare_queue("exit_cam_queue", durable=True)
    
    # Bind queues to exchange with routing keys
    await entry_queue.bind(exchange, routing_key="entry")
    await exit_queue.bind(exchange, routing_key="exit")
    
    return connection, channel, exchange

async def simulate_vehicle_passing(exchange, vehicle_count):
    license_number = await generate_license_number()
    entry_lane = random.randint(1, config.app.lanes)
    entry_timestamp = datetime.now().isoformat()

    # Create entry event
    entry_event = {
        "license_number": license_number,
        "lane": entry_lane,
        "timestamp": entry_timestamp
    }

    # Publish entry event
    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(entry_event).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        ),
        routing_key="entry"
    )
    print(f"Vehicle {license_number} passed entry camera at {entry_timestamp}")

    # Simulate random delay before exiting
    await asyncio.sleep(random.randint(
        config.app.simulation_delay_range.min_seconds,
        config.app.simulation_delay_range.max_seconds
    ))  # Vehicle stays for min to max seconds

    exit_lane = random.randint(1, config.app.lanes)
    exit_timestamp = datetime.now().isoformat()

    # Create exit event
    exit_event = {
        "license_number": license_number,
        "lane": exit_lane,
        "timestamp": exit_timestamp
    }

    # Publish exit event
    await exchange.publish(
        aio_pika.Message(
            body=json.dumps(exit_event).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        ),
        routing_key="exit"
    )
    print(f"Vehicle {license_number} passed exit camera at {exit_timestamp}")

async def main():
    connection, channel, exchange = await setup_rabbitmq()
    try:
        for vehicle_count in range(config.app.num_vehicles):
            await simulate_vehicle_passing(exchange, vehicle_count)
            await asyncio.sleep(random.randint(
                config.app.simulation_delay_range.min_seconds,
                config.app.simulation_delay_range.max_seconds
            ))  # Simulate a vehicle every min to max seconds
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(main())
