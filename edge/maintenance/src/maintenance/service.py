import logging
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import ClassVar

from maintenance.domain.machine import (
    CommandOutcome,
    CommandResult,
    Machine,
    MachineState,
)
from maintenance.domain.prediction import FailurePrediction
from maintenance.domain.reading import MachineReading
from maintenance.ports import FailurePredictor, LockoutStore, LockoutStoreError, SensorReader
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
        machines: Mapping[str, str],
        sensors: SensorReader,
        predictor: FailurePredictor,
        publisher: EventPublisher,
        lockout_store: LockoutStore,
        *,
        clock: Callable[[], float] = time.monotonic,
        alert_cooldown_s: float = 30.0,
    ) -> None:
        self._product_types = dict(machines)
        self._sensors = sensors
        self._predictor = predictor
        self._publisher = publisher
        self._lockout_store = lockout_store
        self._clock = clock
        self._alert_cooldown_s = alert_cooldown_s
        self._last_alert_at: dict[str, float] = {}  
        self._machines = self._build_machines(machines)

    def state_of(self, machine_id: str) -> MachineState:
        return self._machines[machine_id].state

    def is_locked_out(self, machine_id: str) -> bool:
        return self._machines[machine_id].locked_out

    def tick(self) -> None:
        for machine in self._machines.values():
            reading = self._sensors.read(machine.machine_id)

            prediction = None
            if machine.state == MachineState.OPERATING:
                prediction = self._predict(machine.machine_id, reading)
            else:
                reading = replace(reading, rotational_speed_rpm=0, torque_nm=0)

            telemetry = {
                "temperatura_aire_k": reading.air_temperature_k,
                "temperatura_proceso_k": reading.process_temperature_k,
                "velocidad_rpm": reading.rotational_speed_rpm,
                "torque_nm": reading.torque_nm,
                "desgaste_herramienta_min": reading.tool_wear_min,
                "modo_operacion": machine.state,
                "bloqueo_loto": int(machine.locked_out),
            }
            if prediction is not None:
                telemetry["probabilidad_fallo"] = round(prediction.probability, 4)
            self._publisher.publish_telemetry(machine.machine_id, telemetry)

            if prediction is not None:
                self._alert_if_needed(machine.machine_id, prediction)

    def handle_command(self, machine_id: str, command_id: str, command: str) -> None:
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

    def _predict(self, machine_id: str, reading: MachineReading) -> FailurePrediction | None:
        try:
            return self._predictor.predict(reading, self._product_types[machine_id])
        except Exception:
            logger.exception("Error al predecir el fallo de %s", machine_id)
            return None

    def _alert_if_needed(self, machine_id: str, prediction: FailurePrediction) -> None:
        if not prediction.is_failure_risk:
            return

        now = self._clock()
        last_alert_at = self._last_alert_at.get(machine_id)
        if last_alert_at is not None and now - last_alert_at < self._alert_cooldown_s:
            return

        self._last_alert_at[machine_id] = now
        self._publisher.publish_alert(machine_id, self._failure_alert(prediction))

    @staticmethod
    def _failure_alert(prediction: FailurePrediction) -> dict:
        return {
            "tipo": "riesgo_fallo",
            "categoria": "mantenimiento_predictivo",
            "gravedad": "alta",
            "mensaje": f"Riesgo de fallo de proceso: {prediction.probability * 100:.0f} %",
            "probabilidad": round(prediction.probability, 4),
            "umbral": round(prediction.threshold, 4),
            "causas": [
                {"variable": cause.feature, "contribucion": round(cause.contribution, 3)}
                for cause in prediction.top_contributions
            ],
        }

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