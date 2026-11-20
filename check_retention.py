import time

from iiot.storage import (
    init_db,
    downsample_1m,
    purge_older_than,
)

conn = init_db("iiot.db")
now = time.time()
before_ts = int(now // 60) * 60
count = downsample_1m(conn, before_ts)
print("Агрегованих рядків:", count)

# поріг установлено на 30 днів у минулому.
cutoff = now - 30 * 24 * 60 * 60
deleted = purge_older_than(conn, cutoff)
print("Видалених старих рядків:", deleted)
conn.close()