"""Interactive map generator for weather data visualization.

Creates Plotly-based interactive maps where users can hover
to see data values at any point - similar to PivotalWeather.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Tuple


def _regrid_curvilinear_to_regular(
    values2d: np.ndarray,
    lats2d: np.ndarray,
    lons2d: np.ndarray,
    dlat: float = 0.03,
    dlon: float = 0.03,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[float, float, float, float]]:
    """Regrid curvilinear data to regular lat/lon grid using nearest-neighbor.

    Returns:
        (values_regular, lats_1d, lons_1d, (lat_min, lat_max, lon_min, lon_max))
    """
    from scipy.spatial import cKDTree

    # Get bounds from corners
    corners_lat = np.array([lats2d[0, 0], lats2d[0, -1], lats2d[-1, 0], lats2d[-1, -1]])
    corners_lon = np.array([lons2d[0, 0], lons2d[0, -1], lons2d[-1, 0], lons2d[-1, -1]])

    lat_min, lat_max = float(np.nanmin(corners_lat)), float(np.nanmax(corners_lat))
    lon_min, lon_max = float(np.nanmin(corners_lon)), float(np.nanmax(corners_lon))

    # Create regular target grid (north to south for proper orientation)
    lat_t = np.arange(lat_max, lat_min - dlat, -dlat)
    lon_t = np.arange(lon_min, lon_max + dlon, dlon)
    lon_grid, lat_grid = np.meshgrid(lon_t, lat_t)

    # Build KDTree over source points
    src_pts = np.column_stack([lats2d.ravel(), lons2d.ravel()])
    tree = cKDTree(src_pts)

    # Query nearest neighbors
    tgt_pts = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
    distances, idx = tree.query(tgt_pts, k=1)

    # Map values
    vals_src = values2d.ravel()
    vals_reg = vals_src[idx].reshape(lat_grid.shape)

    # Mask points too far from source
    max_dist = np.sqrt(dlat**2 + dlon**2) * 2
    vals_reg[distances.reshape(lat_grid.shape) > max_dist] = np.nan

    return vals_reg, lat_t, lon_t, (lat_min, lat_max, lon_min, lon_max)


def create_interactive_map(
    data,  # xarray.DataArray
    field_name: str,
    field_config: Dict[str, Any],
    cycle: str,
    forecast_hour: int,
    output_dir: Path,
    colormap: str = "viridis",
) -> Optional[Path]:
    """Create an interactive HTML map with hover values using Plotly.

    Args:
        data: xarray DataArray with lat/lon coordinates
        field_name: Name of the field
        field_config: Field configuration dict
        cycle: Model cycle string
        forecast_hour: Forecast hour
        output_dir: Output directory
        colormap: Colormap name (Plotly compatible)

    Returns:
        Path to generated HTML file, or None on failure
    """
    try:
        import plotly.graph_objects as go

        # Get data and coordinates
        values = data.values
        lats = data.latitude.values if 'latitude' in data.coords else data.lat.values
        lons = data.longitude.values if 'longitude' in data.coords else data.lon.values

        # Convert longitudes to -180 to 180
        if lons.max() > 180:
            lons = np.where(lons > 180, lons - 360, lons)

        # Get value range
        levels = field_config.get('levels')
        if levels and len(levels) >= 2:
            vmin = float(min(levels))
            vmax = float(max(levels))
        else:
            vmin = field_config.get('vmin', float(np.nanmin(values)))
            vmax = field_config.get('vmax', float(np.nanmax(values)))

        # Get units and title
        units = field_config.get('units', '')
        title = field_config.get('title', field_name)

        # Handle curvilinear grids
        is_curvilinear = lats.ndim == 2

        if is_curvilinear:
            # Regrid to regular lat/lon (use 0.05° for reasonable file size)
            values_reg, lats_1d, lons_1d, bounds = _regrid_curvilinear_to_regular(
                values, lats, lons, dlat=0.05, dlon=0.05
            )
        else:
            # Already regular grid
            values_reg = values
            lats_1d = lats
            lons_1d = lons

        # Map colormap names to Plotly equivalents
        plotly_colormap = _get_plotly_colormap(colormap, field_name)

        # Mask values below vmin for fields like reflectivity
        if 'reflectivity' in field_name.lower() or 'refl' in field_name.lower():
            values_plot = np.where(values_reg < vmin, np.nan, values_reg)
        else:
            values_plot = values_reg

        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=values_plot,
            x=lons_1d,
            y=lats_1d,
            colorscale=plotly_colormap,
            zmin=vmin,
            zmax=vmax,
            hoverongaps=False,
            hovertemplate=f'Lat: %{{y:.2f}}°<br>Lon: %{{x:.2f}}°<br>{title}: %{{z:.1f}} {units}<extra></extra>',
            colorbar=dict(title=units if units else title),
        ))

        fig.update_layout(
            title=f'{title} - {cycle} F{forecast_hour:02d}',
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            yaxis=dict(scaleanchor='x', scaleratio=1),
            width=1400,
            height=900,
        )

        # Save
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{field_name}_f{forecast_hour:02d}_interactive.html"
        fig.write_html(str(output_path))

        return output_path

    except Exception as e:
        print(f"Error creating interactive map: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_interactive_map_geo(
    data,  # xarray.DataArray
    field_name: str,
    field_config: Dict[str, Any],
    cycle: str,
    forecast_hour: int,
    output_dir: Path,
    colormap: str = "viridis",
) -> Optional[Path]:
    """Create an interactive map with US geography background using Plotly.

    This version shows data as scatter points on a map - better for sparse
    data like reflectivity where most values are masked.
    """
    try:
        import plotly.graph_objects as go

        # Get data and coordinates
        values = data.values
        lats = data.latitude.values if 'latitude' in data.coords else data.lat.values
        lons = data.longitude.values if 'longitude' in data.coords else data.lon.values

        # Convert longitudes
        if lons.max() > 180:
            lons = np.where(lons > 180, lons - 360, lons)

        # Get value range
        levels = field_config.get('levels')
        if levels and len(levels) >= 2:
            vmin = float(min(levels))
            vmax = float(max(levels))
        else:
            vmin = field_config.get('vmin', float(np.nanmin(values)))
            vmax = field_config.get('vmax', float(np.nanmax(values)))

        units = field_config.get('units', '')
        title = field_config.get('title', field_name)

        # Handle curvilinear grids - use coarser resolution for scatter
        is_curvilinear = lats.ndim == 2

        if is_curvilinear:
            values_reg, lats_1d, lons_1d, bounds = _regrid_curvilinear_to_regular(
                values, lats, lons, dlat=0.1, dlon=0.1
            )
        else:
            values_reg = values
            lats_1d = lats
            lons_1d = lons

        # Create coordinate mesh
        lon_mesh, lat_mesh = np.meshgrid(lons_1d, lats_1d)

        # Filter to values above threshold
        mask = values_reg >= vmin
        lats_flat = lat_mesh[mask]
        lons_flat = lon_mesh[mask]
        vals_flat = values_reg[mask]

        plotly_colormap = _get_plotly_colormap(colormap, field_name)

        # Create scatter geo
        fig = go.Figure(data=go.Scattergeo(
            lon=lons_flat,
            lat=lats_flat,
            mode='markers',
            marker=dict(
                size=5,
                color=vals_flat,
                colorscale=plotly_colormap,
                cmin=vmin,
                cmax=vmax,
                colorbar=dict(title=units if units else title),
            ),
            hovertemplate=f'Lat: %{{lat:.2f}}°<br>Lon: %{{lon:.2f}}°<br>{title}: %{{marker.color:.1f}} {units}<extra></extra>',
        ))

        fig.update_layout(
            title=f'{title} - {cycle} F{forecast_hour:02d}',
            geo=dict(
                scope='usa',
                projection_type='albers usa',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                countrycolor='rgb(204, 204, 204)',
                showlakes=True,
                lakecolor='rgb(255, 255, 255)',
                subunitcolor='rgb(180, 180, 180)',
                showsubunits=True,
            ),
            width=1400,
            height=900,
        )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{field_name}_f{forecast_hour:02d}_interactive_geo.html"
        fig.write_html(str(output_path))

        return output_path

    except Exception as e:
        print(f"Error creating interactive geo map: {e}")
        import traceback
        traceback.print_exc()
        return None


def _get_plotly_colormap(colormap: str, field_name: str) -> str:
    """Convert matplotlib colormap names to Plotly equivalents."""
    # Direct mappings
    mappings = {
        'viridis': 'Viridis',
        'plasma': 'Plasma',
        'inferno': 'Inferno',
        'magma': 'Magma',
        'turbo': 'Turbo',
        'jet': 'Jet',
        'hot': 'Hot',
        'cool': 'ice',
        'coolwarm': 'RdBu',
        'RdBu_r': 'RdBu_r',
        'RdBu': 'RdBu',
        'BrBG': 'BrBG',
        'RdYlGn': 'RdYlGn',
        'Spectral': 'Spectral',
        'Blues': 'Blues',
        'Greens': 'Greens',
        'Reds': 'Reds',
        'YlOrRd': 'YlOrRd',
        'YlGnBu': 'YlGnBu',
    }

    if colormap in mappings:
        return mappings[colormap]

    # Field-specific defaults
    if 'reflectivity' in field_name.lower() or 'refl' in colormap.lower():
        return 'Turbo'
    if 'cape' in field_name.lower():
        return 'YlOrRd'
    if 'temp' in field_name.lower() or 't2m' in field_name.lower():
        return 'RdBu_r'

    return 'Viridis'


def batch_create_interactive_maps(
    data_dict: Dict[str, Any],  # field_name -> (data, field_config)
    cycle: str,
    forecast_hour: int,
    output_dir: Path,
) -> Dict[str, Path]:
    """Create interactive maps for multiple fields.

    Returns dict mapping field_name -> output_path
    """
    results = {}
    for field_name, (data, field_config) in data_dict.items():
        colormap = field_config.get('colormap', 'viridis')
        path = create_interactive_map(
            data, field_name, field_config,
            cycle, forecast_hour, output_dir, colormap
        )
        if path:
            results[field_name] = path
    return results
