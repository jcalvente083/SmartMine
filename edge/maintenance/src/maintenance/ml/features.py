import math

import numpy as np

from maintenance.domain.reading import MachineReading

# Orden de las columnas:
FEATURE_NAMES = (
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

# Calidad del producto (AI4I): 
TYPE_CODES = {"L": 0, "M": 1, "H": 2}


def type_code(product_type: str) -> int:
    """Código ordinal del tipo de producto. Lanza ValueError si el tipo no existe."""
    code = TYPE_CODES.get(product_type)
    if code is None:
        raise ValueError(
            f"Tipo de producto desconocido: {product_type!r}. Válidos: {sorted(TYPE_CODES)}"
        )
    return code


def feature_matrix(
    type_codes,
    air_temperature_k,
    process_temperature_k,
    rotational_speed_rpm,
    torque_nm,
    tool_wear_min,
) -> np.ndarray:
    temp_diff_k = process_temperature_k - air_temperature_k  
    power_w = torque_nm * rotational_speed_rpm * 2 * math.pi / 60  
    strain = tool_wear_min * torque_nm  

    return np.column_stack(
        [
            type_codes,
            air_temperature_k,
            process_temperature_k,
            rotational_speed_rpm,
            torque_nm,
            tool_wear_min,
            temp_diff_k,
            power_w,
            strain,
        ]
    )


def features_from_reading(reading: MachineReading, product_type: str) -> np.ndarray:
    return feature_matrix(
        type_codes=type_code(product_type),
        air_temperature_k=reading.air_temperature_k,
        process_temperature_k=reading.process_temperature_k,
        rotational_speed_rpm=reading.rotational_speed_rpm,
        torque_nm=reading.torque_nm,
        tool_wear_min=reading.tool_wear_min,
    )