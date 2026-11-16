from typing import Protocol

from maintenance.domain.reading import MachineReading


class SensorReader(Protocol):
    def read(self, machine_id: str) -> MachineReading: ...