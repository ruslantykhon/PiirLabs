import time
from iiot.config import Config
from iiot.alerts import AlertEngine, DEFAULT_RULES
from iiot.gateway import decode, encode, make_client
from iiot.security import (
    sign,
    verify,
    NonceCache,
    SecurityError
)
from iiot.services.common import connect_retry, heartbeat

def main():
    config = Config.from_env()
    engine = AlertEngine(DEFAULT_RULES)
    cache = NonceCache(ttl=60)
    client = make_client(
        client_id="alert-service",
        username=config.MQTT_USER,
        password=config.MQTT_PASSWORD
    )

    def on_connect(client, userdata, flags,
                   reason_code, properties):
        if reason_code == 0:
            client.subscribe(
                "plant/+/+/+/telemetry",
                qos=1
            )
            print("Alerts connected", flush=True)
        else:
            print(
                "Alerts connection rejected:",
                reason_code,
                flush=True
            )

    def on_message(client, userdata, message):
        try:
            if config.SIGNING_KEY is not None:
                msg = verify(
                    config.SIGNING_KEY,
                    message.topic,
                    message.payload,
                    max_age=30,
                    cache=cache
                )
            else:
                msg = decode(message.payload)

            events = engine.process(msg)

            for event in events:
                parts = message.topic.split("/")

                if (
                    len(parts) != 5
                    or parts[-1] != "telemetry"
                ):
                    continue

                parts[-1] = "alerts"
                topic = "/".join(parts)

                if config.SIGNING_KEY is not None:
                    payload = sign(
                        config.SIGNING_KEY,
                        topic,
                        event
                    )
                else:
                    payload = encode(event)

                client.publish(
                    topic,
                    payload,
                    qos=1
                )

                print(
                    "ALERT:",
                    event["state"],
                    event["device_id"],
                    event["rule"],
                    event["value"],
                    flush=True
                )

        except (
            SecurityError,
            ValueError,
            TypeError,
            KeyError
        ) as error:
            print(
                "Invalid message:",
                error,
                flush=True
            )

    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(
        min_delay=1,
        max_delay=60
    )
    connect_retry(client, config)
    client.loop_start()
    print("Alert service started", flush=True)

    try:
        while True:
            heartbeat(config)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Alerts stopped", flush=True)
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main()