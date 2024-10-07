# config.py
import yaml
from pydantic import BaseModel
from typing import Any

class DatabaseConfig(BaseModel):
    uri: str
    name: str

class MailSMTPConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str

class MailConfig(BaseModel):
    smtp: MailSMTPConfig
    sender: str

class ServicesConfig(BaseModel):
    entry_cam_url: str
    exit_cam_url: str
    vehicle_info_service: str
    collect_fine_service: str

class SimulationDelayRange(BaseModel):
    min_seconds: int
    max_seconds: int

class AppSettings(BaseModel):
    lanes: int
    num_vehicles: int
    simulation_delay_range: SimulationDelayRange

class FastAPIPorts(BaseModel):
    vehicle_state_service: int
    collect_fine_service: int
    vehicle_info_service: int
    

class RabbitMQConfig(BaseModel):
    host: str
    port: int
    virtual_host: str
    username: str
    password: str
# config.py (Additions)
class Config(BaseModel):
    rabbitmq: RabbitMQConfig
    database: DatabaseConfig
    mail: MailConfig
    services: ServicesConfig
    app: AppSettings
    fastapi_ports: FastAPIPorts

def load_config(path: str = "config.yaml") -> Config:
    with open(path, "r") as file:
        config_dict = yaml.safe_load(file)
    return Config(**config_dict)

config = load_config()
