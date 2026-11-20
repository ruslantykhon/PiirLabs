import sqlite3
import threading

def init_db(path=":memory:"):
    conn = sqlite3.connect(
        path,
        check_same_thread=False
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            ts REAL,
            device_id TEXT,
            metric TEXT,
            value REAL
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_telemetry_device_metric_ts
        ON telemetry (device_id, metric, ts)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_1m (
            bucket INTEGER,
            device_id TEXT,
            metric TEXT,
            avg REAL,
            min REAL,
            max REAL,
            n INTEGER,
            PRIMARY KEY (bucket, device_id, metric)
        )
    """)

    conn.commit()
    return conn

def insert_batch(conn, msgs):
    rows = []

    for msg in msgs:
        ts = msg["ts"]
        device_id = msg["device_id"]
        metrics = msg["metrics"]

        for metric, value in metrics.items():
            rows.append((
                ts,
                device_id,
                metric,
                value
            ))

    if not rows:
        return 0

    with conn:
        conn.executemany("""
            INSERT INTO telemetry
            (ts, device_id, metric, value)
            VALUES (?, ?, ?, ?)
        """, rows)

    return len(rows)

def last_n(conn, device_id, metric, n):
    if n <= 0:
        return []

    cursor = conn.execute("""
        SELECT ts, value
        FROM (
            SELECT ts, value, rowid
            FROM telemetry
            WHERE device_id = ?
              AND metric = ?
            ORDER BY ts DESC, rowid DESC
            LIMIT ?
        )
        ORDER BY ts ASC, rowid ASC
    """, (device_id, metric, n))

    return cursor.fetchall()

def downsample_1m(conn, before_ts):
    with conn:
        conn.execute("""
            INSERT INTO telemetry_1m
            (bucket, device_id, metric, avg, min, max, n)

            SELECT
                CAST(ts / 60 AS INTEGER) * 60 AS bucket,
                device_id,
                metric,
                AVG(value),
                MIN(value),
                MAX(value),
                COUNT(*)

            FROM telemetry
            WHERE ts < ?

            GROUP BY
                bucket,
                device_id,
                metric

            ON CONFLICT(bucket, device_id, metric)
            DO UPDATE SET
                avg = excluded.avg,
                min = excluded.min,
                max = excluded.max,
                n = excluded.n
        """, (before_ts,))

    cursor = conn.execute(
        "SELECT COUNT(*) FROM telemetry_1m"
    )
    return cursor.fetchone()[0]

def purge_older_than(conn, ts):
    with conn:
        cursor = conn.execute("""
            DELETE FROM telemetry
            WHERE ts < ?
        """, (ts,))

    return cursor.rowcount

class Ingestor:
    def __init__(self, conn, decoder, batch_size=20):
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        self.conn = conn
        self.decoder = decoder
        self.batch_size = batch_size
        self.batch = []
        self.lock = threading.Lock()

    def on_message(self, client, userdata, message):
        try:
            msg = self.decoder(
                message.payload,
                message.topic
            )

            if not isinstance(msg, dict):
                return

            if (
                "ts" not in msg
                or "device_id" not in msg
                or not isinstance(msg.get("metrics"), dict)
            ):
                return

            with self.lock:
                self.batch.append(msg)

                if len(self.batch) >= self.batch_size:
                    self._flush_locked()

        except (ValueError, TypeError, KeyError, UnicodeError):
            return

    def _flush_locked(self):
        if not self.batch:
            return 0

        count = insert_batch(self.conn, self.batch)
        self.batch.clear()
        return count

    def flush(self):
        with self.lock:
            return self._flush_locked()