import time
import threading
from iiot.gateway import make_client, encode

last_seen = {}
alert_active = set()
lock = threading.Lock()

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe(
            "plant/+/+/+/telemetry",
            qos=1
        )
        print("Watchdog підключено")

def on_message(client, userdata, message):
    parts = message.topic.split("/")
    if len(parts) != 5:
        return
    device_id = parts[3]
    with lock:
        last_seen[message.topic] = time.monotonic()

        if message.topic in alert_active:
            alert_active.remove(message.topic)

            send_alert(
                client,
                message.topic,
                device_id,
                "cleared"
            )

def send_alert(client, topic, device_id, state):
    alert_topic = topic.rsplit("/", 1)[0] + "/alerts"

    event = {
        "rule": "no_data_30s",
        "device_id": device_id,
        "metric": "telemetry",
        "state": state,
        "value": None,
        "ts": time.time(),
        "severity": "warning"
    }

    client.publish(
        alert_topic,
        encode(event),
        qos=1
    )

    print(f"[{state.upper()}] {device_id}: no_data_30s")

def main():
    client = make_client("watchdog-monitor")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async("localhost", 1883, 60)
    client.loop_start()
    print("Watchdog запущено. Поріг: 30 секунд")

    try:
        while True:
            time.sleep(1)
            now = time.monotonic()

            with lock:
                for topic, last_time in list(last_seen.items()):
                    if now - last_time > 30:
                        if topic not in alert_active:
                            alert_active.add(topic)

                            device_id = topic.split("/")[3]

                            send_alert(
                                client,
                                topic,
                                device_id,
                                "raised"
                            )
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main()