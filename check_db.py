import sqlite3
conn = sqlite3.connect("iiot.db")

# Перший SQL-запит
result = conn.execute("SELECT COUNT(*) FROM telemetry;")
print("Кількість записів:", result.fetchone()[0])

# Другий SQL-запит
result = conn.execute("""
    SELECT metric, AVG(value)
    FROM telemetry
    GROUP BY metric;
""")

print("\nСередні значення показників:")
for metric, avg in result:
    print(f"{metric}: {avg:.2f}")

conn.close()