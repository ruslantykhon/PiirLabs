import random
import time

class PumpSimulator:
    def __init__(self, device_id = "pump-01", seed = None, wear_rate = 0.0):
        self.device_id = device_id
        self.rng = random.Random(seed)
        self.wear_rate = wear_rate
        self.wear = 0.0
        self.clog = 0.0
        self.running = True
        self._temp = 55.0

    def inject_fault(self, kind):
        if kind == "bearing":
            self.wear = max(self.wear, 0.7)
        elif kind == "clog":
            self.clog = max(self.clog, 0.6)
        else:
            raise ValueError(f"Unknown fault kind: {kind!r}")

    def step(self, dt = 0.1, now = None):
        ts = time.time() if now is None else now
        self.wear = min(1.0, self.wear + self.wear_rate)

        n_vib = self.rng.gauss(0, 0.15)
        n_temp = self.rng.gauss(0, 0.3)
        n_pres = self.rng.gauss(0, 0.05)
        n_cur = self.rng.gauss(0, 0.2)

        if self.running:
            self._temp = 55.0 + 25.0 * self.wear
            vib = 1.8 + 6.0 * self.wear + n_vib
            temp = self._temp + n_temp
            pres = 4.2 - 1.5 * self.clog + n_pres
            cur = 12.0 + 3.0 * self.wear + 4.0 * self.clog + n_cur
        else:
            k = min(1.0, dt / 300.0)
            self._temp += (25.0 - self._temp) * k
            vib = abs(n_vib) * 0.1
            temp = self._temp + n_temp * 0.1
            pres = 0.0
            cur = 0.0
        return {
            "device_id": self.device_id,
            "ts": ts,
            "running": self.running,
            "metrics":{
                "vibration_mm_s": round(max(vib, 0.0), 2),
                "temperature_c": round(temp, 1),
                "pressure_bar": round((max(pres, 0.0)), 2),
                "current_a": round(max(cur, 0.0), 1),
            },
        }