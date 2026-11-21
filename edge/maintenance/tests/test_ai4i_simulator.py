from pathlib import Path

import pytest

from maintenance.adapters.ai4i_simulator import Ai4iSimulator

CSV_HEADER = (
    "UDI,Product ID,Type,Air temperature [K],Process temperature [K],"
    "Rotational speed [rpm],Torque [Nm],Tool wear [min],Machine failure,TWF,HDF,PWF,OSF,RNF"
)
CSV_ROWS = [
    "1,M14860,M,298.1,308.6,1551,42.8,0,0,0,0,0,0,0",
    "2,L47181,L,298.2,308.7,1408,46.3,3,0,0,0,0,0,0",
    "3,L47182,L,298.3,308.8,1498,49.4,5,0,0,0,0,0,0",
]


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "ai4i.csv"
    path.write_text("\n".join([CSV_HEADER, *CSV_ROWS]), encoding="utf-8")
    return path


def test_reads_dataset_columns_into_a_reading(csv_path):
    simulator = Ai4iSimulator(csv_path, ["m1"])
    reading = simulator.read("m1")
    assert reading.air_temperature_k == 298.1
    assert reading.process_temperature_k == 308.6
    assert reading.rotational_speed_rpm == 1551
    assert reading.torque_nm == 42.8
    assert reading.tool_wear_min == 0


def test_each_read_advances_to_the_next_row(csv_path):
    simulator = Ai4iSimulator(csv_path, ["m1"])
    speeds = [simulator.read("m1").rotational_speed_rpm for _ in range(3)]
    assert speeds == [1551, 1408, 1498]


def test_wraps_around_at_the_end_of_the_dataset(csv_path):
    simulator = Ai4iSimulator(csv_path, ["m1"])
    for _ in range(3):
        simulator.read("m1")
    assert simulator.read("m1").rotational_speed_rpm == 1551


def test_machines_start_at_different_rows(csv_path):
    simulator = Ai4iSimulator(csv_path, ["m1", "m2"])
    assert simulator.read("m1") != simulator.read("m2")


def test_each_machine_keeps_its_own_cursor(csv_path):
    simulator = Ai4iSimulator(csv_path, ["m1", "m2"])
    first_m1 = simulator.read("m1")
    simulator.read("m2")
    simulator.read("m2")
    assert simulator.read("m1") != first_m1  # m1 avanzó solo con sus lecturas
