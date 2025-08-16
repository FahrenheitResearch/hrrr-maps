from .common import *
from .constants import (
    SCP_CAPE_NORM, SCP_SRH_NORM, SCP_SHEAR_MIN, SCP_SHEAR_SPAN, SCP_SHEAR_MAX,
    CAPE_MIN_CONVECTION
)

def supercell_composite_parameter(mucape: np.ndarray, effective_srh: np.ndarray, 
                                effective_shear: np.ndarray) -> np.ndarray:
    """
    Compute Supercell Composite Parameter (SCP) - Standard SPC Definition
    
    SCP = (muCAPE / 1000) × (ESRH / 50) × shear_term
    
    This is the STANDARD SPC implementation WITHOUT CIN term.
    Uses three core ingredients for supercell assessment.
    
    Status: 🟢 SPC-Operational
    
    Ingredients:
    - muCAPE: most-unstable CAPE (J kg⁻¹)
    - ESRH: effective storm-relative helicity (m² s⁻²) 
    - EBWD: effective bulk-wind difference (m s⁻¹)
    
    Args:
        mucape: Most-Unstable CAPE (J/kg) - HRRR field MUCAPE
        effective_srh: Effective Storm Relative Helicity (m²/s²) - HRRR field ESRHL
        effective_shear: Effective Bulk Wind Difference (m/s) - derived parameter
        
    Returns:
        SCP values (dimensionless, always ≥ 0)
        
    References:
        Thompson et al. (2003): Original SCP formulation
        SPC Mesoanalysis Page: Current operational implementation
    """
    
    # ========================================================================
    # QUALITY FLAGS - Log outliers for debugging
    # ========================================================================
    extreme_cape = np.any(mucape > 6000)
    extreme_srh = np.any(effective_srh > 800)
    extreme_shear = np.any(effective_shear > 60)
    
    if extreme_cape or extreme_srh or extreme_shear:
        print(f"🔍 SCP outliers detected: muCAPE>{6000 if extreme_cape else 'OK'}, "
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
    # 4. FINAL SCP - CAPE × SRH × Shear (NO CIN term in standard SCP)
    # ========================================================================
    scp = cape_term * srh_term * shear_term
    
    # ========================================================================
    # 5. QUALITY CONTROL - Mask invalid data and set physical limits
    # ========================================================================
    # Mask invalid input data
    valid_data = (
        np.isfinite(mucape) & (mucape >= 0) &
        np.isfinite(effective_srh) &
        np.isfinite(effective_shear) & (effective_shear >= 0)
    )
    
    # Set invalid or unphysical values to 0
    scp = np.where(valid_data & np.isfinite(scp) & (scp >= 0), scp, 0.0)
    
    # Mask low-CAPE areas (insufficient instability for supercells)
    scp = np.where(mucape < CAPE_MIN_CONVECTION, 0.0, scp)  # J/kg threshold
    
    # Ensure SCP is never negative (should not happen with above logic)
    scp = np.maximum(scp, 0.0)
    
    return scp


def supercell_composite_parameter_legacy(mucape: np.ndarray, srh_03km: np.ndarray, 
                                        shear_06km: np.ndarray, mlcin: np.ndarray = None) -> np.ndarray:
    """
    Legacy SCP implementation - kept for backwards compatibility
    
    Uses 0-3km SRH instead of ESRH and ML-CIN instead of MU-CIN.
    For operational use, prefer the main supercell_composite_parameter function.
    """
    # CAPE term (only positive CAPE contributes)
    cape_term = np.maximum(mucape / 1000.0, 0)
    
    # SRH term - PRESERVE SIGN! Negative SRH = left-moving storms
    # Do NOT take absolute value or force to positive
    srh_term = srh_03km / 50.0
    
    # Shear term with SPC ops cap (stops background carpets)
    # Cap at 1.0 once shear >= 20 m/s (what SPC does in operations)  
    shear_term = np.minimum(shear_06km / 20.0, 1.0)
    
    # SCP calculation - can be positive or negative
    scp = cape_term * srh_term * shear_term
    
    # Apply CIN gate to knock out carpets (optional but recommended)
    if mlcin is not None:
        scp = scp * cin_gate(mlcin)
    
    # Mask invalid input data (but allow negative SRH)
    scp = np.where((mucape < 0) | (np.isnan(mucape)) | 
                  (np.isnan(srh_03km)) | (shear_06km < 0) | (np.isnan(shear_06km)), 
                  np.nan, scp)
    
    return scp