import os
import time
from iiot.alerts import AlertEngine, DEFAULT_RULES
from iiot.gateway import make_client, encode
from iiot.security import (
    verify,
    NonceCache,
    SecurityError
)

def main():
    secret = bytes.fromhex(
        os.environ["IIOT_HMAC_KEY"]
    )

    password = os.environ["MQTT_PASSWORD"]
    engine = AlertEngine(DEFAULT_RULES)
    cache = NonceCache(ttl=60)
    client = make_client(
        client_id="alerts-pump-monitor",
        username="alerts",
        password=password
    )

    def on_connect(
        client, userdata, flags,
        reason_code, properties
    ):
        if reason_code == 0:
            print("Рушій сповіщень підключено")

            client.subscribe(
                "plant/+/+/+/telemetry",
                qos=1
            )
        else:
            print("Помилка авторизації:", reason_code)

    def on_message(client, userdata, message):
        try:
            msg = verify(
                secret,
                message.topic,
                message.payload,
                max_age=30,
                cache=cache
            )

            events = engine.process(msg)

            for event in events:
                parts = message.topic.split("/")

                if len(parts) != 5:
                    continue

                parts[-1] = "alerts"
                alert_topic = "/".join(parts)

                client.publish(
                    alert_topic,
                    encode(event),
                    qos=1
                )

                print(
                    f"[{event['state'].upper()}] "
                    f"{event['device_id']} | "
                    f"{event['rule']} | "
                    f"{event['value']}"
                )

        except SecurityError as error:
            print(
                "Повідомлення не пройшло перевірку:",
                error
            )
        except (ValueError, TypeError, KeyError) as error:
            print("Помилка обробки:", error)

    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(
        min_delay=1,
        max_delay=60
    )

    client.connect_async("localhost", 1883, 60)
    client.loop_start()
    print("Захищений рушій сповіщень запущено")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nЗавершення роботи")
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main()