import csv
from collections.abc import Iterable
from pathlib import Path

from maintenance.domain.reading import MachineReading


class Ai4iSimulator:
    """Reproduce el dataset en bucle. Cada máquina tiene su propio cursor."""

    def __init__(self, csv_path: Path, machine_ids: Iterable[str]) -> None:
        self._rows = self._load(csv_path)

        ids = list(machine_ids)

        self._cursors = {
            machine_id: i * len(self._rows) // len(ids) for i, machine_id in enumerate(ids)
        }

    def read(self, machine_id: str) -> MachineReading:
        index = self._cursors[machine_id]
        self._cursors[machine_id] = (index + 1) % len(self._rows)
        return self._rows[index]

    @staticmethod
    def _load(csv_path: Path) -> list[MachineReading]:
        with csv_path.open(encoding="utf-8", newline="") as file:
            return [
                MachineReading(
                    air_temperature_k=float(row["Air temperature [K]"]),
                    process_temperature_k=float(row["Process temperature [K]"]),
                    rotational_speed_rpm=float(row["Rotational speed [rpm]"]),
                    torque_nm=float(row["Torque [Nm]"]),
                    tool_wear_min=float(row["Tool wear [min]"]),
                )
                for row in csv.DictReader(file)
            ]
