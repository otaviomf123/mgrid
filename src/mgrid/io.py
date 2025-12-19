"""
Input/Output module for MPAS/MONAN grid files.

This module handles reading and writing of grid files in various formats,
including JIGSAW mesh files, NetCDF, and MPAS-specific formats.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

import numpy as np


def load_config(config_file: Union[str, Path]) -> Dict[str, Any]:
    """
    Load grid configuration from a JSON file.

    Parameters
    ----------
    config_file : str or Path
        Path to the JSON configuration file.

    Returns
    -------
    config : dict
        Configuration dictionary containing:
        - 'regions': list of region definitions
        - 'background_resolution': float (optional)
        - 'grid_density': float (optional)

    Raises
    ------
    FileNotFoundError
        If configuration file does not exist.
    json.JSONDecodeError
        If file is not valid JSON.

    Examples
    --------
    >>> config = load_config('my_grid_config.json')
    >>> print(config['regions'][0]['name'])
    'MyRegion'
    """
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config


def save_config(config: Dict[str, Any], output_file: Union[str, Path]) -> Path:
    """
    Save grid configuration to a JSON file.

    Parameters
    ----------
    config : dict
        Configuration dictionary.
    output_file : str or Path
        Output file path.

    Returns
    -------
    output_path : Path
        Path to saved configuration file.
    """
    output_path = Path(output_file)

    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)

    return output_path


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate a grid configuration dictionary.

    Parameters
    ----------
    config : dict
        Configuration to validate.

    Returns
    -------
    valid : bool
        True if configuration is valid.

    Raises
    ------
    ValueError
        If configuration is invalid, with description of the issue.
    """
    if 'regions' not in config:
        raise ValueError("Configuration must contain 'regions' key")

    for idx, region in enumerate(config['regions']):
        # Check required fields
        if 'type' not in region:
            raise ValueError(
                f"Region {idx} must specify 'type' (circle or polygon)"
            )

        if 'resolution' not in region:
            raise ValueError(f"Region {idx} must specify 'resolution'")

        if 'transition_start' not in region:
            raise ValueError(f"Region {idx} must specify 'transition_start'")

        region_type = region['type'].lower()

        if region_type == 'circle':
            if 'center' not in region:
                raise ValueError(f"Circle region {idx} must specify 'center'")
            if 'radius' not in region:
                raise ValueError(f"Circle region {idx} must specify 'radius'")

            center = region['center']
            if len(center) != 2:
                raise ValueError(
                    f"Circle region {idx}: center must be [lat, lon]"
                )

            lat, lon = center
            if not (-90 <= lat <= 90):
                raise ValueError(
                    f"Circle region {idx}: latitude must be in [-90, 90]"
                )
            if not (-180 <= lon <= 180):
                raise ValueError(
                    f"Circle region {idx}: longitude must be in [-180, 180]"
                )

        elif region_type == 'polygon':
            if 'polygon' not in region:
                raise ValueError(
                    f"Polygon region {idx} must specify 'polygon' coordinates"
                )

            vertices = region['polygon']
            if len(vertices) < 3:
                raise ValueError(
                    f"Polygon region {idx} must have at least 3 vertices"
                )

            for i, vertex in enumerate(vertices):
                if len(vertex) != 2:
                    raise ValueError(
                        f"Polygon region {idx}, vertex {i}: must be [lat, lon]"
                    )

        else:
            raise ValueError(
                f"Region {idx} has invalid type: {region_type}. "
                "Must be 'circle' or 'polygon'"
            )

        # Validate resolution values
        res = region['resolution']
        trans = region['transition_start']

        if res <= 0:
            raise ValueError(
                f"Region {idx}: resolution must be positive"
            )

        if trans < res:
            raise ValueError(
                f"Region {idx}: transition_start ({trans}) must be >= "
                f"resolution ({res})"
            )

    return True


