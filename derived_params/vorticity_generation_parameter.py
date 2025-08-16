from .common import *
from .constants import VGP_K_DEFAULT

def vorticity_generation_parameter(cape: np.ndarray, 
                                 wind_shear_01km: np.ndarray, K: float = VGP_K_DEFAULT) -> np.ndarray:
    """
    Compute Vorticity Generation Parameter (VGP) - Dimensionless Definition
    
    VGP = (BWD_0-1km × √CAPE) / K
    
    where BWD_0-1km is the bulk wind difference magnitude (m/s) and
    K is a dimensionless normalization constant (default: 40.0)
    
    VGP estimates the potential for updrafts to generate vertical vorticity
    from horizontal vorticity through tilting and stretching. Normalized to
    produce typical values of 0.3-0.5 for significant tornado environments.
    
    Args:
        cape: CAPE (J/kg) - provides updraft strength (w ∝ √CAPE)
        wind_shear_01km: 0-1km bulk wind difference magnitude (m/s)
        K: Normalization constant (dimensionless) - default 40.0
        
    Returns:
        VGP values (dimensionless)
        
    Interpretation (with K=40):
        > 0.3: Increased tornado potential
        > 0.5: Significant tornado potential
        > 0.7: High tornado potential
        
    Note:
        Thresholds are dataset-dependent and should be calibrated with local cases.
        
    References:
        Rasmussen, E.N., and D.O. Blanchard, 1998: A baseline climatology of 
            sounding-derived supercell and tornado forecast parameters. WAF, 13, 1148-1164.
        Davies-Jones, R., et al., 2001: Tornadogenesis in supercell storms. 
            Severe Convective Storms, Meteor. Monogr., 28, 167-221.
    """
    # ========================================================================
    # DIMENSIONLESS VGP CALCULATION
    # ========================================================================
    # VGP = (BWD_0-1km × √CAPE) / K
    # Use bulk wind difference directly (m/s), not divided by depth
    # K provides dimensionless normalization for operational thresholds
    vgp = (wind_shear_01km * np.sqrt(np.maximum(cape, 0))) / K
    
    # Mask invalid data
    vgp = np.where((cape < 0) | (np.isnan(cape)) | 
                  (wind_shear_01km < 0) | (np.isnan(wind_shear_01km)), 
                  np.nan, vgp)
    
    return vgp
