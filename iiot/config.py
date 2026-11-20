import os
from dataclasses import dataclass

def optional(name):
    value = os.getenv(name, "").strip()
    return value if value else None

@dataclass
class Config:
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USER: str | None = None
    MQTT_PASSWORD: str | None = None

    SITE: str = "kyiv"
    LINE: str = "line1"
    DEVICE_ID: str = "pump-01"

    INTERVAL: float = 1.0
    SIGNING_KEY: bytes | None = None
    DB_PATH: str = "iiot.db"
    FAULT_AFTER: float | None = None
    HEALTH_FILE: str = "/tmp/healthy"

    @classmethod
    def from_env(cls):
        key = optional("SIGNING_KEY")
        return cls(
            MQTT_HOST=os.getenv("MQTT_HOST") or "localhost",
            MQTT_PORT=int(os.getenv("MQTT_PORT") or 1883),
            MQTT_USER=optional("MQTT_USER"),
            MQTT_PASSWORD=optional("MQTT_PASSWORD"),
            SITE=os.getenv("SITE") or "kyiv",
            LINE=os.getenv("LINE") or "line1",
            DEVICE_ID=os.getenv("DEVICE_ID") or "pump-01",
            INTERVAL=float(os.getenv("INTERVAL") or 1.0),
            SIGNING_KEY=(
                key.encode("utf-8")
                if key is not None
                else None
            ),
            DB_PATH=os.getenv("DB_PATH") or "iiot.db",
            FAULT_AFTER=(
                float(value)
                if (value := optional("FAULT_AFTER"))
                else None
            ),
            HEALTH_FILE=os.getenv("HEALTH_FILE") or "/tmp/healthy",
        )