import matplotlib.pyplot as plt
from iiot.sim import PumpSimulator
from iiot.analytics import (
    ewma,
    detect_anomalies,
    estimate_rul
)

def main():
    # 1. Генерація 600 кроків симулятора
    sim = PumpSimulator(
        device_id="pump-01",
        seed=42,
        wear_rate=0.001
    )

    ts = []
    vibration = []

    for step in range(600):
        msg = sim.step(
            dt=1.0,
            now=float(step)
        )

        value = msg["metrics"]["vibration_mm_s"]

        ts.append(float(step))
        vibration.append(value)
    # 2. Експоненційне згладжування
    smoothed = ewma(vibration, alpha=0.3)
    # 3. Створення штучних викидів
    anomaly_signal = vibration.copy()
    spike_indices = [150, 300, 520]

    for index in spike_indices:
        anomaly_signal[index] += 3.0

    anomalies = detect_anomalies(
        anomaly_signal,
        window=30,
        threshold=3.5
    )

    print("Штучні викиди:", spike_indices)
    print("Виявлені аномалії:", anomalies)
    # 4. Фактичний момент перетину порога
    limit = 4.5
    actual_crossing = None

    for t, value in zip(ts, vibration):
        if value >= limit:
            actual_crossing = t
            break

    print(
        "Фактичний перетин порога:",
        actual_crossing
    )

    # 5. Оцінка RUL кожні 50 кроків
    evaluation_times = []
    rul_predictions = []
    actual_remaining = []
    print("\nОцінки RUL:")

    for step in range(100, 600, 50):
        end = step + 1
        start = max(0, end - 100)

        window_ts = ts[start:end]
        window_values = vibration[start:end]

        rul = estimate_rul(
            window_ts,
            window_values,
            limit
        )

        evaluation_times.append(ts[step])
        rul_predictions.append(rul)

        if actual_crossing is not None:
            remaining = max(
                actual_crossing - ts[step],
                0.0
            )
        else:
            remaining = None

        actual_remaining.append(remaining)

        print(
            f"Крок {step}: "
            f"RUL = {rul}, "
            f"фактично залишилося = {remaining}"
        )

    # 6. Графік сирого та згладженого сигналу
    plt.figure(figsize=(12, 5))
    plt.plot(
        ts,
        vibration,
        label="Сира вібрація",
        alpha=0.6
    )

    plt.plot(
        ts,
        smoothed,
        label="EWMA",
        linewidth=2
    )

    plt.axhline(
        y=limit,
        color="red",
        linestyle="--",
        label="Поріг 4.5 мм/с"
    )

    if actual_crossing is not None:
        plt.axvline(
            x=actual_crossing,
            color="green",
            linestyle=":",
            label="Фактичний перетин"
        )

    plt.title("Вібрація насосного агрегату та EWMA")
    plt.xlabel("Крок симулятора")
    plt.ylabel("Вібрація, мм/с")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    # 7. Графік виявлених аномалій
    plt.figure(figsize=(12, 5))
    plt.plot(
        ts,
        anomaly_signal,
        label="Сигнал зі штучними викидами"
    )

    plt.scatter(
        [ts[i] for i in anomalies],
        [anomaly_signal[i] for i in anomalies],
        color="red",
        s=60,
        label="Виявлені аномалії",
        zorder=5
    )

    plt.title("Виявлення аномалій за Rolling Z-score")
    plt.xlabel("Крок симулятора")
    plt.ylabel("Вібрація, мм/с")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    # 8. Графік оцінки RUL
    plt.figure(figsize=(12, 5))
    valid_times = []
    valid_rul = []

    for t, rul in zip(
        evaluation_times,
        rul_predictions
    ):
        if rul is not None:
            valid_times.append(t)
            valid_rul.append(rul)

    plt.plot(
        valid_times,
        valid_rul,
        "o-",
        label="Прогнозований RUL"
    )

    if actual_crossing is not None:
        plt.plot(
            evaluation_times,
            actual_remaining,
            "s--",
            label="Фактичний залишковий час"
        )

        plt.axvline(
            x=actual_crossing,
            color="red",
            linestyle=":",
            label="Фактичний момент перетину"
        )

    plt.title("Оцінка залишкового ресурсу (RUL)")
    plt.xlabel("Крок симулятора")
    plt.ylabel("Залишковий ресурс, кроки")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()