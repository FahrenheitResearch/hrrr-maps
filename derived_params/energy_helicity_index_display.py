from .common import *
from .constants import EHI_NORM_DISPLAY, EHI_DAMPING_THRESHOLD

def energy_helicity_index_display(cape: np.ndarray, srh_03km: np.ndarray) -> np.ndarray:
    """
    Compute Energy-Helicity Index (EHI) - Display-Scaled Version
    
    EHI_display = (CAPE × SRH) / 160,000
    
    Status: 🟡 Modified (display-scaled for visualization)
    
    This is a DISPLAY-SCALED variant that provides damped values to prevent
    oversaturation in extreme environments. For SPC-canonical values, use
    energy_helicity_index().
    
    Args:
        cape: CAPE (J/kg) - surface-based or mixed-layer
        srh_03km: 0-3 km Storm Relative Helicity (m²/s²) - preserves sign
        
    Returns:
        EHI display values (dimensionless, can be positive or negative)
        
    Interpretation (adjusted for display scaling):
        EHI_display > 0.6: Notable for supercells
        EHI_display > 1.25: Significant tornado potential  
        EHI_display > 2.5: Extreme tornado potential
        
    References:
        Based on Davies (1993) with display scaling modifications
    """
    # ========================================================================
    # DISPLAY-SCALED EHI CALCULATION
    # ========================================================================
    # Display-scaled calculation: /160,000 instead of canonical /100,000
    ehi_raw = (cape * srh_03km) / EHI_NORM_DISPLAY
    
    # Apply damping factor to prevent extreme oversaturation
    # Damping kicks in when |EHI| > 5, scales down exponentially for extreme values
    ehi_abs = np.abs(ehi_raw)
    damping_threshold = EHI_DAMPING_THRESHOLD
    
    # Exponential damping: factor = threshold + log(ehi_abs/threshold) for values > threshold
    # This compresses extreme values while preserving moderate ones
    damping_factor = np.where(
        ehi_abs > damping_threshold,
        damping_threshold + np.log(ehi_abs / damping_threshold),
        ehi_abs
    )
    
    # Preserve sign and apply damping
    ehi = np.sign(ehi_raw) * damping_factor
    
    # Quality control - log extreme raw values for monitoring
    extreme_ehi = np.any(np.abs(ehi_raw) > 15)
    if extreme_ehi:
        print(f"🔍 EHI anti-saturation: Raw peaks {np.nanmax(np.abs(ehi_raw)):.1f}, "
              f"damped to {np.nanmax(np.abs(ehi)):.1f}")
    
    # Mask invalid input data (but preserve negative SRH sign)
    ehi = np.where((cape < 0) | (np.isnan(cape)) | (np.isnan(srh_03km)), 
                  np.nan, ehi)
    
    return ehi