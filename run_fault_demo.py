import os
from iiot.security import sign
import time
from iiot.sim import PumpSimulator
from iiot.gateway import Gateway, make_client

def main():
    secret = bytes.fromhex(os.environ["IIOT_HMAC_KEY"])
    password = os.environ["MQTT_PASSWORD"]
    sim = PumpSimulator(
        device_id="pump-01",
        seed=42
    )

    client = make_client(
        client_id="fault-demo-pump-01",
        username="pump-01",
        password=password
    )

    gw = Gateway(
        client=client,
        site="site1",
        line="line1",
        device_id="pump-01"
    )

    client.on_connect = gw.on_connect
    client.on_disconnect = gw.on_disconnect
    client.connect_async("localhost", 1883, 60)
    client.loop_start()
    print("Демонстрація несправності насоса")

    try:
        for i in range(30):
            if i == 10:
                sim.inject_fault("bearing")
                print("\nНЕСПРАВНІСТЬ: знос підшипника\n")

            if i == 20:
                sim.running = False
                print("\nНАСОС ЗУПИНЕНО\n")

            msg = sim.step(dt=1.0)
            gw.publish(sign(secret, gw.telemetry_topic, msg))

            print(
                f"Крок {i + 1}: "
                f"вібрація = "
                f"{msg['metrics']['vibration_mm_s']} мм/с"
            )

            time.sleep(1)
    except KeyboardInterrupt:
        print("Демонстрацію зупинено")
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main()