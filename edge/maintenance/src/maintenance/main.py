import logging
import queue
import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from maintenance.adapters.ai4i_simulator import Ai4iSimulator
from maintenance.service import MaintenanceService
from smartmine_common.config import env_float, env_int, env_list, env_str
from smartmine_common.mqtt_adapter import MqttAdapter, MqttSettings

logger = logging.getLogger("maintenance")

MODULE = "mantenimiento"
MACHINE_COMMAND_TOPIC = f"smartmine/{MODULE}/+/comando"
EMERGENCY_TOPIC = "smartmine/global/all/comando"

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "datasets" / "ai4i2020.csv"


@dataclass(frozen=True)
class InboundCommand:
    """Comando recibido por MQTT, ya traducido, pendiente de procesar en el hilo principal."""

    machine_id: str | None
    command_id: str
    command: str


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # --- Configuración (variables de entorno, con valores por defecto para desarrollo)
    machine_ids = env_list("MACHINE_IDS", "trituradora-01,cinta-02,molino-03")
    tick_interval_s = env_float("TICK_INTERVAL_S", 1.0)
    dataset = Path(env_str("DATASET_PATH", str(DEFAULT_DATASET)))
    settings = MqttSettings(
        host=env_str("MQTT_HOST", "localhost"),
        port=env_int("MQTT_PORT", 1883),
        client_id=env_str("MQTT_CLIENT_ID", "edge-mantenimiento"),
        module=MODULE,
        node_id=env_str("NODE_ID", "nodo-mantenimiento"),
    )

    # --- Composición: adaptadores → servicio
    mqtt_adapter = MqttAdapter(settings)
    sensors = Ai4iSimulator(dataset, machine_ids)
    service = MaintenanceService(machine_ids, sensors, mqtt_adapter)

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
    logger.info("Nodo de Mantenimiento en marcha con %d máquinas", len(machine_ids))
    try:
        run_loop(service, inbox, tick_interval_s, stop_event)
    finally:
        mqtt_adapter.stop()
        logger.info("Nodo detenido")


def parse_machine_command(topic: str, payload: dict) -> InboundCommand:
    """Traduce un comando de máquina. Nunca lanza: un payload raro se rechaza después.

    Se ejecuta en el hilo de paho: una excepción aquí podría tumbar el hilo de red.
    """
    return InboundCommand(
        machine_id=topic.split("/")[2],
        command_id=str(payload.get("command_id", "")),
        command=str(payload.get("comando", "")),
    )


def parse_emergency_command(payload: dict) -> InboundCommand:
    """Traduce un comando global de emergencia (afecta a todas las máquinas)."""
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
    next_tick = time.monotonic() + tick_interval_s  # Reloj que nunca va hacia atrás
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
