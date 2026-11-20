import math
from collections import deque

def ewma(values, alpha=0.3) -> list[float]:
    values = list(values)

    if not values:
        return []

    result = [float(values[0])]

    for value in values[1:]:
        smoothed = (
            alpha * value
            + (1 - alpha) * result[-1]
        )
        result.append(smoothed)

    return result

class RollingZ:
    def __init__(self, window=30, min_samples=10):
        if window <= 0:
            raise ValueError("window must be positive")
        self.window = window
        self.min_samples = min_samples
        self.values = deque(maxlen=window)

    def update(self, x) -> float | None:
        if len(self.values) < self.min_samples:
            z = None
        else:
            mean = sum(self.values) / len(self.values)
            variance = sum(
                (v - mean) ** 2
                for v in self.values
            ) / len(self.values)

            std = math.sqrt(variance)
            # Захист від ділення на нуль
            std = max(std, 1e-6)
            z = (x - mean) / std
        # Поточне значення додається тільки після обчислення z
        self.values.append(x)
        return z

def detect_anomalies(
    values,
    window=30,
    threshold=3.5
) -> list[int]:

    detector = RollingZ(window=window)
    anomalies = []
    for index, value in enumerate(values):
        z = detector.update(value)

        if z is not None and abs(z) > threshold:
            anomalies.append(index)

    return anomalies

def linear_trend(ts, values):
    ts = list(ts)
    values = list(values)

    if len(ts) != len(values):
        raise ValueError("ts and values must have equal length")

    if not ts:
        raise ValueError("Empty data")
    n = len(ts)
    mean_t = sum(ts) / n
    mean_y = sum(values) / n
    sxx = sum(
        (t - mean_t) ** 2
        for t in ts
    )

    if sxx == 0:
        slope = 0.0
    else:
        sxy = sum(
            (t - mean_t) * (y - mean_y)
            for t, y in zip(ts, values)
        )

        slope = sxy / sxx
    intercept = mean_y - slope * mean_t
    return slope, intercept

def estimate_rul(ts, values, limit) -> float | None:
    ts = list(ts)
    values = list(values)

    if not ts or not values:
        return None

    if values[-1] >= limit:
        return 0.0

    slope, intercept = linear_trend(ts, values)

    if slope <= 1e-12:
        return None

    crossing_time = (limit - intercept) / slope
    rul = crossing_time - ts[-1]
    return max(rul, 0.0)