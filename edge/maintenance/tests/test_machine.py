from maintenance.domain.machine import CommandOutcome, Machine, MachineState


def make_machine(state: MachineState = MachineState.OPERATING) -> Machine:
    return Machine(machine_id="trituradora-01", state=state)


def test_new_machine_is_operating_by_default():
    assert Machine(machine_id="trituradora-01").state == MachineState.OPERATING


# --- stop ---------------------------------------------------------------------


def test_stop_operating_machine_stops_it():
    machine = make_machine(MachineState.OPERATING)
    result = machine.stop()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.state == MachineState.STOPPED


def test_stop_already_stopped_machine_is_executed_without_change():
    machine = make_machine(MachineState.STOPPED)
    result = machine.stop()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.state == MachineState.STOPPED


def test_stop_during_emergency_is_rejected():
    machine = make_machine(MachineState.EMERGENCY)
    result = machine.stop()
    assert result.outcome == CommandOutcome.REJECTED
    assert result.detail
    assert machine.state == MachineState.EMERGENCY


# --- start --------------------------------------------------------------------


def test_start_stopped_machine_starts_it():
    machine = make_machine(MachineState.STOPPED)
    result = machine.start()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.state == MachineState.OPERATING


def test_start_already_operating_machine_is_executed_without_change():
    machine = make_machine(MachineState.OPERATING)
    result = machine.start()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.state == MachineState.OPERATING


def test_start_during_emergency_is_rejected():
    machine = make_machine(MachineState.EMERGENCY)
    result = machine.start()
    assert result.outcome == CommandOutcome.REJECTED
    assert result.detail
    assert machine.state == MachineState.EMERGENCY


# --- emergencia y rearme --------------------------------------------------------


def test_emergency_stop_from_operating_enters_emergency():
    machine = make_machine(MachineState.OPERATING)
    result = machine.emergency_stop()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.state == MachineState.EMERGENCY


def test_emergency_stop_from_stopped_enters_emergency():
    machine = make_machine(MachineState.STOPPED)
    machine.emergency_stop()
    assert machine.state == MachineState.EMERGENCY


def test_reset_leaves_machine_stopped_not_operating():
    machine = make_machine(MachineState.EMERGENCY)
    result = machine.reset()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.state == MachineState.STOPPED


def test_reset_without_emergency_is_rejected():
    machine = make_machine(MachineState.OPERATING)
    result = machine.reset()
    assert result.outcome == CommandOutcome.REJECTED
    assert machine.state == MachineState.OPERATING


# --- Bloqueo LOTO (mantenimiento) -------------------------------------------------


def test_new_machine_is_not_locked_out():
    assert make_machine().locked_out is False


def test_start_maintenance_on_stopped_machine_locks_it():
    machine = make_machine(MachineState.STOPPED)
    result = machine.start_maintenance()
    assert result.outcome == CommandOutcome.EXECUTED
    assert machine.locked_out


def test_start_maintenance_on_operating_machine_is_rejected():
    machine = make_machine(MachineState.OPERATING)
    result = machine.start_maintenance()
    assert result.outcome == CommandOutcome.REJECTED
    assert result.detail
    assert not machine.locked_out


def test_start_maintenance_is_allowed_during_emergency():
    machine = make_machine(MachineState.EMERGENCY)
    assert machine.start_maintenance().outcome == CommandOutcome.EXECUTED
    assert machine.locked_out


def test_start_maintenance_twice_is_executed_without_change():
    machine = make_machine(MachineState.STOPPED)
    machine.start_maintenance()
    assert machine.start_maintenance().outcome == CommandOutcome.EXECUTED
    assert machine.locked_out


def test_start_is_rejected_while_locked_out():
    machine = make_machine(MachineState.STOPPED)
    machine.start_maintenance()
    result = machine.start()
    assert result.outcome == CommandOutcome.REJECTED
    assert result.detail
    assert machine.state == MachineState.STOPPED


def test_lockout_survives_emergency_and_reset():
    machine = make_machine(MachineState.STOPPED)
    machine.start_maintenance()
    machine.emergency_stop()
    machine.reset()
    assert machine.state == MachineState.STOPPED
    assert machine.locked_out
    assert machine.start().outcome == CommandOutcome.REJECTED


def test_end_maintenance_unlocks_but_does_not_start():
    machine = make_machine(MachineState.STOPPED)
    machine.start_maintenance()
    result = machine.end_maintenance()
    assert result.outcome == CommandOutcome.EXECUTED
    assert not machine.locked_out
    assert machine.state == MachineState.STOPPED


def test_end_maintenance_without_lockout_is_rejected():
    machine = make_machine(MachineState.STOPPED)
    result = machine.end_maintenance()
    assert result.outcome == CommandOutcome.REJECTED
    assert result.detail
