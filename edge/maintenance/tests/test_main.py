import pytest

from maintenance.main import parse_machine_types
from smartmine_common.config import ConfigError


def test_machine_types_are_parsed_in_order():
    assert parse_machine_types(["trituradora-01:H", "cinta-02:L"]) == {
        "trituradora-01": "H",
        "cinta-02": "L",
    }


def test_spaces_around_id_and_type_are_ignored():
    assert parse_machine_types([" molino-03 : M "]) == {"molino-03": "M"}


@pytest.mark.parametrize(
    "item",
    [
        "trituradora-01",  
        ":H",  
        "trituradora-01:X",  
        "trituradora-01:",  
    ],
)
def test_malformed_item_raises_config_error(item):
    with pytest.raises(ConfigError):
        parse_machine_types([item])


def test_repeated_machine_raises_config_error():
    with pytest.raises(ConfigError):
        parse_machine_types(["cinta-02:L", "cinta-02:H"])