from pathlib import Path
from iiot.security import generate_acl

devices = ["pump-01", "pump-02"]
site = "kyiv"
line = "line1"
acl = generate_acl(devices)

# Конкретизуємо топіки для двох насосів.
for device in devices:
    acl = acl.replace(
        f"topic write plant/+/+/{device}/#",
        f"topic write plant/{site}/{line}/{device}/#"
    )

acl = acl.replace(
    "topic read plant/#",
    "topic read plant/#\ntopic write health/broker"
)

acl = acl.replace(
    "topic write plant/+/+/+/alerts",
    "\n".join(
        f"topic write plant/{site}/{line}/{device}/alerts"
        for device in devices
    )
)

path = Path(__file__).with_name("acl")
path.write_text(acl, encoding="utf-8")
print("ACL generated:", path)