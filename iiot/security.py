import hashlib
import hmac
import json
import os
import random
import threading
import time

class SecurityError(Exception):
    pass

class InvalidSignature(SecurityError):
    pass

class ExpiredError(SecurityError):
    pass

class ReplayError(SecurityError):
    pass

def canonical_json(payload):
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":")
    )

def sign(secret: bytes, topic, payload: dict,
         ts=None, nonce=None) -> bytes:

    if ts is None:
        ts = time.time()

    if nonce is None:
        nonce = os.urandom(8).hex()

    message = (
        f"{topic}\n"
        f"{ts}\n"
        f"{nonce}\n"
        f"{canonical_json(payload)}"
    )

    signature = hmac.new(
        secret,
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    envelope = {
        "payload": payload,
        "ts": ts,
        "nonce": nonce,
        "sig": signature
    }

    return canonical_json(envelope).encode("utf-8")

class NonceCache:
    def __init__(self, ttl=60):
        self.ttl = ttl
        self.seen = {}
        self.lock = threading.Lock()

    def check_and_add(self, nonce, now) -> bool:
        with self.lock:
            expired = [
                key for key, timestamp in self.seen.items()
                if now - timestamp > self.ttl
            ]

            for key in expired:
                del self.seen[key]

            if nonce in self.seen:
                return False

            self.seen[nonce] = now
            return True

def verify(secret, topic, raw,
           max_age=30, cache=None, now=None) -> dict:
    if now is None:
        now = time.time()

    try:
        envelope = json.loads(raw)
        if not isinstance(envelope, dict):
            raise ValueError("Invalid envelope")

        payload = envelope["payload"]
        ts = envelope["ts"]
        nonce = envelope["nonce"]
        signature = envelope["sig"]

        if not isinstance(payload, dict):
            raise ValueError("Invalid payload")
        if not isinstance(ts, (int, float)) or isinstance(ts, bool):
            raise ValueError("Invalid timestamp")
        if not isinstance(nonce, str) or not nonce:
            raise ValueError("Invalid nonce")
        if not isinstance(signature, str):
            raise ValueError("Invalid signature")

    except (ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise InvalidSignature(
            "Invalid JSON or envelope"
        ) from exc

    message = (
        f"{topic}\n"
        f"{ts}\n"
        f"{nonce}\n"
        f"{canonical_json(payload)}"
    )

    expected = hmac.new(
        secret,
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise InvalidSignature("Signature mismatch")
    if abs(now - ts) > max_age:
        raise ExpiredError("Message expired")
    if cache is not None:
        if not cache.check_and_add(nonce, now):
            raise ReplayError("Repeated nonce")
    return payload

def backoff_delays(
    base=1.0,
    factor=2.0,
    cap=60.0,
    jitter=0.0,
    rng=None
):
    if rng is None:
        rng = random.Random()
    delay = base
    while True:
        current = min(delay, cap)

        if jitter > 0:
            current *= 1 + rng.uniform(-jitter, jitter)
        yield current
        delay = min(delay * factor, cap)

def generate_acl(
    devices,
    ingest_user="ingest",
    alert_user="alerts"
) -> str:

    lines = []
    for device in devices:
        lines.extend([
            f"user {device}",
            f"topic write plant/+/+/{device}/#",
            ""
        ])

    lines.extend([
        f"user {ingest_user}",
        "topic read plant/#",
        "",
        f"user {alert_user}",
        "topic read plant/+/+/+/telemetry",
        "topic write plant/+/+/+/alerts",
        ""
    ])
    return "\n".join(lines)