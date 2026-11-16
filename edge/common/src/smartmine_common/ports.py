from collections.abc import Mapping
from typing import Protocol

TelemetryValue = float | int | str


class EventPublisher(Protocol):
    def publish_telemetry(self, device_id: str, values: Mapping[str, TelemetryValue]) -> None: ...

    def publish_response(self, device_id: str, command_id: str, outcome: str, detail: str) -> None: ...

    def publish_alert(self, device_id: str, alert: Mapping[str, object]) -> None: ...