import logging

import pytest

from maintenance.domain.machine import MachineState
from maintenance.domain.reading import MachineReading
from maintenance.ports import LockoutStoreError
from maintenance.service import MaintenanceService

MACHINE_IDS = ["trituradora-01", "cinta-02"]


class FakeSensorReader:
    def __init__(self) -> None:
        self.reading = MachineReading(298.1, 308.6, 1551.0, 42.8, 108.0)

    def read(self, machine_id: str) -> MachineReading:
        return self.reading


class FakeEventPublisher:
    def __init__(self) -> None:
        self.telemetry: list[tuple[str, dict]] = []
        self.responses: list[tuple[str, str, str, str]] = []
        self.alerts: list[tuple[str, dict]] = []

    def publish_telemetry(self, device_id, values):
        self.telemetry.append((device_id, dict(values)))

    def publish_response(self, device_id, command_id, outcome, detail):
        self.responses.append((device_id, command_id, outcome, detail))

    def publish_alert(self, device_id, alert):
        self.alerts.append((device_id, dict(alert)))


class FakeLockoutStore:
    """Almacén de candados en memoria. Puede simular un fallo al leer o al escribir."""

    def __init__(
        self,
        locked: set[str] | None = None,
        fail_on_load: bool = False,
        fail_on_save: bool = False,
    ) -> None:
        self.locked = set(locked or ())
        self.fail_on_load = fail_on_load
        self.fail_on_save = fail_on_save
        self.saved: list[set[str]] = []  # Historial de guardados, para comprobar cuándo se escribe

    def load(self) -> set[str]:
        if self.fail_on_load:
            raise LockoutStoreError("Almacén de candados ilegible")
        return set(self.locked)

    def save(self, locked_machine_ids: set[str]) -> None:
        if self.fail_on_save:
            raise LockoutStoreError("No se pudo escribir el almacén de candados")
        self.locked = set(locked_machine_ids)
        self.saved.append(set(locked_machine_ids))


@pytest.fixture
def publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def store() -> FakeLockoutStore:
    return FakeLockoutStore()


@pytest.fixture
def service(publisher, store) -> MaintenanceService:
    return MaintenanceService(MACHINE_IDS, FakeSensorReader(), publisher, store)


# --- latido: telemetría ----------------------------------------------------------


def test_tick_publishes_telemetry_for_every_machine(service, publisher):
    service.tick()
    assert [device_id for device_id, _ in publisher.telemetry] == [
        "trituradora-01",
        "cinta-02",
    ]


def test_tick_telemetry_follows_mqtt_contract(service, publisher):
    service.tick()
    _, values = publisher.telemetry[0]
    assert values == {
        "temperatura_aire_k": 298.1,
        "temperatura_proceso_k": 308.6,
        "velocidad_rpm": 1551.0,
        "torque_nm": 42.8,
        "desgaste_herramienta_min": 108.0,
        "modo_operacion": "operando",
        "bloqueo_loto": 0,
    }


def test_stopped_machine_reports_zero_speed_and_torque(service, publisher):
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.tick()
    _, values = publisher.telemetry[0]
    assert values["velocidad_rpm"] == 0
    assert values["torque_nm"] == 0
    assert values["temperatura_aire_k"] == 298.1  # la temperatura no desaparece al parar
    assert values["modo_operacion"] == "parada"


# --- comandos por máquina --------------------------------------------------------


def test_stop_command_stops_machine_and_acknowledges(service, publisher):
    service.handle_command("trituradora-01", "cmd-1", "stop")
    assert service.state_of("trituradora-01") == MachineState.STOPPED
    assert publisher.responses == [("trituradora-01", "cmd-1", "ejecutado", "")]


def test_command_for_unknown_machine_is_rejected(service, publisher):
    service.handle_command("maquina-fantasma", "cmd-1", "stop")
    device_id, command_id, outcome, detail = publisher.responses[0]
    assert (device_id, command_id, outcome) == (
        "maquina-fantasma",
        "cmd-1",
        "rechazado",
    )
    assert detail


