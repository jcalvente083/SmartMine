# Contrato MQTT - SmartMine PoC

## Estructura Base (UNS Simplificado)
Patrón: `smartmine/<modulo>/<id_dispositivo>/<tipo_mensaje>`

## Tipos de Mensaje y Reglas de Calidad (QoS)

| Tipo de Mensaje | QoS | Retain | Descripción |
| :--- | :---: | :---: | :--- |
| `telemetria` | 1 | False | Datos numéricos y métricas periódicas para InfluxDB. |
| `alerta` | 1 | False | Eventos asíncronos y críticos (infracciones de EPIs, anomalías detectadas por reglas). |
| `comando` | 1 | False | Órdenes enviadas desde SCADA o Telegram (*Nota: Excepto estop/reset globales, ver Regla 4*). |
| `respuesta` | 1 | False | Confirmación (ACK) del nodo tras procesar un comando, incluyendo el `command_id`. |
| `estado` | 1 | True | Mensajes LWT (online/offline) retenidos para visibilidad inmediata al arrancar el SCADA. |

## Reglas Estructurales

1. **Telemetría plana y campos permitidos:** El payload de `telemetria` solo contendrá valores numéricos planos y una lista cerrada de campos de texto explícitamente permitidos: `modo_operacion`. Cualquier otro campo de texto no declarado será descartado por Telegraf. *(Nota: El `device_id` viaja en el payload para hacerlo autocontenido, pero InfluxDB extraerá la etiqueta principal directamente del topic MQTT).*
2. **Timestamps:** Todos los timestamps deben enviarse en formato **Epoch en milisegundos** (entero de 13 dígitos, ej. `1699530000123`), generados siempre por el nodo Edge.
3. **Trazabilidad de Comandos:** Todos los comandos deben incluir un identificador único en formato **UUID v4** válido (`command_id`) y un `timestamp` para auditoría y control de caducidad.
4. **Comando Global de Emergencia (Enclavado y Rearme):** El `estop` global se publica con `Retain=True` en `smartmine/global/all/comando`. El rearme requiere enviar un comando explícito de `reset` (también con `Retain=True` en el mismo topic) para sobrescribir y limpiar el estado retenido en el broker.

## Suscripciones Clave
- **Telegraf (Base de datos):** `smartmine/+/+/telemetria`
- **SCADA (Tiempo real):** `smartmine/#`
- **Emergencia Global:** `smartmine/global/all/comando` (Todos los actuadores se suscriben aquí).

## Vocabulario Cerrado
- **Comandos permitidos (`comando`):** `start`, `stop`, `estop`, `reset`, `activar_aspersores`, `nueva_tarea`, `permitir`, `denegar`.
- **Resultados de respuesta (`resultado`):** `ejecutado`, `rechazado`, `error`.
- **Parámetros específicos por comando:**
  - `nueva_tarea`: Requiere `destino_x` (número) y `destino_y` (número).
  - `permitir` / `denegar`: Requieren `solicitud_id` (UUID v4) para identificar la solicitud de acceso asociada.

---

## Ejemplos de Payload JSON por Módulo

### 1. MANTENIMIENTO: Telemetria
**Topic:** `smartmine/mantenimiento/trituradora-01/telemetria`
```json
{
  "device_id": "trituradora-01",
  "timestamp": 1718000000123,
  "temperatura_aire_k": 298.1,
  "temperatura_proceso_k": 308.6,
  "velocidad_rpm": 1551,
  "torque_nm": 42.8,
  "modo_operacion": "operando"
}
```

### 2. MEDIO AMBIENTE: Telemetria y Comandos
**Topic (Telemetria):** `smartmine/ambiente/estacion-aire-01/telemetria`
```json
{
  "device_id": "estacion-aire-01",
  "timestamp": 1718000000123,
  "polvo_pm10": 150.5,
  "humedad_pct": 35.2,
  "modo_operacion": "monitoreo"
}
```
**Topic (Comando):** `smartmine/ambiente/estacion-aire-01/comando`
```json
{
  "command_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "timestamp": 1718000001000,
  "comando": "activar_aspersores",
  "origen": "scada_dashboard"
}
```

### 3. SEGURIDAD: Alerta de Acceso e Infracción de EPIs
**Topic (Alerta):** `smartmine/seguridad/cam-acceso-norte/alerta`
```json
{
  "device_id": "cam-acceso-norte",
  "timestamp": 1718000000123,
  "solicitud_id": "8c554522-8356-4c4f-9e7f-7a9159021272",
  "infraccion_detectada": 1,
  "tipo_falta": "sin_chaleco",
  "mensaje": "Operario detectado sin chaleco de alta visibilidad en acceso norte."
}
```
**Topic (Comando - Permitir/Denegar):** `smartmine/seguridad/cam-acceso-norte/comando`
```json
{
  "command_id": "07876e23-6be7-4bfd-9c38-e9f8bf744dee",
  "timestamp": 1718000002000,
  "comando": "denegar",
  "solicitud_id": "8c554522-8356-4c4f-9e7f-7a9159021272",
  "origen": "telegram_bot"
}
```

### 4. LOGÍSTICA: Posición del Camión (Multiagente)
**Topic (Telemetria):** `smartmine/logistica/camion-01/telemetria`
```json
{
  "device_id": "camion-01",
  "timestamp": 1718000000123,
  "pos_x": 12.5,
  "pos_y": 45.2,
  "velocidad_kmh": 22.0,
  "bateria_pct": 88.0,
  "modo_operacion": "en_ruta"
}
```
**Topic (Comando - Asignar Tarea con Parámetros):** `smartmine/logistica/camion-01/comando`
```json
{
  "command_id": "d3b07384-d113-4c4e-9644-8d9987820468",
  "timestamp": 1718000003000,
  "comando": "nueva_tarea",
  "destino_x": 80.0,
  "destino_y": 10.0,
  "origen": "scada_dashboard"
}
```

### 5. Respuesta / ACK Genérica (Nodo -> SCADA)
**Topic:** `smartmine/logistica/camion-01/respuesta`
```json
{
  "command_id": "d3b07384-d113-4c4e-9644-8d9987820468",
  "resultado": "ejecutado",
  "timestamp": 1718000003150,
  "detalle": "Nueva ruta recalculada hacia Zona Norte"
}
```

### 6. Comandos Globales de Emergencia (Enclavamiento y Rearme)
**Topic (Parada de Emergencia - Retained: True):** `smartmine/global/all/comando`
```json
{
  "command_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "timestamp": 1718000050123,
  "comando": "estop",
  "origen": "boton_seta_ui"
}
```
**Topic (Rearme / Reset - Retained: True):** `smartmine/global/all/comando`
```json
{
  "command_id": "2b07b8fd-d3e2-40ea-aa60-e5e45b82d0a2",
  "timestamp": 1718000300123,
  "comando": "reset",
  "origen": "admin_ui"
}
```