import os
import time
from iiot.gateway import make_client
from iiot.storage import init_db, Ingestor
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
    conn = init_db("iiot.db")
    cache = NonceCache(ttl=60)

    def decoder(raw, topic):
        return verify(
            secret,
            topic,
            raw,
            max_age=30,
            cache=cache
        )

    ingestor = Ingestor(
        conn=conn,
        decoder=decoder,
        batch_size=20
    )

    client = make_client(
        client_id="ingestor-pump-01",
        username="ingest",
        password=password
    )

    def on_connect(
        client, userdata, flags,
        reason_code, properties
    ):
        if reason_code == 0:
            print("Захищений приймач підключено")
            client.subscribe(
                "plant/+/+/+/telemetry",
                qos=1
            )
        else:
            print("Відмова підключення:", reason_code)

    def on_message(client, userdata, message):
        try:
            ingestor.on_message(
                client, userdata, message
            )
        except SecurityError as error:
            print("Повідомлення відхилено:", error)

    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(
        min_delay=1,
        max_delay=60
    )

    client.connect_async("localhost", 1883, 60)
    client.loop_start()
    print("Захищений запис у SQLite запущено")

    try:
        while True:
            time.sleep(1)
            count = ingestor.flush()

            if count:
                print(f"Записано {count} рядків")
    except KeyboardInterrupt:
        print("\nЗупинка приймача")
    finally:
        client.disconnect()
        client.loop_stop()
        ingestor.flush()
        conn.close()

if __name__ == "__main__":
    main()