# vehicle_info_service
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import motor.motor_asyncio
from config import config

app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(config.database.uri)
db = client[config.database.name]

class VehicleInfo(BaseModel):
    license_number: str
    owner_name: str
    email: str

@app.get("/vehicleinfo/{license_number}")
async def get_vehicle_info(license_number: str):
    print("Fetching info for license:", license_number)
    vehicleinfo = await db.vehicleinfo.find_one({"license_number": license_number})
    print("Vehicle info:", vehicleinfo)
    if not vehicleinfo:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {
        "license_number": vehicleinfo["license_number"],
        "owner_name": vehicleinfo["owner_name"],
        "email": vehicleinfo["email"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.fastapi_ports.vehicle_info_service)