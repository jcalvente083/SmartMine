import logging
import queue
import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from maintenance.adapters.ai4i_simulator import Ai4iSimulator
from maintenance.adapters.json_lockout_store import JsonFileLockoutStore
from maintenance.adapters.lightgbm_predictor import LightGbmPredictor
from maintenance.ml.features import TYPE_CODES
from maintenance.service import MaintenanceService
from smartmine_common.config import ConfigError, env_float, env_int, env_list, env_str
from smartmine_common.mqtt_adapter import MqttAdapter, MqttSettings

logger = logging.getLogger("maintenance")

MODULE = "mantenimiento"
MACHINE_COMMAND_TOPIC = f"smartmine/{MODULE}/+/comando"
EMERGENCY_TOPIC = "smartmine/global/all/comando"

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PACKAGE_ROOT / "datasets" / "ai4i2020.csv"
DEFAULT_LOCKOUT_FILE = PACKAGE_ROOT / "data" / "candados.json"
DEFAULT_MODEL = PACKAGE_ROOT / "models" / "failure_model.txt"


@dataclass(frozen=True)
class InboundCommand:

    machine_id: str | None
    command_id: str
    command: str


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    machine_types = parse_machine_types(
        env_list("MACHINE_TYPES", "trituradora-01:H,cinta-02:L,molino-03:M")
    )
    tick_interval_s = env_float("TICK_INTERVAL_S", 1.0)
    dataset = Path(env_str("DATASET_PATH", str(DEFAULT_DATASET)))
    lockout_file = Path(env_str("LOCKOUT_FILE", str(DEFAULT_LOCKOUT_FILE)))
    model_path = Path(env_str("MODEL_PATH", str(DEFAULT_MODEL)))
    alert_cooldown_s = env_float("ALERT_COOLDOWN_S", 30.0)
    settings = MqttSettings(
        host=env_str("MQTT_HOST", "localhost"),
        port=env_int("MQTT_PORT", 1883),
        client_id=env_str("MQTT_CLIENT_ID", "edge-mantenimiento"),
        module=MODULE,
        node_id=env_str("NODE_ID", "nodo-mantenimiento"),
    )

    # --- Composición: adaptadores → servicio
    mqtt_adapter = MqttAdapter(settings)
    sensors = Ai4iSimulator(dataset, list(machine_types))
    predictor = LightGbmPredictor(model_path, model_path.with_suffix(".json"))
    lockout_store = JsonFileLockoutStore(lockout_file)
    service = MaintenanceService(
        machine_types,
        sensors,
        predictor,
        mqtt_adapter,
        lockout_store,
        alert_cooldown_s=alert_cooldown_s,
    )

    # --- El hilo de paho solo encola; el dominio se ejecuta únicamente en el hilo principal
    inbox: queue.Queue[InboundCommand] = queue.Queue()
    mqtt_adapter.subscribe(
        MACHINE_COMMAND_TOPIC,
        lambda topic, payload: inbox.put(parse_machine_command(topic, payload)),
    )
    mqtt_adapter.subscribe(
        EMERGENCY_TOPIC,
        lambda topic, payload: inbox.put(parse_emergency_command(payload)),
    )

    # --- Parada ordenada: "docker stop" envía SIGTERM; Ctrl+C, SIGINT
    stop_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())

    mqtt_adapter.start()
    logger.info(
        "Nodo de Mantenimiento en marcha con %d máquinas (modelo %s, candados en %s)",
        len(machine_types),
        model_path.name,
        lockout_file,
    )
    try:
        run_loop(service, inbox, tick_interval_s, stop_event)
    finally:
        mqtt_adapter.stop()
        logger.info("Nodo detenido")


def parse_machine_types(items: list[str]) -> dict[str, str]:

    machine_types: dict[str, str] = {}
    for item in items:
        machine_id, separator, product_type = item.partition(":")
        machine_id = machine_id.strip()
        product_type = product_type.strip()

        if not separator or not machine_id:
            raise ConfigError(f"MACHINE_TYPES: se esperaba 'id:tipo' y llegó '{item}'")
        if product_type not in TYPE_CODES:
            raise ConfigError(
                f"MACHINE_TYPES: el tipo '{product_type}' de {machine_id} no es L, M o H"
            )
        if machine_id in machine_types:
            raise ConfigError(f"MACHINE_TYPES: la máquina {machine_id} está repetida")

        machine_types[machine_id] = product_type
    return machine_types


def parse_machine_command(topic: str, payload: dict) -> InboundCommand:

    return InboundCommand(
        machine_id=topic.split("/")[2],
        command_id=str(payload.get("command_id", "")),
        command=str(payload.get("comando", "")),
    )


def parse_emergency_command(payload: dict) -> InboundCommand:
    return InboundCommand(
        machine_id=None,
        command_id=str(payload.get("command_id", "")),
        command=str(payload.get("comando", "")),
    )


def run_loop(
    service: MaintenanceService,
    inbox: queue.Queue[InboundCommand],
    tick_interval_s: float,
    stop_event: threading.Event,
) -> None:
    next_tick = time.monotonic() + tick_interval_s  
    while not stop_event.is_set():
        remaining = next_tick - time.monotonic()
        if remaining <= 0:
            service.tick()
            next_tick += tick_interval_s
            continue
        try:
            command = inbox.get(timeout=remaining)
        except queue.Empty:
            continue
        dispatch(service, command)


def dispatch(service: MaintenanceService, command: InboundCommand) -> None:
    if command.machine_id is None:
        service.handle_emergency(command.command_id, command.command)
    else:
        service.handle_command(command.machine_id, command.command_id, command.command)


if __name__ == "__main__":
    main()