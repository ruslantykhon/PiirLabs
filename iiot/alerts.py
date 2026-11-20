from dataclasses import dataclass

@dataclass
class Rule:
    name: str
    metric: str
    high: float
    hysteresis: float = 0.0
    debounce: int = 3
    severity: str = "warning"

DEFAULT_RULES = [
    Rule(
        name="high_vibration",
        metric="vibration_mm_s",
        high=4.5,
        hysteresis=0.5,
        debounce=3,
        severity="critical"
    ),
    Rule(
        name="high_temperature",
        metric="temperature_c",
        high=80.0,
        hysteresis=3.0,
        debounce=5,
        severity="warning"
    )
]

class AlertEngine:
    def __init__(self, rules):
        self.rules = list(rules)
        self.states = {}

    def process(self, msg) -> list[dict]:
        events = []

        device_id = msg["device_id"]
        ts = msg["ts"]
        metrics = msg.get("metrics", {})

        for rule in self.rules:
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            key = (device_id, rule.name)

            if key not in self.states:
                self.states[key] = {
                    "active": False,
                    "count": 0
                }

            state = self.states[key]

            if not state["active"]:
                if value > rule.high:
                    state["count"] += 1
                else:
                    state["count"] = 0

                if state["count"] >= rule.debounce:
                    state["active"] = True
                    state["count"] = 0

                    events.append({
                        "rule": rule.name,
                        "device_id": device_id,
                        "metric": rule.metric,
                        "state": "raised",
                        "value": value,
                        "ts": ts,
                        "severity": rule.severity
                    })

            else:
                if value < rule.high - rule.hysteresis:
                    state["active"] = False
                    state["count"] = 0

                    events.append({
                        "rule": rule.name,
                        "device_id": device_id,
                        "metric": rule.metric,
                        "state": "cleared",
                        "value": value,
                        "ts": ts,
                        "severity": rule.severity
                    })
        return events