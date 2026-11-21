import json
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MessageHandler = Callable[[str, dict], None]

TOPIC_ROOT = "smartmine"
QOS = 1


@dataclass(frozen=True)
class MqttSettings:
    host: str
    port: int
    client_id: str
    module: str
    node_id: str


class MqttAdapter:
    def __init__(self, settings: MqttSettings) -> None:
        self._settings = settings
        self._handlers: dict[str, MessageHandler] = {}
        self._status_topic = self._topic(settings.node_id, "estado")

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.client_id,
        )
        self._client.will_set(self._status_topic, "offline", qos=QOS, retain=True)
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    # --- Ciclo de vida -------------------------------------------------------------

    def subscribe(self, topic_filter: str, handler: MessageHandler) -> None:
        """Registra un manejador. Llamar antes de start(): se aplica al conectar."""
        self._handlers[topic_filter] = handler

    def start(self) -> None:
        self._client.connect_async(self._settings.host, self._settings.port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        if self._client.is_connected():
            info = self._client.publish(self._status_topic, "offline", qos=QOS, retain=True)
            info.wait_for_publish(timeout=2)
        self._client.disconnect()
        self._client.loop_stop()

    # --- Puerto EventPublisher ---------------------------------------------------------

    def publish_telemetry(self, device_id: str, values: Mapping[str, object]) -> None:
        self._publish(device_id, "telemetria", values)

    def publish_response(self, device_id: str, command_id: str, outcome: str, detail: str) -> None:
        self._publish(
            device_id,
            "respuesta",
            {"command_id": command_id, "resultado": outcome, "detalle": detail},
        )

    def publish_alert(self, device_id: str, alert: Mapping[str, object]) -> None:
        self._publish(device_id, "alerta", alert)

    # --- Traducción al contrato MQTT (docs/MQTT_TOPICS.md) ----------------------------

    def _publish(self, device_id: str, message_type: str, fields: Mapping[str, object]) -> None:
        payload = {
            "device_id": device_id,
            "timestamp": int(time.time() * 1000),
            **fields,
        }
        topic = self._topic(device_id, message_type)

        info = self._client.publish(
            topic, json.dumps(payload, ensure_ascii=False), qos=QOS, retain=False
        )
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.warning("Publicación en %s no enviada al momento (código %s)", topic, info.rc)

    def _topic(self, device_id: str, message_type: str) -> str:
        return f"{TOPIC_ROOT}/{self._settings.module}/{device_id}/{message_type}"

    # --- Callbacks de paho (se ejecutan en su hilo de red) -----------------------------

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            logger.error("Conexión rechazada por el broker: %s", reason_code)
            return
        logger.info("Conectado a %s:%s", self._settings.host, self._settings.port)

        for topic_filter in self._handlers:
            client.subscribe(topic_filter, qos=QOS)
        client.publish(self._status_topic, "online", qos=QOS, retain=True)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        logger.warning("Desconectado del broker (%s); paho reintentará", reason_code)

    def _on_message(self, client, userdata, message) -> None:
        try:
            payload = json.loads(message.payload)
        except (ValueError, UnicodeDecodeError):
            logger.warning("Mensaje no JSON en %s: descartado", message.topic)
            return
        if not isinstance(payload, dict):
            logger.warning("Mensaje en %s no es un objeto JSON: descartado", message.topic)
            return

        for topic_filter, handler in self._handlers.items():
            if mqtt.topic_matches_sub(topic_filter, message.topic):
                handler(message.topic, payload)
