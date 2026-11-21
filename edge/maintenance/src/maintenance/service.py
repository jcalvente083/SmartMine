import logging
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import ClassVar

from maintenance.domain.machine import (
    CommandOutcome,
    CommandResult,
    Machine,
    MachineState,
)
from maintenance.ports import LockoutStore, LockoutStoreError, SensorReader
from smartmine_common.ports import EventPublisher

logger = logging.getLogger(__name__)

type MachineAction = Callable[[Machine], CommandResult]


class MaintenanceService:
    _MACHINE_COMMANDS: ClassVar[Mapping[str, MachineAction]] = {
        "start": Machine.start,
        "stop": Machine.stop,
    }
    _LOCKOUT_COMMANDS: ClassVar[Mapping[str, MachineAction]] = {
        "iniciar_mantenimiento": Machine.start_maintenance,
        "finalizar_mantenimiento": Machine.end_maintenance,
    }
    _EMERGENCY_COMMANDS: ClassVar[Mapping[str, MachineAction]] = {
        "estop": Machine.emergency_stop,
        "reset": Machine.reset,
    }

    def __init__(
        self,
        machine_ids: Iterable[str],
        sensors: SensorReader,
        publisher: EventPublisher,
        lockout_store: LockoutStore,
    ) -> None:
        self._sensors = sensors
        self._publisher = publisher
        self._lockout_store = lockout_store
        self._machines = self._build_machines(machine_ids)

    def state_of(self, machine_id: str) -> MachineState:
        return self._machines[machine_id].state

    def is_locked_out(self, machine_id: str) -> bool:
        return self._machines[machine_id].locked_out

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
                    "bloqueo_loto": int(machine.locked_out),
                },
            )

    def handle_command(self, machine_id: str, command_id: str, command: str) -> None:
        """Aplica un comando a una máquina y responde siempre con un ACK."""
        machine = self._machines.get(machine_id)
        if machine is None:
            self._reject(machine_id, command_id, f"Máquina desconocida: {machine_id}")
            return

        lockout_action = self._LOCKOUT_COMMANDS.get(command)
        if lockout_action is not None:
            self._respond(machine_id, command_id, self._apply_lockout(machine, lockout_action))
            return

        action = self._MACHINE_COMMANDS.get(command)
        if action is None:
            self._reject(machine_id, command_id, f"Comando desconocido: {command}")
            return

        self._respond(machine_id, command_id, action(machine))

    def handle_emergency(self, command_id: str, command: str) -> None:
        action = self._EMERGENCY_COMMANDS.get(command)
        if action is None:
            return 

        for machine in self._machines.values():
            self._respond(machine.machine_id, command_id, action(machine))

    def _build_machines(self, machine_ids: Iterable[str]) -> dict[str, Machine]:
        machine_ids = list(machine_ids)  
        locked_ids = self._load_lockouts(machine_ids)
        return {
            machine_id: Machine(machine_id, MachineState.STOPPED, locked_out=True)
            if machine_id in locked_ids
            else Machine(machine_id)
            for machine_id in machine_ids
        }

    def _load_lockouts(self, machine_ids: list[str]) -> set[str]:
        try:
            return self._lockout_store.load()
        except LockoutStoreError:
            logger.critical(
                "No se pueden leer los candados LOTO: se bloquean todas las máquinas",
                exc_info=True,
            )
            return set(machine_ids)

    def _apply_lockout(self, machine: Machine, action: MachineAction) -> CommandResult:
        result = action(machine)
        if result.outcome != CommandOutcome.EXECUTED:
            return result  

        try:
            self._lockout_store.save(self._locked_machine_ids())
        except LockoutStoreError:
            logger.exception("No se pudo guardar el candado de %s", machine.machine_id)
            return CommandResult(
                CommandOutcome.ERROR,
                "Candado cambiado pero no guardado: un reinicio recupera el último estado guardado",
            )
        return result

    def _locked_machine_ids(self) -> set[str]:
        return {machine.machine_id for machine in self._machines.values() if machine.locked_out}

    def _respond(self, machine_id: str, command_id: str, result: CommandResult) -> None:
        self._publisher.publish_response(machine_id, command_id, result.outcome, result.detail)

    def _reject(self, machine_id: str, command_id: str, detail: str) -> None:
        self._respond(machine_id, command_id, CommandResult(CommandOutcome.REJECTED, detail))