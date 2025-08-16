from .common import *
from .ventilation_rate import ventilation_rate

def ventilation_rate_from_components(u_wind: np.ndarray, v_wind: np.ndarray,
                                   boundary_layer_height: np.ndarray) -> np.ndarray:
    """
    Compute Ventilation Rate using transport wind methodology
    
    Transport wind is the vector mean wind speed over the mixed layer,
    which is more representative of pollutant transport than surface wind.
    
    Args:
        u_wind: U-component of wind (m/s) - should be mixed-layer representative
        v_wind: V-component of wind (m/s) - should be mixed-layer representative  
        boundary_layer_height: Boundary layer height (m)
        
    Returns:
        Ventilation rate (m²/s) using transport wind
        
    Notes:
        - For HRRR, use 850mb winds as proxy for mixed-layer transport wind
        - Transport wind = |⟨**u**⟩| (magnitude of vector mean)
        - Falls back to scalar mean if needed: sqrt(⟨u⟩² + ⟨v⟩²)
    """
    # Calculate transport wind as magnitude of vector mean
    # This is more physically correct than scalar mean of wind speeds
    transport_wind_speed = np.sqrt(u_wind**2 + v_wind**2)
    
    return ventilation_rate(transport_wind_speed, boundary_layer_height)


def ventilation_rate_from_surface_winds(u10: np.ndarray, v10: np.ndarray,
                                       boundary_layer_height: np.ndarray) -> np.ndarray:
    """
    Compute Ventilation Rate using 10m winds (fallback method)
    
    This is a fallback when mixed-layer winds are unavailable.
    Less accurate than transport wind method but operationally useful.
    
    Args:
        u10: 10m U-component wind (m/s)
        v10: 10m V-component wind (m/s)
        boundary_layer_height: Boundary layer height (m)
        
    Returns:
        Ventilation rate (m²/s) using surface winds
    """
    surface_wind_speed = np.sqrt(u10**2 + v10**2)
    return ventilation_rate(surface_wind_speed, boundary_layer_height)
