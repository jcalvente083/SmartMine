import logging

import pytest

from maintenance.domain.machine import MachineState
from maintenance.domain.prediction import FailurePrediction, FeatureContribution
from maintenance.domain.reading import MachineReading
from maintenance.ports import LockoutStoreError
from maintenance.service import MaintenanceService

MACHINES = {"trituradora-01": "H", "cinta-02": "L"}
MACHINE_IDS = list(MACHINES)
THRESHOLD = 0.7


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

    def __init__(
        self,
        locked: set[str] | None = None,
        fail_on_load: bool = False,
        fail_on_save: bool = False,
    ) -> None:
        self.locked = set(locked or ())
        self.fail_on_load = fail_on_load
        self.fail_on_save = fail_on_save
        self.saved: list[set[str]] = [] 

    def load(self) -> set[str]:
        if self.fail_on_load:
            raise LockoutStoreError("Almacén de candados ilegible")
        return set(self.locked)

    def save(self, locked_machine_ids: set[str]) -> None:
        if self.fail_on_save:
            raise LockoutStoreError("No se pudo escribir el almacén de candados")
        self.locked = set(locked_machine_ids)
        self.saved.append(set(locked_machine_ids))


class FakePredictor:
    """Predictor con la probabilidad fijada por tipo de producto. Puede simular un fallo."""

    def __init__(self) -> None:
        self.probabilities = {"L": 0.1, "M": 0.1, "H": 0.1}
        self.fail = False
        self.calls: list[str] = []  

    def predict(self, reading: MachineReading, product_type: str) -> FailurePrediction:
        self.calls.append(product_type)
        if self.fail:
            raise RuntimeError("El modelo ha fallado")
        return FailurePrediction(
            probability=self.probabilities[product_type],
            threshold=THRESHOLD,
            top_contributions=(
                FeatureContribution("power_w", 1.2345),
                FeatureContribution("torque_nm", 0.4321),
            ),
        )


class FakeClock:
    """Reloj controlado por la prueba: avanzar 30 s no cuesta esperar 30 s."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def store() -> FakeLockoutStore:
    return FakeLockoutStore()


@pytest.fixture
def predictor() -> FakePredictor:
    return FakePredictor()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def build_service(publisher, store, predictor=None, clock=None) -> MaintenanceService:
    return MaintenanceService(
        MACHINES,
        FakeSensorReader(),
        predictor or FakePredictor(),
        publisher,
        store,
        clock=clock or FakeClock(),
        alert_cooldown_s=30.0,
    )


@pytest.fixture
def service(publisher, store, predictor, clock) -> MaintenanceService:
    return build_service(publisher, store, predictor, clock)


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
        "probabilidad_fallo": 0.1,
    }


def test_stopped_machine_reports_zero_speed_and_torque(service, publisher):
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.tick()
    _, values = publisher.telemetry[0]
    assert values["velocidad_rpm"] == 0
    assert values["torque_nm"] == 0
    assert values["temperatura_aire_k"] == 298.1  
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
    assert len(publisher.responses) == 2  


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
    service.handle_command("trituradora-01", "cmd-1", "iniciar_mantenimiento") 
    _, _, outcome, _ = publisher.responses[-1]
    assert outcome == "rechazado"
    assert store.saved == []


def test_lockouts_are_restored_on_startup(publisher):
    service = build_service(publisher, FakeLockoutStore(locked={"cinta-02"}))

    assert service.is_locked_out("cinta-02")
    assert service.state_of("cinta-02") == MachineState.STOPPED
    assert not service.is_locked_out("trituradora-01")

    service.handle_command("cinta-02", "cmd-1", "start")
    _, _, outcome, _ = publisher.responses[-1]
    assert outcome == "rechazado"


def test_unreadable_store_locks_every_machine(publisher, caplog):
    with caplog.at_level(logging.CRITICAL):
        service = build_service(publisher, FakeLockoutStore(fail_on_load=True))

    assert all(service.is_locked_out(machine_id) for machine_id in MACHINE_IDS)
    assert any(record.levelno == logging.CRITICAL for record in caplog.records)


def test_save_failure_is_reported_as_error(publisher):
    service = build_service(publisher, FakeLockoutStore(fail_on_save=True))
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.handle_command("trituradora-01", "cmd-2", "iniciar_mantenimiento")

    _, _, outcome, detail = publisher.responses[-1]
    assert outcome == "error"
    assert detail
    assert service.is_locked_out("trituradora-01")


# --- predicción de fallos y alertas ------------------------------------------------


def test_prediction_uses_each_machine_product_type(service, predictor):
    service.tick()
    assert predictor.calls == ["H", "L"]


def test_only_operating_machines_are_predicted(service, predictor):
    service.handle_command("cinta-02", "cmd-1", "stop")
    service.tick()
    assert predictor.calls == ["H"]


def test_stopped_machine_telemetry_has_no_failure_probability(service, publisher):
    service.handle_command("trituradora-01", "cmd-1", "stop")
    service.tick()
    _, values = publisher.telemetry[0]
    assert "probabilidad_fallo" not in values


def test_no_alert_below_threshold(service, publisher):
    service.tick()
    assert publisher.alerts == []


def test_failure_risk_publishes_alert_following_contract(service, publisher, predictor):
    predictor.probabilities["H"] = 0.8312345
    service.tick()
    assert publisher.alerts == [
        (
            "trituradora-01",
            {
                "tipo": "riesgo_fallo",
                "categoria": "mantenimiento_predictivo",
                "gravedad": "alta",
                "mensaje": "Riesgo de fallo de proceso: 83 %",
                "probabilidad": 0.8312,
                "umbral": 0.7,
                "causas": [
                    {"variable": "power_w", "contribucion": 1.234},
                    {"variable": "torque_nm", "contribucion": 0.432},
                ],
            },
        )
    ]


def test_alert_is_not_repeated_during_cooldown(service, publisher, predictor, clock):
    predictor.probabilities["H"] = 0.9
    service.tick()
    clock.now += 29.9
    service.tick()
    assert len(publisher.alerts) == 1


def test_alert_is_repeated_after_cooldown(service, publisher, predictor, clock):
    predictor.probabilities["H"] = 0.9
    service.tick()
    clock.now += 30.0
    service.tick()
    assert len(publisher.alerts) == 2


def test_cooldown_is_per_machine(service, publisher, predictor, clock):
    predictor.probabilities["H"] = 0.9
    service.tick()  
    clock.now += 10.0
    predictor.probabilities["L"] = 0.9
    service.tick()  
    assert [device_id for device_id, _ in publisher.alerts] == ["trituradora-01", "cinta-02"]


def test_predictor_failure_does_not_stop_telemetry(service, publisher, predictor, caplog):
    predictor.fail = True
    with caplog.at_level(logging.ERROR):
        service.tick()

    assert len(publisher.telemetry) == 2
    assert "probabilidad_fallo" not in publisher.telemetry[0][1]
    assert publisher.alerts == []
    assert any(record.levelno == logging.ERROR for record in caplog.records)