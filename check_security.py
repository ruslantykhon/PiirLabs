import json
from iiot.security import (
    sign,
    verify,
    NonceCache,
    InvalidSignature,
    ExpiredError,
    ReplayError
)

secret = b"temporary-lab-test-secret"
topic = "plant/site1/line1/pump-01/telemetry"

payload = {
    "device_id": "pump-01",
    "metrics": {
        "vibration_mm_s": 5.1
    }
}

raw = sign(
    secret,
    topic,
    payload,
    ts=1000.0,
    nonce="test-nonce-001"
)

cache = NonceCache(ttl=60)
print("1. Перевірка правильного повідомлення")
result = verify(
    secret, topic, raw,
    now=1000.0, cache=cache
)

print("PASSED:", result)

print("\n2. Перевірка повторного повідомлення")

try:
    verify(
        secret, topic, raw,
        now=1001.0, cache=cache
    )
except ReplayError:
    print("PASSED: ReplayError")

print("\n3. Перевірка простроченого повідомлення")

try:
    verify(
        secret, topic, raw,
        now=1100.0
    )
except ExpiredError:
    print("PASSED: ExpiredError")

print("\n4. Перевірка зміненого повідомлення")
changed = json.loads(raw)
changed["payload"]["metrics"]["vibration_mm_s"] = 9.9

try:
    verify(
        secret,
        topic,
        json.dumps(changed).encode("utf-8"),
        now=1000.0
    )
except InvalidSignature:
    print("PASSED: InvalidSignature")