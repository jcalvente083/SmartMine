# Contrato MQTT - SmartMine PoC

## Estructura Base (UNS Simplificado)
Patrón: `smartmine/<modulo>/<id_dispositivo>/<tipo_mensaje>`

## Tipos de Mensaje y Reglas de Calidad (QoS)

| Tipo de Mensaje | QoS | Retain | Descripción |
| :--- | :---: | :---: | :--- |
| `telemetria` | 1 | False | Datos numéricos y métricas periódicas para InfluxDB. |
| `alerta` | 1 | False | Eventos asíncronos y críticos (infracciones de EPIs, anomalías detectadas por reglas o modelos). |
| `comando` | 1 | False | Órdenes enviadas desde SCADA o Telegram (*Nota: Excepto estop/reset globales, ver Regla 4*). |
| `respuesta` | 1 | False | Confirmación (ACK) del nodo tras procesar un comando, incluyendo el `command_id`. |
| `estado` | 1 | True | Disponibilidad del nodo (`online`/`offline`, texto plano), con *Last Will*. Ver Regla 5. |

## Reglas Estructurales

1. **Telemetría plana y campos permitidos:** El payload de `telemetria` solo contendrá valores numéricos planos y una lista cerrada de campos de texto explícitamente permitidos: `modo_operacion`. Cualquier otro campo de texto no declarado será descartado por Telegraf. *(Nota: El `device_id` viaja en el payload para hacerlo autocontenido, pero InfluxDB extraerá la etiqueta principal directamente del topic MQTT).*
2. **Timestamps:** Todos los timestamps deben enviarse en formato **Epoch en milisegundos** (entero de 13 dígitos, ej. `1699530000123`), generados siempre por el nodo Edge.
3. **Trazabilidad de Comandos:** Todos los comandos deben incluir un identificador único en formato **UUID v4** válido (`command_id`) y un `timestamp` para auditoría y control de caducidad.
4. **Comando Global de Emergencia (Enclavado y Rearme):** El `estop` global se publica con `Retain=True` en `smartmine/global/all/comando`. El rearme requiere enviar un comando explícito de `reset` (también con `Retain=True` en el mismo topic) para sobrescribir y limpiar el estado retenido en el broker.
   - Al recibir `estop`, todos los actuadores pasan a emergencia y rechazan cualquier `start` o `stop`.
   - Al recibir `reset`, los actuadores quedan **detenidos**, nunca en marcha: el rearme no provoca por sí solo una puesta en marcha (ISO 13850).
   - Cada nodo responde con un ACK por actuador.
5. **Estado de los nodos:** Cada nodo publica su disponibilidad en `smartmine/<modulo>/<node_id>/estado` (ej. `smartmine/mantenimiento/nodo-mantenimiento/estado`). El payload es **texto plano**: `online` u `offline`. Siempre retenido y con QoS 1. El `offline` se publica como *Last Will* (caída inesperada) y también de forma explícita en una parada ordenada.
6. **Respuestas:** `device_id` y `timestamp` los añade siempre el nodo. El campo `detalle` explica el motivo cuando el resultado es `rechazado` o `error`, y puede ir vacío cuando es `ejecutado`.

## Suscripciones Clave
- **Telegraf (Base de datos):** `smartmine/+/+/telemetria`
- **SCADA (Tiempo real):** `smartmine/#`
- **Emergencia Global:** `smartmine/global/all/comando` (Todos los actuadores se suscriben aquí).

## Vocabulario Cerrado
- **Comandos permitidos (`comando`):** `start`, `stop`, `estop`, `reset`, `activar_aspersores`, `nueva_tarea`, `permitir`, `denegar`.
- **Resultados de respuesta (`resultado`):** `ejecutado`, `rechazado`, `error`.
- **Origen de los comandos (`origen`):** `scada_dashboard`, `telegram_bot`.
- **Modo de operación (`modo_operacion`) en Mantenimiento:** `operando`, `parada`, `emergencia`. Con la máquina parada o en emergencia, `velocidad_rpm` y `torque_nm` valen 0, pero las temperaturas y el desgaste se siguen enviando.
- **Parámetros específicos por comando:**
  - `nueva_tarea`: Requiere `destino_x` (número) y `destino_y` (número).
  - `permitir` / `denegar`: Requieren `solicitud_id` (UUID v4) para identificar la solicitud de acceso asociada.

---

## Ejemplos de Payload JSON por Módulo

### 1. MANTENIMIENTO: Telemetría y Comandos
**Topic (Telemetría):** `smartmine/mantenimiento/trituradora-01/telemetria`
```json
{
  "device_id": "trituradora-01",
  "timestamp": 1718000000123,
  "temperatura_aire_k": 298.1,
  "temperatura_proceso_k": 308.6,
  "velocidad_rpm": 1551,
  "torque_nm": 42.8,
  "desgaste_herramienta_min": 108,
  "modo_operacion": "operando"
}
```
**Topic (Comando - Parada individual):** `smartmine/mantenimiento/trituradora-01/comando`
```json
{
  "command_id": "6f1c2b7e-9a4d-4e3b-8c21-5d7f0a9e3b14",
  "timestamp": 1718000001000,
  "comando": "stop",
  "origen": "scada_dashboard"
}
```

### 2. MEDIO AMBIENTE: Telemetría y Comandos
**Topic (Telemetría):** `smartmine/ambiente/estacion-aire-01/telemetria`
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
**Topic (Telemetría):** `smartmine/logistica/camion-01/telemetria`
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
**Topic:** `smartmine/mantenimiento/trituradora-01/respuesta`
```json
{
  "device_id": "trituradora-01",
  "timestamp": 1718000001150,
  "command_id": "6f1c2b7e-9a4d-4e3b-8c21-5d7f0a9e3b14",
  "resultado": "rechazado",
  "detalle": "Emergencia activa: requiere rearme"
}
```

### 6. Estado del Nodo (Retained: True)
**Topic:** `smartmine/mantenimiento/nodo-mantenimiento/estado`
```
online
```
*(Texto plano, no JSON. El broker publica `offline` automáticamente si el nodo cae sin despedirse.)*

### 7. Comandos Globales de Emergencia (Enclavamiento y Rearme)
**Topic (Parada de Emergencia - Retained: True):** `smartmine/global/all/comando`
```json
{
  "command_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "timestamp": 1718000050123,
  "comando": "estop",
  "origen": "scada_dashboard"
}
```
**Topic (Rearme / Reset - Retained: True):** `smartmine/global/all/comando`
```json
{
  "command_id": "2b07b8fd-d3e2-40ea-aa60-e5e45b82d0a2",
  "timestamp": 1718000300123,
  "comando": "reset",
  "origen": "scada_dashboard"
}
```