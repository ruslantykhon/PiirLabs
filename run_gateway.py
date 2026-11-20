import os
import time
from iiot.sim import PumpSimulator
from iiot.gateway import Gateway, make_client
from iiot.security import sign, backoff_delays

def connect_with_retry(client):
    for delay in backoff_delays(
        base=1.0,
        factor=2.0,
        cap=60.0,
        jitter=0.1
    ):
        try:
            client.connect("localhost", 1883, 60)
            return
        except OSError as error:
            print("Не вдалося підключитися:", error)
            time.sleep(delay)

def main():
    secret = bytes.fromhex(
        os.environ["IIOT_HMAC_KEY"]
    )
    password = os.environ["MQTT_PASSWORD"]
    sim = PumpSimulator(
        device_id="pump-01",
        seed=42
    )

    client = make_client(
        client_id="gateway-pump-01",
        username="pump-01",
        password=password
    )

    gw = Gateway(
        client=client,
        site="site1",
        line="line1",
        device_id="pump-01",
        buffer_size=1000
    )

    client.on_connect = gw.on_connect
    client.on_disconnect = gw.on_disconnect
    client.reconnect_delay_set(
        min_delay=1,
        max_delay=60
    )

    connect_with_retry(client)
    client.loop_start()
    print("Захищений MQTT-шлюз запущено")
    print("Топік:", gw.telemetry_topic)

    try:
        while True:
            msg = sim.step(dt=1.0)

            signed = sign(
                secret,
                gw.telemetry_topic,
                msg
            )
            gw.publish(signed)
            print(
                "Стан:",
                "ONLINE" if gw.connected else "OFFLINE",
                "| Буфер:", len(gw.buffer),
                "| Дані:", msg["metrics"]
            )

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nЗавершення роботи шлюзу")
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main()