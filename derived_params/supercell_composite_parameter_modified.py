from .common import *
from .constants import (
    SCP_CAPE_NORM, SCP_SRH_NORM, SCP_SHEAR_MIN, SCP_SHEAR_SPAN,
    SCP_CIN_WEAK_GATE, CAPE_MIN_CONVECTION
)

def supercell_composite_parameter_modified(mucape: np.ndarray, effective_srh: np.ndarray, 
                                         effective_shear: np.ndarray, mucin: np.ndarray) -> np.ndarray:
    """
    Compute Supercell Composite Parameter (SCP) - Modified with CIN
    
    SCP_modified = (muCAPE / 1000) × (ESRH / 50) × shear_term × CIN_weight
    
    Status: 🟡 Modified (not SPC canonical)
    
    This is a PROJECT-SPECIFIC VARIANT that adds CIN weighting to standard SCP.
    The standard SCP does not include CIN - this variant may be useful for
    operational applications but is not the canonical SPC definition.
    
    Args:
        mucape: Most-Unstable CAPE (J/kg) - HRRR field MUCAPE
        effective_srh: Effective Storm Relative Helicity (m²/s²) - HRRR field ESRHL
        effective_shear: Effective Bulk Wind Difference (m/s) - derived parameter
        mucin: Most-Unstable CIN (J/kg, negative values) - HRRR field MUCIN
        
    Returns:
        SCP modified values (dimensionless, always ≥ 0)
        
    CIN Weight Formula:
        - muCIN > -40 J/kg: CIN_weight = 1.0 (no penalty)
        - muCIN ≤ -40 J/kg: CIN_weight = -40/muCIN (proportional penalty)
        
    References:
        Based on Thompson et al. (2003) SCP + project-specific CIN enhancement
    """
    
    # ========================================================================
    # MUCIN SIGN FIX - Ensure HRRR MUCIN field is negative
    # ========================================================================
    # Force MUCIN to negative values (HRRR may store as positive magnitude)
    mucin = -np.abs(mucin)
    
    # ========================================================================
    # QUALITY FLAGS - Log outliers for debugging
    # ========================================================================
    extreme_cape = np.any(mucape > 6000)
    extreme_srh = np.any(effective_srh > 800)
    extreme_shear = np.any(effective_shear > 60)
    
    if extreme_cape or extreme_srh or extreme_shear:
        print(f"🔍 SCP Modified outliers detected: muCAPE>{6000 if extreme_cape else 'OK'}, "
              f"SRH>{800 if extreme_srh else 'OK'}, Shear>{60 if extreme_shear else 'OK'}")
    
    # ========================================================================
    # 1. CAPE TERM - muCAPE ÷ 1000
    # ========================================================================
    cape_term = mucape / SCP_CAPE_NORM
    
    # ========================================================================
    # 2. SRH TERM - ESRH ÷ 50 (force negative values to 0)
    # ========================================================================
    srh_positive = np.maximum(effective_srh, 0.0)  # Force negatives to 0 first
    srh_term = srh_positive / SCP_SRH_NORM
    
    # ========================================================================
    # 3. SHEAR TERM - SPC-compliant piecewise EBWD scaling
    # ========================================================================
    # 0 when EBWD < 10 m/s
    # linear from 0→1 between 10–20 m/s: (EBWD-10)/10
    # 1 once EBWD ≥ 20 m/s
    shear_term = np.clip((effective_shear - SCP_SHEAR_MIN) / SCP_SHEAR_SPAN, 0.0, 1.0)
    
    # ========================================================================
    # 4. CIN WEIGHT - Project-specific enhancement
    # ========================================================================
    # If inhibition is weak (muCIN > -40 J/kg), no penalty (weight = 1.0)
    # Otherwise, proportional penalty: -40 / muCIN
    cin_weight = np.where(
        mucin > SCP_CIN_WEAK_GATE,     # Weak inhibition
        1.0,                           # No penalty
        SCP_CIN_WEAK_GATE / mucin      # Proportional penalty
    )
    # Ensure valid range (should be 0.0 to 1.0 naturally)
    cin_weight = np.clip(cin_weight, 0.0, 1.0)
    
    # ========================================================================
    # 5. FINAL SCP - CAPE × SRH × Shear × CIN_weight
    # ========================================================================
    scp = cape_term * srh_term * shear_term * cin_weight
    
    # ========================================================================
    # 6. QUALITY CONTROL - Mask invalid data and set physical limits
    # ========================================================================
    # Mask invalid input data
    valid_data = (
        np.isfinite(mucape) & (mucape >= 0) &
        np.isfinite(effective_srh) &
        np.isfinite(effective_shear) & (effective_shear >= 0) &
        np.isfinite(mucin)
    )
    
    # Set invalid or unphysical values to 0
    scp = np.where(valid_data & np.isfinite(scp) & (scp >= 0), scp, 0.0)
    
    # Mask low-CAPE areas (insufficient instability for supercells)
    scp = np.where(mucape < CAPE_MIN_CONVECTION, 0.0, scp)  # J/kg threshold
    
    # Ensure SCP is never negative (should not happen with above logic)
    scp = np.maximum(scp, 0.0)
    
    return scp