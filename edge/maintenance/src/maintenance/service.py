from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import ClassVar

from maintenance.domain.machine import (
    CommandOutcome,
    CommandResult,
    Machine,
    MachineState,
)
from maintenance.ports import SensorReader
from smartmine_common.ports import EventPublisher


class MaintenanceService:
    
    _MACHINE_COMMANDS: ClassVar[Mapping[str, Callable[[Machine], CommandResult]]] = {
        "start": Machine.start,
        "stop": Machine.stop,
    }
    _EMERGENCY_COMMANDS: ClassVar[Mapping[str, Callable[[Machine], CommandResult]]] = {
        "estop": Machine.emergency_stop,
        "reset": Machine.reset,
    }
   
    def __init__(
        self,
        machine_ids: Iterable[str],
        sensors: SensorReader,
        publisher: EventPublisher,
    ) -> None:
        self._machines = {machine_id: Machine(machine_id) for machine_id in machine_ids}
        self._sensors = sensors
        self._publisher = publisher

    def state_of(self, machine_id: str) -> MachineState:
        return self._machines[machine_id].state

    def tick(self) -> None:
        for machine in self._machines.values():
            reading = self._sensors.read(machine.machine_id)

            if machine.state != MachineState.OPERATING:
                reading = replace(reading, rotational_speed_rpm=0, torque_nm=0)

            self._publisher.publish_telemetry(
                machine.machine_id,
                {
                    "temperatura_aire_k": reading.air_temperature_k,
                    "temperatura_proceso_k": reading.process_temperature_k,
                    "velocidad_rpm": reading.rotational_speed_rpm,
                    "torque_nm": reading.torque_nm,
                    "desgaste_herramienta_min": reading.tool_wear_min,
                    "modo_operacion": machine.state,
                },
            )

    def handle_command(self, machine_id: str, command_id: str, command: str) -> None:
        machine = self._machines.get(machine_id)
        if machine is None:
            self._reject(machine_id, command_id, f"Máquina desconocida: {machine_id}")
            return

        action = self._MACHINE_COMMANDS.get(command)
        if action is None:
            self._reject(machine_id, command_id, f"Comando desconocido: {command}")
            return

        self._respond(machine_id, command_id, action(machine))

    def handle_emergency(self, command_id: str, command: str) -> None:
        action = self._EMERGENCY_COMMANDS.get(command)
        if action is None:
            return  # No es un comando de emergencia: se ignora

        for machine in self._machines.values():
            self._respond(machine.machine_id, command_id, action(machine))

    def _respond(self, machine_id: str, command_id: str, result: CommandResult) -> None:
        self._publisher.publish_response(machine_id, command_id, result.outcome, result.detail)

    def _reject(self, machine_id: str, command_id: str, detail: str) -> None:
        self._respond(machine_id, command_id, CommandResult(CommandOutcome.REJECTED, detail))
