from .common import *
from .constants import (
    STP_CAPE_NORM, STP_LCL_REF, STP_LCL_NORM, STP_SRH_NORM, STP_SHEAR_NORM_SPC,
    STP_CIN_OFFSET, STP_CIN_NORM, STP_CAPE_MIN, STP_CIN_GATE, STP_LCL_MAX
)

def significant_tornado_parameter_fixed(mlcape: np.ndarray, mlcin: np.ndarray, 
                                       srh_01km: np.ndarray, shear_06km: np.ndarray, 
                                       lcl_height: np.ndarray) -> np.ndarray:
    """
    Compute Significant Tornado Parameter (STP) - Fixed Layer SPC Definition
    
    STP_fixed = (MLCAPE/1500) × (SRH_01km/150) × (BWD_06km/20) × ((2000-MLLCL)/1000) × ((150+MLCIN)/125)
    
    This is the CANONICAL SPC fixed-layer implementation WITH CIN term per 2012 update.
    Uses fixed 0-1km SRH and 0-6km bulk wind difference as defined in literature.
    
    Status: 🟢 SPC-Operational
    
    Args:
        mlcape: Mixed Layer CAPE (J/kg)
        mlcin: Mixed Layer CIN (J/kg, negative values)
        srh_01km: 0-1 km Storm Relative Helicity (m²/s²) - FIXED LAYER
        shear_06km: 0-6 km bulk wind difference magnitude (m/s) - FIXED LAYER
        lcl_height: Mixed Layer LCL height (m AGL)
        
    Returns:
        STP values (dimensionless, always ≥ 0)
        
    Interpretation:
        STP > 1: Significant tornado potential
        STP > 4: Extreme tornado potential
        STP > 8: Historic outbreak-level environment
        
    References:
        Thompson et al. (2003): Original fixed-layer formulation
        SPC Mesoanalysis Page: Canonical implementation
    """
    # ========================================================================
    # MLCIN SIGN FIX - Ensure HRRR MLCIN field is negative
    # ========================================================================
    # Force MLCIN to negative values (HRRR may store as positive magnitude)
    mlcin = -np.abs(mlcin)
    
    # ========================================================================
    # SPC FIXED-LAYER STP TERMS (2012 update with CIN)
    # ========================================================================
    
    # 1. CAPE term: MLCAPE/1500 (configurable cap)
    cape_term = mlcape / STP_CAPE_NORM
    cape_term = np.clip(cape_term, 0.0, 1.5)  # Optional cap for extreme values
    
    # 2. LCL term: (2000-MLLCL)/1000 with proper clipping
    # LCL < 1000m → 1.0 (extremely favorable)
    # LCL > 2000m → 0.0 (unfavorable, high cloud base)
    lcl_term = (STP_LCL_REF - lcl_height) / STP_LCL_NORM
    lcl_term = np.clip(lcl_term, 0.0, 1.0)
    
    # 3. SRH term: SRH_01km/150 (preserve positive values only)
    srh_term = np.maximum(srh_01km, 0.0) / STP_SRH_NORM
    
    # 4. Shear term: BWD_06km/20 m/s (SPC normalization)
    shear_term = shear_06km / STP_SHEAR_NORM_SPC
    shear_term = np.clip(shear_term, 0.0, 1.5)  # Optional cap for extreme shear
    
    # 5. CIN term: (150+MLCIN)/125 with proper clipping [SPC 2012 update]
    # Strong CIN (< -200 J/kg) → 0.0 (complete inhibition)
    # Weak CIN (> -50 J/kg) → near 1.0 (little inhibition)
    cin_term = (STP_CIN_OFFSET + mlcin) / STP_CIN_NORM
    cin_term = np.clip(cin_term, 0.0, 1.0)
    
    # ========================================================================
    # FINAL STP CALCULATION - All five terms multiplied
    # ========================================================================
    stp = cape_term * lcl_term * srh_term * shear_term * cin_term
    
    # ========================================================================
    # HARD GATES - SPC standard thresholds
    # ========================================================================
    stp = np.where(mlcape < STP_CAPE_MIN, 0.0, stp)        # Insufficient instability
    stp = np.where(mlcin <= STP_CIN_GATE, 0.0, stp)        # Excessive inhibition
    stp = np.where(lcl_height > STP_LCL_MAX, 0.0, stp)     # Cloud base too high
    
    # Ensure STP is never negative
    stp = np.maximum(stp, 0.0)
    
    # Mask invalid input data
    stp = np.where((mlcape < 0) | (np.isnan(mlcape)) |
                  (np.isnan(mlcin)) |
                  (np.isnan(srh_01km)) | 
                  (shear_06km < 0) | (np.isnan(shear_06km)) |
                  (lcl_height < 0) | (np.isnan(lcl_height)), 
                  np.nan, stp)
    
    return stp