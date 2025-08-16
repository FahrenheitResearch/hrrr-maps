from .common import *
from .constants import (
    STP_CAPE_NORM, STP_LCL_REF, STP_LCL_NORM, STP_SRH_NORM, STP_SHEAR_NORM_SPC,
    STP_CAPE_MIN, STP_LCL_MAX
)

def significant_tornado_parameter_fixed_no_cin(mlcape: np.ndarray, srh_01km: np.ndarray,
                                               shear_06km: np.ndarray, lcl_height: np.ndarray) -> np.ndarray:
    """
    Compute Significant Tornado Parameter (STP) - Fixed Layer WITHOUT CIN
    
    STP_fixed_no_cin = (MLCAPE/1500) × (SRH_01km/150) × (BWD_06km/20) × ((2000-MLLCL)/1000)
    
    Status: 🟡 Modified (not SPC canonical)
    
    This is a MODIFIED variant that omits the CIN term from the SPC fixed-layer STP.
    The canonical SPC fixed-layer STP includes CIN per the 2012 update.
    
    Args:
        mlcape: Mixed Layer CAPE (J/kg)
        srh_01km: 0-1 km Storm Relative Helicity (m²/s²) - FIXED LAYER
        shear_06km: 0-6 km bulk wind difference magnitude (m/s) - FIXED LAYER
        lcl_height: Mixed Layer LCL height (m AGL)
        
    Returns:
        STP values (dimensionless, always ≥ 0)
        
    References:
        Based on Thompson et al. (2003) but without CIN term
    """
    # ========================================================================
    # MODIFIED STP TERMS (no CIN)
    # ========================================================================
    
    # 1. CAPE term: MLCAPE/1500 (configurable cap)
    cape_term = mlcape / STP_CAPE_NORM
    cape_term = np.clip(cape_term, 0.0, 1.5)  # Optional cap for extreme values
    
    # 2. LCL term: (2000-MLLCL)/1000 with proper clipping
    lcl_term = (STP_LCL_REF - lcl_height) / STP_LCL_NORM
    lcl_term = np.clip(lcl_term, 0.0, 1.0)
    
    # 3. SRH term: SRH_01km/150 (preserve positive values only)
    srh_term = np.maximum(srh_01km, 0.0) / STP_SRH_NORM
    
    # 4. Shear term: BWD_06km/20 m/s (SPC normalization)
    shear_term = shear_06km / STP_SHEAR_NORM_SPC
    shear_term = np.clip(shear_term, 0.0, 1.5)  # Optional cap for extreme shear
    
    # ========================================================================
    # FINAL STP CALCULATION - Four terms (no CIN)
    # ========================================================================
    stp = cape_term * lcl_term * srh_term * shear_term
    
    # ========================================================================
    # HARD GATES - Basic thresholds
    # ========================================================================
    stp = np.where(mlcape < STP_CAPE_MIN, 0.0, stp)        # Insufficient instability
    stp = np.where(lcl_height > STP_LCL_MAX, 0.0, stp)     # Cloud base too high
    
    # Ensure STP is never negative
    stp = np.maximum(stp, 0.0)
    
    # Mask invalid input data
    stp = np.where((mlcape < 0) | (np.isnan(mlcape)) |
                  (np.isnan(srh_01km)) | 
                  (shear_06km < 0) | (np.isnan(shear_06km)) |
                  (lcl_height < 0) | (np.isnan(lcl_height)), 
                  np.nan, stp)
    
    return stp