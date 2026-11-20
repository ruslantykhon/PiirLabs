import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

conn = sqlite3.connect("iiot.db")
rows = conn.execute("""
    SELECT ts, value
    FROM telemetry
    WHERE device_id = 'pump-01'
      AND metric = 'vibration_mm_s'
    ORDER BY ts
""").fetchall()

conn.close()
if not rows:
    print("Дані вібрації відсутні в базі")
else:
    timestamps = [
        datetime.fromtimestamp(row[0])
        for row in rows
    ]
    values = [row[1] for row in rows]
    plt.figure(figsize=(12, 5))
    plt.plot(
        timestamps,
        values,
        label="Вібрація насоса"
    )

    plt.axhline(
        y=4.5,
        color="red",
        linestyle="--",
        label="Поріг спрацювання: 4.5 мм/с"
    )

    plt.axhline(
        y=4.0,
        color="orange",
        linestyle="--",
        label="Поріг скидання: 4.0 мм/с"
    )

    plt.title("Моніторинг вібрації насосного агрегату")
    plt.xlabel("Час")
    plt.ylabel("Вібрація, мм/с")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.show()