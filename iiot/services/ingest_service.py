import time
from iiot.config import Config
from iiot.gateway import decode, make_client
from iiot.security import (
    verify,
    NonceCache,
    SecurityError
)
from iiot.storage import init_db, Ingestor
from iiot.services.common import connect_retry, heartbeat

def main():
    config = Config.from_env()
    conn = init_db(config.DB_PATH)
    cache = NonceCache(ttl=60)

    def decoder(raw, topic):
        if config.SIGNING_KEY is not None:
            return verify(
                config.SIGNING_KEY,
                topic,
                raw,
                max_age=30,
                cache=cache
            )

        return decode(raw)

    ingestor = Ingestor(
        conn=conn,
        decoder=decoder,
        batch_size=20
    )

    client = make_client(
        client_id="ingest-service",
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
            print("Ingest connected", flush=True)
        else:
            print(
                "Ingest connection rejected:",
                reason_code,
                flush=True
            )

    def on_message(client, userdata, message):
        try:
            ingestor.on_message(
                client,
                userdata,
                message
            )
        except SecurityError as error:
            print(
                "Rejected telemetry:",
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
    print("Ingest service started", flush=True)

    try:
        while True:
            time.sleep(1)

            count = ingestor.flush()

            if count:
                print(
                    "Saved rows:",
                    count,
                    flush=True
                )

            heartbeat(config)
    except KeyboardInterrupt:
        print("Ingest stopped", flush=True)
    finally:
        client.disconnect()
        client.loop_stop()
        ingestor.flush()
        conn.close()

if __name__ == "__main__":
    main()