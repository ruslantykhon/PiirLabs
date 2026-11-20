import time
from iiot.config import Config
from iiot.gateway import Gateway, make_client
from iiot.security import sign
from iiot.sim import PumpSimulator
from iiot.services.common import connect_retry, heartbeat

def main():
    config = Config.from_env()

    sim = PumpSimulator(
        device_id=config.DEVICE_ID,
        seed=42
    )

    client = make_client(
        client_id=f"gateway-{config.DEVICE_ID}",
        username=config.MQTT_USER,
        password=config.MQTT_PASSWORD
    )

    gateway = Gateway(
        client=client,
        site=config.SITE,
        line=config.LINE,
        device_id=config.DEVICE_ID,
        buffer_size=1000
    )

    def on_connect(client, userdata, flags,
                   reason_code, properties):
        if reason_code == 0:
            gateway.on_connect(
                client, userdata, flags,
                reason_code, properties
            )
            print("Gateway connected", flush=True)
        else:
            gateway.connected = False
            print(
                "MQTT connection rejected:",
                reason_code,
                flush=True
            )

    client.on_connect = on_connect
    client.on_disconnect = gateway.on_disconnect
    client.reconnect_delay_set(
        min_delay=1,
        max_delay=60
    )
    connect_retry(client, config)
    client.loop_start()

    print(
        "Gateway started:",
        config.DEVICE_ID,
        gateway.telemetry_topic,
        flush=True
    )

    start_time = time.monotonic()
    fault_injected = False

    try:
        while True:
            elapsed = time.monotonic() - start_time

            if (
                config.FAULT_AFTER is not None
                and not fault_injected
                and elapsed >= config.FAULT_AFTER
            ):
                sim.inject_fault("bearing")
                fault_injected = True
                print(
                    "Bearing fault injected:",
                    config.DEVICE_ID,
                    flush=True
                )

            msg = sim.step(dt=config.INTERVAL)

            if config.SIGNING_KEY is not None:
                payload = sign(
                    config.SIGNING_KEY,
                    gateway.telemetry_topic,
                    msg
                )
            else:
                payload = msg
            gateway.publish(payload)
            heartbeat(config)
            print(
                config.DEVICE_ID,
                "connected =", gateway.connected,
                "buffer =", len(gateway.buffer),
                "vibration =",
                msg["metrics"]["vibration_mm_s"],
                flush=True
            )

            time.sleep(config.INTERVAL)
    except KeyboardInterrupt:
        print("Gateway stopped", flush=True)
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main()