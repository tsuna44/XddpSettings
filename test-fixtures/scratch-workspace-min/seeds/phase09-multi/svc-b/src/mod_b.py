import json
import urllib.request

SVC_A_VALIDATE_URL = "http://svc-a/validate"


def notify(value):
    if value == "":
        raise ValueError("value must not be empty")
    req = urllib.request.Request(
        SVC_A_VALIDATE_URL,
        data=json.dumps({"value": float(value)}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        json.load(resp)
