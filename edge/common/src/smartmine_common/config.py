import os


class ConfigError(RuntimeError):
    """Configuración ausente o inválida: el nodo no debe arrancar."""


def env_str(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise ConfigError(f"Falta la variable de entorno {name}")
    return value


def env_int(name: str, default: int | None = None) -> int:
    raw = env_str(name, None if default is None else str(default))
    try:
        return int(raw)
    except ValueError:
        raise ConfigError(f"{name} debe ser un entero (valor: {raw!r})") from None


def env_float(name: str, default: float | None = None) -> float:
    raw = env_str(name, None if default is None else str(default))
    try:
        return float(raw)
    except ValueError:
        raise ConfigError(f"{name} debe ser un número (valor: {raw!r})") from None


def env_list(name: str, default: str | None = None) -> list[str]:
    """Lista separada por comas, p. ej. 'trituradora-01,cinta-02'."""
    return [item.strip() for item in env_str(name, default).split(",") if item.strip()]