def convert_to_mpas(
    mesh_file: Union[str, Path],
    output_file: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Convert a JIGSAW mesh to MPAS format.

    This function performs the following conversions:
    1. JIGSAW mesh (.msh) -> Triangular NetCDF
    2. Triangular NetCDF -> MPAS Voronoi dual mesh

    Parameters
    ----------
    mesh_file : str or Path
        Path to JIGSAW mesh file.
    output_file : str or Path
        Path for final MPAS NetCDF file.
    output_dir : str or Path, optional
        Directory for intermediate files. Uses output file's directory if
        not specified.

    Returns
    -------
    mpas_file : Path
        Path to the generated MPAS grid file.

    Raises
    ------
    ImportError
        If mpas_tools is not installed.
    RuntimeError
        If conversion fails.

    Notes
    -----
    Requires mpas_tools package. Install with:
        conda install -c conda-forge mpas_tools
    """
    try:
        from mpas_tools.mesh.creation.jigsaw_to_netcdf import jigsaw_to_netcdf
        from mpas_tools.mesh.conversion import convert
        from mpas_tools.io import write_netcdf
        import xarray
    except ImportError as e:
        raise ImportError(
            "mpas_tools is required for MPAS conversion. "
            "Install with: conda install -c conda-forge mpas_tools"
        ) from e

    mesh_path = Path(mesh_file)
    output_path = Path(output_file)

    if output_dir is None:
        output_dir = output_path.parent
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Intermediate file paths
    base_name = output_path.stem.replace('_mpas', '')
    triangles_file = output_dir / f"{base_name}_triangles.nc"
    graph_file = output_dir / f"{base_name}_graph.info"

    print("\n" + "=" * 60)
    print("Converting to MPAS format")
    print("=" * 60)

    # Step 1: JIGSAW mesh to triangular NetCDF
    print(f"Converting JIGSAW mesh to NetCDF...")
    jigsaw_to_netcdf(
        msh_filename=str(mesh_path),
        output_name=str(triangles_file),
        on_sphere=True,
        sphere_radius=1.0
    )
    print(f"  -> {triangles_file}")

    # Step 2: Convert triangular mesh to MPAS Voronoi dual
    print(f"Converting to MPAS Voronoi dual mesh...")
    ds = xarray.open_dataset(triangles_file)
    mpas_ds = convert(
        ds,
        dir=str(output_dir),
        graphInfoFileName=str(graph_file)
    )

    # Step 3: Write final MPAS file
    print(f"Writing MPAS grid file...")
    write_netcdf(mpas_ds, str(output_path))
    print(f"  -> {output_path}")

    print("\n" + "=" * 60)
    print("Conversion completed successfully!")
    print("=" * 60 + "\n")

    return output_path


def read_mpas_grid(grid_file: Union[str, Path]) -> Dict[str, Any]:
    """
    Read basic information from an MPAS grid file.

    Parameters
    ----------
    grid_file : str or Path
        Path to MPAS NetCDF grid file.

    Returns
    -------
    info : dict
        Dictionary containing:
        - 'n_cells': number of cells
        - 'n_edges': number of edges
        - 'n_vertices': number of vertices
        - 'sphere_radius': sphere radius used
        - 'variables': list of variable names
    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError(
            "xarray is required to read MPAS files. "
            "Install with: pip install xarray"
        )

    ds = xr.open_dataset(grid_file)

    info = {
        'n_cells': ds.dims.get('nCells', 0),
        'n_edges': ds.dims.get('nEdges', 0),
        'n_vertices': ds.dims.get('nVertices', 0),
        'variables': list(ds.data_vars.keys()),
    }

    # Try to get sphere radius
    if 'sphere_radius' in ds.attrs:
        info['sphere_radius'] = ds.attrs['sphere_radius']

    ds.close()

    return info


def save_cell_width(
    cell_width: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    output_file: Union[str, Path]
) -> Path:
    """
    Save cell width array to NetCDF file.

    This is useful for inspecting or visualizing the cell width
    function before mesh generation.

    Parameters
    ----------
    cell_width : ndarray
        2D array of cell widths (nlat x nlon).
    lon : ndarray
        1D array of longitudes.
    lat : ndarray
        1D array of latitudes.
    output_file : str or Path
        Output file path.

    Returns
    -------
    output_path : Path
        Path to saved file.
    """
    try:
        import xarray as xr
    except ImportError:
        raise ImportError(
            "xarray is required to save cell width. "
            "Install with: pip install xarray"
        )

    ds = xr.Dataset(
        {
            'cell_width': (['lat', 'lon'], cell_width, {
                'units': 'km',
                'long_name': 'Target cell width'
            })
        },
        coords={
            'lon': ('lon', lon, {'units': 'degrees_east'}),
            'lat': ('lat', lat, {'units': 'degrees_north'})
        },
        attrs={
            'title': 'MPAS/MONAN mesh cell width function',
            'created_by': 'm-grid'
        }
    )

    output_path = Path(output_file)
    ds.to_netcdf(output_path)

    return output_path
