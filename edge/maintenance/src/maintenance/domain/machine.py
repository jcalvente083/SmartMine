from dataclasses import dataclass
from enum import StrEnum


class MachineState(StrEnum):
    OPERATING = "operando"
    STOPPED = "parada"
    EMERGENCY = "emergencia"


class CommandOutcome(StrEnum):
    EXECUTED = "ejecutado"
    REJECTED = "rechazado"


@dataclass(frozen=True)
class CommandResult:
    outcome: CommandOutcome
    detail: str = ""


@dataclass
class Machine:
    machine_id: str
    state: MachineState = MachineState.OPERATING

    def start(self) -> CommandResult:
        if self.state == MachineState.EMERGENCY:
            return CommandResult(
                CommandOutcome.REJECTED, "Emergencia activa: requiere rearme"
            )
        else:
            self.state = MachineState.OPERATING
            return CommandResult(CommandOutcome.EXECUTED)

    def stop(self) -> CommandResult:
        if self.state == MachineState.EMERGENCY:
            return CommandResult(
                CommandOutcome.REJECTED, "Emergencia activa: requiere rearme"
            )
        self.state = MachineState.STOPPED
        return CommandResult(CommandOutcome.EXECUTED)

    def emergency_stop(self) -> CommandResult:
        self.state = MachineState.EMERGENCY
        return CommandResult(CommandOutcome.EXECUTED)

    def reset(self) -> CommandResult:
        if self.state != MachineState.EMERGENCY:
            return CommandResult(CommandOutcome.REJECTED, "no hay emergencia activa")
        else:
            self.state = MachineState.STOPPED
            return CommandResult(CommandOutcome.EXECUTED)
