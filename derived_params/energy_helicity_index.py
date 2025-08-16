from .common import *
from .constants import EHI_NORM_SPC

def energy_helicity_index(cape: np.ndarray, srh_03km: np.ndarray) -> np.ndarray:
    """
    Compute Energy-Helicity Index (EHI) - SPC Canonical Definition
    
    EHI_spc = (CAPE/1000) × (SRH/100) = (CAPE × SRH) / 100,000
    
    This is the CANONICAL SPC implementation per Davies (1993).
    For display-scaled version, use energy_helicity_index_display().
    
    Status: 🟢 SPC-Operational
    
    Args:
        cape: CAPE (J/kg) - surface-based or mixed-layer
        srh_03km: 0-3 km Storm Relative Helicity (m²/s²) - preserves sign
        
    Returns:
        EHI values (dimensionless, can be positive or negative)
        
    Interpretation:
        EHI > 1: Notable for supercells
        EHI > 2: Significant tornado potential  
        EHI > 4: Extreme tornado potential
        Positive EHI: Cyclonic (right-moving) supercell potential
        Negative EHI: Anticyclonic (left-moving) supercell potential
        
    References:
        Davies, J.M., 1993: Small tornadic supercells in the central plains.
        SPC Mesoanalysis Page: https://www.spc.noaa.gov/exper/mesoanalysis/help/
    """
    # ========================================================================
    # SPC CANONICAL EHI CALCULATION
    # ========================================================================
    # Standard EHI calculation per Davies (1993) and SPC: (CAPE/1000) × (SRH/100)
    ehi = (cape * srh_03km) / EHI_NORM_SPC
    
    # Mask invalid input data (but preserve negative SRH sign)
    ehi = np.where((cape < 0) | (np.isnan(cape)) | (np.isnan(srh_03km)), 
                  np.nan, ehi)
    
    return ehi
