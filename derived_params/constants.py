#!/usr/bin/env python3
"""
Centralized Constants for Derived Parameters

This module contains all normalization constants and thresholds used throughout
the derived parameter calculations to ensure consistency and prevent drift.

Status: 🟢 Centralized (v2.2)
"""

# =============================================================================
# STP (SIGNIFICANT TORNADO PARAMETER) CONSTANTS
# =============================================================================

# STP Normalization Constants
STP_CAPE_NORM = 1500.0          # J/kg - CAPE normalization
STP_SRH_NORM = 150.0            # m²/s² - SRH normalization  
STP_SHEAR_NORM_SPC = 20.0       # m/s - SPC standard EBWD normalization
STP_SHEAR_NORM_LEGACY = 12.0    # m/s - Legacy BWD normalization
STP_LCL_REF = 2000.0            # m AGL - LCL reference height
STP_LCL_NORM = 1000.0           # m - LCL normalization factor

# STP CIN Constants
STP_CIN_OFFSET = 150.0          # J/kg - CIN offset (SPC standard)
STP_CIN_NORM = 125.0            # J/kg - CIN normalization (SPC standard)
STP_CIN_OFFSET_LEGACY = 200.0   # J/kg - Legacy CIN offset
STP_CIN_NORM_LEGACY = 150.0     # J/kg - Legacy CIN normalization

# STP Thresholds and Limits
STP_CAPE_MIN = 100.0            # J/kg - Minimum CAPE for convection
STP_CIN_GATE = -200.0           # J/kg - Strong CIN gate threshold
STP_LCL_MAX = 2000.0            # m AGL - Maximum useful LCL height
STP_SHEAR_MIN = 12.5            # m/s - Minimum useful shear
STP_SHEAR_CAP = 30.0            # m/s - Shear cap for extreme values
STP_SHEAR_CAP_FACTOR = 1.5      # Dimensionless - Cap factor for extreme shear

# =============================================================================
# EHI (ENERGY-HELICITY INDEX) CONSTANTS  
# =============================================================================

# EHI Normalization Constants
EHI_CAPE_NORM_SPC = 1000.0      # J/kg - SPC canonical CAPE normalization
EHI_SRH_NORM_SPC = 100.0        # m²/s² - SPC canonical SRH normalization
EHI_NORM_SPC = 100000.0         # Combined: CAPE_NORM × SRH_NORM

EHI_NORM_DISPLAY = 160000.0     # Display-scaled normalization (modified)
EHI_NORM_LEGACY = 80000.0       # Legacy normalization (deprecated)

# EHI Display Damping Constants
EHI_DAMPING_THRESHOLD = 5.0     # Threshold for anti-saturation damping

# =============================================================================
# SCP (SUPERCELL COMPOSITE PARAMETER) CONSTANTS
# =============================================================================

# SCP Normalization Constants  
SCP_CAPE_NORM = 1000.0          # J/kg - muCAPE normalization
SCP_SRH_NORM = 50.0             # m²/s² - ESRH normalization
SCP_SHEAR_MIN = 10.0            # m/s - Minimum shear for linear scaling
SCP_SHEAR_SPAN = 10.0           # m/s - Linear scaling span (10-20 m/s)
SCP_SHEAR_MAX = 20.0            # m/s - Shear for maximum scaling

# SCP CIN Constants (for modified variants)
SCP_CIN_WEAK_GATE = -40.0       # J/kg - Weak CIN threshold (no penalty)

# =============================================================================
# SHIP (SIGNIFICANT HAIL PARAMETER) CONSTANTS
# =============================================================================

# SHIP v1.1 Normalization Constants
SHIP_CAPE_NORM = 1500.0         # J/kg - muCAPE normalization
SHIP_MR_NORM = 13.6             # g/kg - Mixing ratio normalization
SHIP_LAPSE_NORM = 7.0           # °C/km - Lapse rate normalization  
SHIP_SHEAR_NORM = 20.0          # m/s - Wind shear normalization

# SHIP Temperature Constants
SHIP_TEMP_REF = -20.0           # °C - Reference temperature
SHIP_TEMP_NORM = 5.0            # °C - Temperature normalization

# SHIP Quality Control Thresholds
SHIP_CAPE_MIN = 100.0           # J/kg - Minimum CAPE threshold

# =============================================================================
# VGP (VORTICITY GENERATION PARAMETER) CONSTANTS
# =============================================================================

# VGP Normalization Constants
VGP_K_DEFAULT = 40.0            # Dimensionless normalization constant
VGP_K_UNITS = "m s⁻¹ × J^0.5 kg^⁻⁰·⁵"  # Physical units of K constant

# =============================================================================
# GENERAL METEOROLOGICAL CONSTANTS
# =============================================================================

# Common Thresholds
CAPE_MIN_CONVECTION = 100.0     # J/kg - Minimum CAPE for convection
CIN_STRONG_GATE = -200.0        # J/kg - Strong inhibition threshold
CIN_WEAK_GATE = -50.0           # J/kg - Weak inhibition threshold

# Wind Speed Thresholds  
WIND_SPEED_MIN_SWEAT = 7.5      # m/s - Minimum wind speed for SWEAT terms
WIND_SPEED_MIN_KTS = 15.0       # kt - Minimum wind speed in knots (7.5 m/s)

# Common Scaling Factors
SHEAR_CAP_FACTOR = 1.5          # Dimensionless - Standard shear cap factor
TERM_CAP_MAX = 1.0              # Dimensionless - Standard term cap

# =============================================================================
# UNIT CONVERSION CONSTANTS
# =============================================================================

# Common Conversions
M_TO_KM = 0.001                 # Convert meters to kilometers
KM_TO_M = 1000.0                # Convert kilometers to meters
MS_TO_KT = 1.94384              # Convert m/s to knots
KT_TO_MS = 0.514444             # Convert knots to m/s

# =============================================================================
# VALIDATION RANGES
# =============================================================================

# Expected Value Ranges for Quality Control
CAPE_MAX_REALISTIC = 6000.0     # J/kg - Extreme but realistic CAPE
SRH_MAX_REALISTIC = 800.0       # m²/s² - Extreme but realistic SRH  
SHEAR_MAX_REALISTIC = 60.0      # m/s - Extreme but realistic shear
LAPSE_MAX_REALISTIC = 12.0      # °C/km - Extreme but realistic lapse rate

# =============================================================================
# STATUS REFERENCE
# =============================================================================

# Status Badge Meanings:
# 🟢 SPC-Operational: Storm Prediction Center canonical implementation
# 🟡 Modified: Project-specific enhancement or modification  
# 🟠 Approximation: Heuristic approximation with known limitations
# 🔵 Research: Experimental or research-oriented parameter
# 🔴 Deprecated: No longer recommended for operational use