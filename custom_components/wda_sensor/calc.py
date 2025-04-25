from .const import DEFAULT_EXP_MAX, DEFAULT_EXP_MIN

def calc_target(
        outside_temp: float,
        heating_curve: int,
        exp_min: float = DEFAULT_EXP_MIN,
        exp_max: float = DEFAULT_EXP_MAX) -> float:
    """
    Calculation of the target temperature of the coolant based on the outside
    temperature and the heating curve number
    """

    # Curve normolization from 1 to 200
    # We bring it into the range from 0 to 1
    normalized_hc = (heating_curve - 1) / 199

    # The degree of the exponent depends on the curve number.
    # Range from exp_min to exp_max
    exponent = exp_min + normalized_hc * (exp_max - exp_min)

    # The maximum temperature of the coolant — from 20 to 150°C
    A = 20 + (150 - 20) * normalized_hc

    # Temperature factor
    temp_factor = (20 - outside_temp) / 45

    # Target temperature of the coolant
    target = A * (1 - (1 - temp_factor) ** exponent)
    return target
