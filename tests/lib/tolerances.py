"""
Test Tolerances

Defines tolerance values for state detection in simulation vs hardware.

Simulation: Tighter tolerances (direct digital access)
Hardware: Looser tolerances (ADC noise, polling latency)
"""

from .hw import HVS

# Simulation tolerance (tighter - direct digital access)
SIM_HVS_TOLERANCE = 200  # +/-200 digital units (~30mV)

# Hardware tolerance (looser - ADC noise, polling latency)
HW_HVS_TOLERANCE_V = 0.30  # +/-300mV
HW_HVS_TOLERANCE_DIGITAL = HVS.mv_to_digital(int(HW_HVS_TOLERANCE_V * 1000))
