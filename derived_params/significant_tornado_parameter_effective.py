from .common import *
from .constants import (
    STP_CAPE_NORM, STP_LCL_REF, STP_LCL_NORM, STP_SRH_NORM, STP_SHEAR_NORM_SPC,
    STP_CIN_OFFSET, STP_CIN_NORM, STP_CAPE_MIN, STP_CIN_GATE, STP_LCL_MAX,
    STP_SHEAR_MIN, STP_SHEAR_CAP, STP_SHEAR_CAP_FACTOR
)

def significant_tornado_parameter_effective(mlcape: np.ndarray, mlcin: np.ndarray,
                                          effective_srh: np.ndarray, effective_shear: np.ndarray,
                                          mllcl_height: np.ndarray) -> np.ndarray:
    """
    Compute STP (Effective Layer Version with CIN) - Current SPC Definition
    
    STP_effective = (MLCAPE/1500) × (ESRH/150) × (EBWD/20) × ((2000-MLLCL)/1000) × ((150+MLCIN)/125)
    
    This is the EFFECTIVE LAYER VERSION with CIN term as currently used by SPC.
    Uses effective-layer storm-relative helicity (ESRH) and effective bulk wind 
    difference (EBWD) instead of fixed layers for improved accuracy in varied environments.
    
    Args:
        mlcape: Mixed Layer CAPE (J/kg)
        mlcin: Mixed Layer CIN (J/kg, negative values)
        effective_srh: Effective Storm Relative Helicity (m²/s²) - ESRH
        effective_shear: Effective Bulk Wind Difference (m/s) - EBWD
        mllcl_height: Mixed Layer LCL height (m AGL)
        
    Returns:
        STP_effective values (dimensionless, always ≥ 0)
        
    Interpretation:
        STP_eff > 1: Heightened significant tornado risk
        STP_eff > 4: Extreme tornado potential
        STP_eff > 8: Historic outbreak-level environment
        
    References:
        Thompson et al. (2012): Updated STP formulation
        SPC Mesoanalysis Page: Current operational implementation
    """
    # 1. CAPE term: MLCAPE/1500 (no arbitrary cap)
    cape_term = np.maximum(mlcape / STP_CAPE_NORM, 0)
    
    # 2. LCL term: (2000-MLLCL)/1000 with proper clipping
    # MLLCL < 1000m → 1.0 (extremely favorable low cloud base)
    # MLLCL > 2000m → 0.0 (unfavorable high cloud base)
    lcl_term = np.where(mllcl_height < STP_LCL_NORM, 1.0,
                       np.where(mllcl_height > STP_LCL_REF, 0.0,
                               (STP_LCL_REF - mllcl_height) / STP_LCL_NORM))
    
    # 3. Effective SRH term: Effective_SRH/150 (preserve sign but cap negative)
    srh_term = np.maximum(effective_srh / STP_SRH_NORM, 0)
    
    # 4. Effective Shear term: EBWD/20 m/s with SPC clipping
    # < 12.5 m/s (25 kt) → 0 (insufficient shear)
    # > 30 m/s (60 kt) → cap at 1.5 (diminishing returns)
    shear_term = np.where(effective_shear < STP_SHEAR_MIN, 0,
                         np.where(effective_shear > STP_SHEAR_CAP, STP_SHEAR_CAP_FACTOR, 
                                 effective_shear / STP_SHEAR_NORM_SPC))
    
    # ========================================================================
    # MLCIN SIGN FIX - Ensure HRRR MLCIN field is negative
    # ========================================================================
    # Force MLCIN to negative values (HRRR may store as positive magnitude)
    mlcin = -np.abs(mlcin)
    
    # 5. CIN term: (150 + MLCIN)/125 - SPC standard formula  
    # Strong CIN (< -200 J/kg) → 0.0 (complete inhibition)
    # Weak CIN (> -50 J/kg) → near 1.0 (little inhibition)
    cin_term = (STP_CIN_OFFSET + mlcin) / STP_CIN_NORM
    cin_term = np.clip(cin_term, 0.0, 1.0)
    
    # Enhanced STP calculation (multiplicative)
    stp_eff = cape_term * lcl_term * srh_term * shear_term * cin_term
    
    # Hard zeros for unphysical conditions - ANY of these makes STP = 0
    stp_eff = np.where(mlcape < STP_CAPE_MIN, 0.0, stp_eff)         # Insufficient instability
    stp_eff = np.where(mlcin <= STP_CIN_GATE, 0.0, stp_eff)         # Too strong inhibition
    stp_eff = np.where(mllcl_height > STP_LCL_MAX, 0.0, stp_eff)    # Cloud base too high
    
    # Ensure STP is never negative
    stp_eff = np.maximum(stp_eff, 0.0)
    
    # Mask invalid input data
    stp_eff = np.where((mlcape < 0) | (np.isnan(mlcape)) | (np.isnan(mlcin)) |
                      (np.isnan(effective_srh)) | (np.isnan(effective_shear)) | 
                      (mllcl_height < 0) | (np.isnan(mllcl_height)), 
                      np.nan, stp_eff)
    
    return stp_eff
