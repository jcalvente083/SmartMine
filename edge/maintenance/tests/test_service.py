import pytest

from maintenance.domain.machine import MachineState
from maintenance.domain.reading import MachineReading
from maintenance.service import MaintenanceService


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


@pytest.fixture
def publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def service(publisher) -> MaintenanceService:
    return MaintenanceService(["trituradora-01", "cinta-02"], FakeSensorReader(), publisher)


# --- latido: telemetría ----------------------------------------------------------

def test_tick_publishes_telemetry_for_every_machine(service, publisher):
    service.tick()
    assert [device_id for device_id, _ in publisher.telemetry] == ["trituradora-01", "cinta-02"]


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
    assert (device_id, command_id, outcome) == ("maquina-fantasma", "cmd-1", "rechazado")
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