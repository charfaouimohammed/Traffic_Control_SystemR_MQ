# traffic_control_service.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import motor.motor_asyncio
from datetime import datetime
import httpx
import logging
from config import config
import aio_pika
import json
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(config.database.uri)
db = client[config.database.name]

RABBITMQ_EXCHANGE = "camera_events"
FINE_EXCHANGE = "fine_events"

# Models
class VehicleEntry(BaseModel):
    license_number: str
    lane: int
    timestamp: str

class VehicleExit(BaseModel):
    license_number: str
    lane: int
    timestamp: str

# Function to calculate speed
def calculate_speed(entry_time: datetime, exit_time: datetime) -> float:
    time_diff = (exit_time - entry_time).total_seconds()  # Time difference in seconds
    distance_meters = 1000  # Fixed distance in meters
    
    if time_diff > 0:
        speed_kmh = (distance_meters / time_diff) * 3.6  # Convert to km/h
        return speed_kmh
    else:
        return 0.0

# Function to notify fine collection service via RabbitMQ
async def notify_fine_collection(exchange, license_number, speed, timestamp):
    payload = {
        "license_number": license_number,
        "speed": speed,
        "timestamp": timestamp
    }
    try:
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        await exchange.publish(message, routing_key="fine")
        logger.info(f"Fine collection notified for {license_number} with speed {speed} km/h")
    except Exception as e:
        logger.error(f"Error notifying fine collection service: {e}")

async def setup_rabbitmq():
    connection = await aio_pika.connect_robust(
        host=config.rabbitmq.host,
        port=config.rabbitmq.port,
        virtualhost=config.rabbitmq.virtual_host,
        login=config.rabbitmq.username,
        password=config.rabbitmq.password
    )
    channel = await connection.channel()
    
    # Declare exchange for camera events
    camera_exchange = await channel.declare_exchange(RABBITMQ_EXCHANGE, aio_pika.ExchangeType.DIRECT)
    
    # Declare queues
    entry_queue = await channel.declare_queue("entry_cam_queue", durable=True)
    exit_queue = await channel.declare_queue("exit_cam_queue", durable=True)
    
    # Bind queues to exchange with routing keys
    await entry_queue.bind(camera_exchange, routing_key="entry")
    await exit_queue.bind(camera_exchange, routing_key="exit")
    
    # Declare exchange for fines
    fine_exchange = await channel.declare_exchange(FINE_EXCHANGE, aio_pika.ExchangeType.DIRECT)
    
    return connection, channel, camera_exchange, fine_exchange

# Function to consume entry events
async def consume_entry_messages(channel, camera_exchange, fine_exchange):
    queue = await channel.declare_queue("entry_cam_queue", durable=True)
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                entry_data = json.loads(message.body.decode())
                await handle_entry_event(entry_data, camera_exchange, fine_exchange)

# Function to consume exit messages
async def consume_exit_messages(channel, camera_exchange, fine_exchange):
    queue = await channel.declare_queue("exit_cam_queue", durable=True)
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                exit_data = json.loads(message.body.decode())
                await handle_exit_event(exit_data, camera_exchange, fine_exchange)

# Handle entry event
async def handle_entry_event(entry_data, camera_exchange, fine_exchange):
    vehicle_state = {
        "license_number": entry_data["license_number"],
        "entry_timestamp": entry_data["timestamp"],
        "entry_lane": entry_data["lane"],
        "exit_timestamp": None,
        "exit_lane": None,
        "speed": None
    }
    try:
        await db.vehicle_states.insert_one(vehicle_state)
        logger.info(f"Vehicle entry recorded: {vehicle_state}")
    except Exception as e:
        logger.error(f"Error recording vehicle entry: {e}")

# Handle exit event
async def handle_exit_event(exit_data, camera_exchange, fine_exchange):
    # Find the most recent vehicle state based on the entry timestamp
    vehicle_state = await db.vehicle_states.find_one(
        {"license_number": exit_data["license_number"], "exit_timestamp": None},
        sort=[("entry_timestamp", -1)]  # Sort by entry_timestamp in descending order to get the latest entry
    )
    
    if not vehicle_state:
        logger.error(f"Vehicle entry not found for license: {exit_data['license_number']}")
        return

    try:
        # Parse timestamps
        entry_time = datetime.fromisoformat(vehicle_state["entry_timestamp"])
        exit_time = datetime.fromisoformat(exit_data["timestamp"])
        
        # Calculate speed
        speed = calculate_speed(entry_time, exit_time)
        logger.info(f"Speed calculated: {speed} km/h for vehicle {exit_data['license_number']}")

        # Use update_one with $set to update only specific fields
        await db.vehicle_states.update_one(
            {"_id": vehicle_state["_id"]},  # Ensure we are updating the correct document by _id
            {"$set": {
                "exit_timestamp": exit_data["timestamp"],
                "exit_lane": exit_data["lane"],
                "speed": speed
            }}
        )

        # Notify fine collection service if speed exceeds limit
        if speed > 60:  # Assuming speed limit is 60 km/h
            await notify_fine_collection(fine_exchange, exit_data["license_number"], speed, exit_data["timestamp"])

        logger.info(f"Vehicle exit recorded: {exit_data['license_number']}, Speed: {speed} km/h")
    except Exception as e:
        logger.error(f"Error processing vehicle exit: {e}")

async def consume_messages(connection, channel, camera_exchange, fine_exchange):
    await asyncio.gather(
        consume_entry_messages(channel, camera_exchange, fine_exchange),
        consume_exit_messages(channel, camera_exchange, fine_exchange)
    )

async def start_consuming():
    connection, channel, camera_exchange, fine_exchange = await setup_rabbitmq()
    await consume_messages(connection, channel, camera_exchange, fine_exchange)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_consuming())

@app.get("/")
async def root():
    return {"message": "Traffic Control Service is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.fastapi_ports.vehicle_state_service)
