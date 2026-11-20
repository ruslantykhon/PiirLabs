import json
from collections import deque
import paho.mqtt.client as mqtt

def build_topic(site, line, device, kind="telemetry"):
    return f"plant/{site}/{line}/{device}/{kind}"

def encode(msg):
    return json.dumps(
        msg,
        separators=(",", ":"),
        sort_keys=True
    ).encode("utf-8")

def decode(raw):
    return json.loads(raw)

class OfflineBuffer:
    def __init__(self, maxlen):
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")

        self.items = deque()
        self.maxlen = maxlen
        self.dropped = 0

    def push(self, item):
        if len(self.items) >= self.maxlen:
            self.items.popleft()
            self.dropped += 1

        self.items.append(item)

    def drain(self):
        result = list(self.items)
        self.items.clear()
        return result

    def __len__(self):
        return len(self.items)

class Gateway:
    def __init__(
        self,
        client,
        site,
        line,
        device_id,
        buffer_size=1000
    ):
        self.client = client
        self.site = site
        self.line = line
        self.device_id = device_id

        self.connected = False
        self.buffer = OfflineBuffer(buffer_size)

        self.telemetry_topic = build_topic(
            site, line, device_id, "telemetry"
        )

        self.status_topic = build_topic(
            site, line, device_id, "status"
        )

        self.client.will_set(
            self.status_topic,
            encode({"state": "offline"}),
            qos=1,
            retain=True
        )

    def on_connect(self, *args, **kwargs):
        self.connected = True

        self.client.publish(
            self.status_topic,
            encode({"state": "online"}),
            qos=1,
            retain=True
        )

        for item in self.buffer.drain():
            self.client.publish(
                self.telemetry_topic,
                item,
                qos=1
            )

    def on_disconnect(self, *args, **kwargs):
        self.connected = False

    def publish(self, msg):
        if isinstance(msg, bytes):
            payload = msg
        else:
            payload = encode(msg)

        if self.connected:
            self.client.publish(
                self.telemetry_topic,
                payload,
                qos=1
            )
        else:
            self.buffer.push(payload)

def make_client(client_id, username=None, password=None):
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id
    )
    if username is not None:
        client.username_pw_set(username, password)
    return client