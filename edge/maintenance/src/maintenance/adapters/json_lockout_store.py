import json
import os
import tempfile
from pathlib import Path

from maintenance.ports import LockoutStoreError

_KEY = "maquinas_bloqueadas"


class JsonFileLockoutStore:

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> set[str]:
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return set()
        except OSError as error:
            raise LockoutStoreError(f"No se puede leer {self._path}") from error

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as error:
            raise LockoutStoreError(f"JSON corrupto en {self._path}") from error

        machine_ids = data.get(_KEY) if isinstance(data, dict) else None
        if not isinstance(machine_ids, list) or not all(isinstance(i, str) for i in machine_ids):
            raise LockoutStoreError(f"Formato inesperado en {self._path}")
        return set(machine_ids)

    def save(self, locked_machine_ids: set[str]) -> None:
        content = json.dumps({_KEY: sorted(locked_machine_ids)}, ensure_ascii=False, indent=2)
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_write(content)
        except OSError as error:
            raise LockoutStoreError(f"No se puede escribir {self._path}") from error

    def _atomic_write(self, content: str) -> None:
        fd, tmp_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=f".{self._path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  
            os.replace(tmp_path, self._path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)  
            raise