def test_unknown_command_is_rejected(service, publisher):
    service.handle_command("trituradora-01", "cmd-1", "despegar")
    _, _, outcome, detail = publisher.responses[0]
    assert outcome == "rechazado"
    assert detail
    assert service.state_of("trituradora-01") == MachineState.OPERATING


# --- emergencia global -------------------------------------------------------------


def test_emergency_stop_affects_every_machine(service, publisher):
    service.handle_emergency("cmd-e", "estop")
    assert service.state_of("trituradora-01") == MachineState.EMERGENCY
    assert service.state_of("cinta-02") == MachineState.EMERGENCY
    assert len(publisher.responses) == 2  # un ACK por máquina


def test_start_after_emergency_is_rejected(service, publisher):
    service.handle_emergency("cmd-e", "estop")
    service.handle_command("trituradora-01", "cmd-2", "start")
    _, _, outcome, _ = publisher.responses[-1]
    assert outcome == "rechazado"


def test_reset_leaves_every_machine_stopped(service):
    service.handle_emergency("cmd-e", "estop")
    service.handle_emergency("cmd-r", "reset")
    assert service.state_of("trituradora-01") == MachineState.STOPPED
    assert service.state_of("cinta-02") == MachineState.STOPPED


def test_unknown_emergency_command_is_ignored(service, publisher):
    service.handle_emergency("cmd-x", "otra-cosa")
    assert publisher.responses == []
    assert service.state_of("trituradora-01") == MachineState.OPERATING


# --- candado LOTO y su persistencia ------------------------------------------------


def test_start_maintenance_locks_machine_and_saves_lockouts(service, publisher, store):
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.handle_command("trituradora-01", "cmd-2", "iniciar_mantenimiento")
    assert service.is_locked_out("trituradora-01")
    assert store.saved == [{"trituradora-01"}]
    assert publisher.responses[-1] == ("trituradora-01", "cmd-2", "ejecutado", "")


def test_end_maintenance_unlocks_machine_and_saves_lockouts(service, store):
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.handle_command("trituradora-01", "cmd-2", "iniciar_mantenimiento")
    service.handle_command("trituradora-01", "cmd-3", "finalizar_mantenimiento")
    assert not service.is_locked_out("trituradora-01")
    assert store.saved[-1] == set()


def test_rejected_lockout_command_does_not_touch_the_store(service, publisher, store):
    service.handle_command("trituradora-01", "cmd-1", "iniciar_mantenimiento")  # está en marcha
    _, _, outcome, _ = publisher.responses[-1]
    assert outcome == "rechazado"
    assert store.saved == []


def test_lockouts_are_restored_on_startup(publisher):
    store = FakeLockoutStore(locked={"cinta-02"})
    service = MaintenanceService(MACHINE_IDS, FakeSensorReader(), publisher, store)

    # Un candado restaurado implica máquina parada: nunca vuelve del reinicio en marcha
    assert service.is_locked_out("cinta-02")
    assert service.state_of("cinta-02") == MachineState.STOPPED
    assert not service.is_locked_out("trituradora-01")

    service.handle_command("cinta-02", "cmd-1", "start")
    _, _, outcome, _ = publisher.responses[-1]
    assert outcome == "rechazado"


def test_unreadable_store_locks_every_machine(publisher, caplog):
    store = FakeLockoutStore(fail_on_load=True)
    with caplog.at_level(logging.CRITICAL):
        service = MaintenanceService(MACHINE_IDS, FakeSensorReader(), publisher, store)

    # Fail-safe: si no sabemos qué máquinas tienen candado, las bloqueamos todas
    assert all(service.is_locked_out(machine_id) for machine_id in MACHINE_IDS)
    assert any(record.levelno == logging.CRITICAL for record in caplog.records)


def test_save_failure_is_reported_as_error(publisher):
    store = FakeLockoutStore(fail_on_save=True)
    service = MaintenanceService(MACHINE_IDS, FakeSensorReader(), publisher, store)
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.handle_command("trituradora-01", "cmd-2", "iniciar_mantenimiento")

    _, _, outcome, detail = publisher.responses[-1]
    assert outcome == "error"
    assert detail
    # El candado se mantiene en memoria: ante la duda, la máquina sigue protegida
    assert service.is_locked_out("trituradora-01")