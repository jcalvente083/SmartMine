from dataclasses import dataclass
from enum import StrEnum


class MachineState(StrEnum):
    OPERATING = "operando"
    STOPPED = "parada"
    EMERGENCY = "emergencia"


class CommandOutcome(StrEnum):
    EXECUTED = "ejecutado"
    REJECTED = "rechazado"
    ERROR = "error"


@dataclass(frozen=True)
class CommandResult:
    outcome: CommandOutcome
    detail: str = ""


@dataclass
class Machine:
    machine_id: str
    state: MachineState = MachineState.OPERATING
    locked_out: bool = False

    def start(self) -> CommandResult:
        if self.state == MachineState.EMERGENCY:
            return CommandResult(CommandOutcome.REJECTED, "Emergencia activa: requiere rearme")
        if self.locked_out:
            return CommandResult(
                CommandOutcome.REJECTED, "Bloqueo LOTO activo: máquina en mantenimiento"
            )
        self.state = MachineState.OPERATING
        return CommandResult(CommandOutcome.EXECUTED)

    def stop(self) -> CommandResult:
        if self.state == MachineState.EMERGENCY:
            return CommandResult(CommandOutcome.REJECTED, "Emergencia activa: requiere rearme")
        self.state = MachineState.STOPPED
        return CommandResult(CommandOutcome.EXECUTED)

    def emergency_stop(self) -> CommandResult:
        self.state = MachineState.EMERGENCY
        return CommandResult(CommandOutcome.EXECUTED)

    def reset(self) -> CommandResult:
        if self.state != MachineState.EMERGENCY:
            return CommandResult(CommandOutcome.REJECTED, "No hay emergencia activa")
        self.state = MachineState.STOPPED
        return CommandResult(CommandOutcome.EXECUTED)

    def start_maintenance(self) -> CommandResult:
        if self.state == MachineState.OPERATING:
            return CommandResult(
                CommandOutcome.REJECTED,
                "Máquina en marcha: detenla antes de iniciar el mantenimiento",
            )
        self.locked_out = True
        return CommandResult(CommandOutcome.EXECUTED)

    def end_maintenance(self) -> CommandResult:
        if not self.locked_out:
            return CommandResult(CommandOutcome.REJECTED, "No hay mantenimiento activo")
        self.locked_out = False
        return CommandResult(CommandOutcome.EXECUTED)
