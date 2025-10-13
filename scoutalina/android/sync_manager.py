"""Sync manager for communicating with Flask backend.

TODO:
- Handle retries and background sync
"""

import json
from urllib import request as urllib_request


def send_event(server_base_url: str, event: dict) -> int:
    data = json.dumps(event).encode("utf-8")
    req = urllib_request.Request(
        url=f"{server_base_url}/api/v1/events",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req) as resp:  # nosec B310 (demo-only)
        return resp.status


