"""Puertos del nodo de Mantenimiento: lo que el servicio necesita del exterior.

Solo contratos. Las implementaciones viven en adapters/ (y los dobles, en tests/).
"""

from typing import Protocol

from maintenance.domain.prediction import FailurePrediction
from maintenance.domain.reading import MachineReading


class SensorReader(Protocol):
    """Fuente de lecturas de sensores de una máquina (simulador o sensores reales)."""

    def read(self, machine_id: str) -> MachineReading:
        """Devuelve la lectura actual de la máquina indicada."""
        ...


class FailurePredictor(Protocol):
    """Modelo que estima el riesgo de fallo de proceso a partir de una lectura."""

    def predict(self, reading: MachineReading, product_type: str) -> FailurePrediction:
        """Devuelve la probabilidad de fallo y sus causas principales.

        Args:
            reading: lectura de sensores de una máquina en marcha.
            product_type: calidad del producto que procesa la máquina ("L", "M" o "H").
        """
        ...


class LockoutStoreError(Exception):
    """El almacén de candados no se puede leer o escribir."""


class LockoutStore(Protocol):
    """Almacén persistente de los candados LOTO.

    Permite que un candado sobreviva a un reinicio del nodo: nadie debe poder
    arrancar una máquina en mantenimiento solo porque el contenedor se reinició.
    """

    def load(self) -> set[str]:
        """Devuelve los ids de las máquinas con candado.

        Si el almacén aún no existe (primer arranque), devuelve un conjunto vacío.

        Raises:
            LockoutStoreError: si el almacén existe pero no se puede leer.
        """
        ...

    def save(self, locked_machine_ids: set[str]) -> None:
        """Guarda el conjunto completo de máquinas con candado, sustituyendo al anterior.

        Raises:
            LockoutStoreError: si no se puede escribir.
        """
        ...