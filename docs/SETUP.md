# 🛠️ Guía de preparación del entorno - SmartMine

Esta guía describe cómo preparar desde cero un equipo **Windows** para desarrollar y ejecutar SmartMine.

> Las rutas (`C:\Qt`, `C:\dev`) son las usadas durante el desarrollo. Si las cambias, adapta los comandos.

---

## 1. Requisitos

| Herramienta | Versión | Uso |
|---|---|---|
| [Git](https://git-scm.com/) | Reciente | Control de versiones (incluye Git Bash) |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Reciente | Infraestructura (Mosquitto, InfluxDB, Telegraf) |
| [Visual Studio Community](https://visualstudio.microsoft.com/) | 2026 | IDE y compilador MSVC del SCADA |
| [Qt](https://www.qt.io/download-open-source) | 6.11.3 | Framework del SCADA |
| [MQTT Explorer](https://mqtt-explorer.com/) | Reciente | Inspección y pruebas de topics MQTT (opcional) |

---

## 2. Infraestructura (Docker)

### 2.1. Configurar los secretos

Copia la plantilla de variables de entorno:

```powershell
Copy-Item .env.example .env
```

Edita `.env` con valores reales. Para generar el token de InfluxDB, desde **Git Bash**:

```bash
openssl rand -hex 32
```

> ⚠️ El fichero `.env` está en `.gitignore` y **nunca** debe subirse al repositorio.

### 2.2. Levantar los servicios

```powershell
docker compose up -d
docker compose ps
```

Mosquitto e InfluxDB deben aparecer como `(healthy)`, y Telegraf como `Up`.

### 2.3. Verificar la cadena MQTT → InfluxDB

1. Abre MQTT Explorer y conéctate a `localhost:1883`.
2. Publica en `smartmine/mantenimiento/trituradora-01/telemetria` un JSON según el [contrato MQTT](MQTT_TOPICS.md), con un `timestamp` actual en milisegundos. Desde PowerShell:
   ```powershell
   [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
   ```
3. Consulta el dato desde el contenedor de InfluxDB:
   ```powershell
   docker compose exec influxdb bash
   ```
   ```bash
   influx query 'from(bucket: "telemetria") |> range(start: -10m) |> filter(fn: (r) => r._measurement == "mantenimiento")'
   ```

La interfaz web de InfluxDB está disponible en `http://localhost:8086`.

> La configuración inicial de InfluxDB solo se aplica la primera vez (volumen vacío). Para empezar de cero: `docker compose down -v` (⚠️ borra todos los datos).

---

## 3. Entorno C++ / Qt

### 3.1. Visual Studio 2026

Instala Visual Studio Community 2026 con la carga de trabajo **"Desarrollo para el escritorio con C++"**. Para comprobar que las herramientas de C++ están instaladas:

```powershell
& "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property displayName
```

Instala también la extensión **Qt Visual Studio Tools** (*Extensiones → Administrar extensiones*) y configúrala con la ruta `C:\Qt\6.11.3\msvc2022_64`.

### 3.2. Qt 6.11.3

Con el instalador online de Qt (o `C:\Qt\MaintenanceTool.exe` → *Agregar o quitar componentes*), instala:

- **Qt for Development → Qt → Qt 6.11.3:**
  - MSVC 2022 64-bit
  - Additional Libraries → Qt Charts y Qt Graphs (el instalador añade sus dependencias automáticamente)
- **Qt for Development → Qt → Build Tools:** CMake y Ninja
- **Developer Tools:** Qt Creator (opcional, incluye Qt Designer)

> El kit de MSVC 2022 es compatible con el compilador de Visual Studio 2026: Microsoft mantiene la compatibilidad binaria de MSVC desde 2015.

### 3.3. Compilar Qt MQTT desde el código fuente

En la versión de código abierto, **Qt MQTT no está disponible en el instalador**, así que se compila desde su código fuente.

> 📄 **Licencia:** en su versión de código abierto, Qt MQTT se distribuye bajo **GPLv3**. Una aplicación que lo use y se distribuya debe ser también GPLv3.

**1. Descargar el código fuente** de la versión que coincide con Qt (fuera del repositorio del proyecto). En PowerShell:

```powershell
mkdir C:\dev
git clone --branch v6.11.3 --depth 1 https://github.com/qt/qtmqtt.git C:\dev\qtmqtt
```

> Los avisos `is not a commit!` y `detached HEAD` son normales al descargar una etiqueta de Qt.

**2. Abrir la consola de compilación de Visual Studio.** Desde el menú Inicio: **"x64 Native Tools Command Prompt for VS 2026"**. Los siguientes pasos se ejecutan en esta consola (`cmd`, no PowerShell).

**3. Añadir CMake y Ninja de Qt al PATH** de la sesión:

```cmd
set PATH=C:\Qt\Tools\CMake_64\bin;C:\Qt\Tools\Ninja;%PATH%
```

**4. Crear la carpeta de compilación:**

```cmd
mkdir C:\dev\qtmqtt-build
cd C:\dev\qtmqtt-build
```

**5. Configurar el módulo:**

```cmd
C:\Qt\6.11.3\msvc2022_64\bin\qt-configure-module.bat C:\dev\qtmqtt
```

> Los avisos sobre `pthread`, `Vulkan`, `Qt6TaskTree` y `WebSockets` son esperables y no afectan al uso de Qt MQTT sobre TCP.

**6. Compilar e instalar ambas configuraciones.** Con MSVC, una aplicación en Debug requiere las librerías en Debug, y una en Release las de Release:

```cmd
cmake --build . --config RelWithDebInfo
cmake --build . --config Debug
cmake --install . --config RelWithDebInfo
cmake --install . --config Debug
```

**7. Verificar:**

```cmd
dir C:\Qt\6.11.3\msvc2022_64\bin\Qt6Mqtt*.dll
```

Deben aparecer **dos** ficheros: `Qt6Mqtt.dll` (Release) y `Qt6Mqttd.dll` (Debug).