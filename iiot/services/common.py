import time
from pathlib import Path
from iiot.security import backoff_delays

def connect_retry(client, config):
    delays = backoff_delays(
        base=1.0,
        factor=2.0,
        cap=60.0,
        jitter=0.1
    )

    while True:
        try:
            result = client.connect(
                config.MQTT_HOST,
                config.MQTT_PORT,
                60
            )

            if result == 0:
                return
            print("MQTT connection result:", result)
        except OSError as error:
            print("MQTT connection failed:", error)
        delay = next(delays)
        time.sleep(delay)

def heartbeat(config):
    path = Path(config.HEALTH_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()