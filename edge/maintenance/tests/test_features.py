import math

import numpy as np
import pytest

from maintenance.domain.reading import MachineReading
from maintenance.ml.features import (
    FEATURE_NAMES,
    feature_matrix,
    features_from_reading,
    type_code,
)

READING = MachineReading(
    air_temperature_k=298.1,
    process_temperature_k=308.6,
    rotational_speed_rpm=1551.0,
    torque_nm=42.8,
    tool_wear_min=108.0,
)


def test_feature_names_have_the_agreed_order():
    assert FEATURE_NAMES == (
        "type_code",
        "air_temperature_k",
        "process_temperature_k",
        "rotational_speed_rpm",
        "torque_nm",
        "tool_wear_min",
        "temp_diff_k",
        "power_w",
        "strain",
    )


@pytest.mark.parametrize(("product_type", "expected"), [("L", 0), ("M", 1), ("H", 2)])
def test_type_code_is_ordinal(product_type, expected):
    assert type_code(product_type) == expected


def test_unknown_product_type_is_rejected():
    with pytest.raises(ValueError):
        type_code("X")


def test_features_from_reading_returns_one_row_with_every_feature():
    features = features_from_reading(READING, "M")
    assert features.shape == (1, len(FEATURE_NAMES))


def test_derived_features_follow_the_physics():
    row = dict(zip(FEATURE_NAMES, features_from_reading(READING, "M")[0]))
    assert row["type_code"] == 1
    assert row["temp_diff_k"] == pytest.approx(308.6 - 298.1)
    assert row["power_w"] == pytest.approx(42.8 * 1551.0 * 2 * math.pi / 60)
    assert row["strain"] == pytest.approx(108.0 * 42.8)


def test_single_reading_and_batch_produce_identical_features():

    readings = [
        READING,
        MachineReading(299.0, 309.5, 1380.0, 55.1, 210.0),
        MachineReading(301.2, 310.0, 2100.0, 18.3, 5.0),
    ]
    types = ["M", "L", "H"]

    one_by_one = np.vstack([features_from_reading(r, t) for r, t in zip(readings, types)])
    batch = feature_matrix(
        type_codes=np.array([type_code(t) for t in types]),
        air_temperature_k=np.array([r.air_temperature_k for r in readings]),
        process_temperature_k=np.array([r.process_temperature_k for r in readings]),
        rotational_speed_rpm=np.array([r.rotational_speed_rpm for r in readings]),
        torque_nm=np.array([r.torque_nm for r in readings]),
        tool_wear_min=np.array([r.tool_wear_min for r in readings]),
    )
    np.testing.assert_allclose(one_by_one, batch)