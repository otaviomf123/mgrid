"""
High-level API for MPAS-based grid generation.

This module provides simple, user-friendly functions that hide the
complexity of mesh generation behind an intuitive interface.

Example usage:

    from mgrid import generate_mesh, save_grid

    # Generate a uniform resolution grid
    mesh = generate_mesh(resolution=30)  # 30 km resolution

    # Generate from configuration file
    mesh = generate_mesh(config='my_config.json')

    # Save to MPAS format
    save_grid(mesh, 'my_grid.nc')
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Grid:
    """
    Container for generated grid data.

    Attributes
    ----------
    cell_width : ndarray
        2D array of cell widths in km.
    lon : ndarray
        1D array of longitudes.
    lat : ndarray
        1D array of latitudes.
    mesh_file : Path or None
        Path to generated mesh file (after generation).
    mpas_file : Path or None
        Path to MPAS NetCDF file (after conversion).
    config : dict
        Configuration used to generate the grid.
    """
    cell_width: np.ndarray = field(default_factory=lambda: np.array([]))
    lon: np.ndarray = field(default_factory=lambda: np.array([]))
    lat: np.ndarray = field(default_factory=lambda: np.array([]))
    mesh_file: Optional[Path] = None
    mpas_file: Optional[Path] = None
    config: Dict[str, Any] = field(default_factory=dict)

    @property
    def min_resolution(self) -> float:
        """Minimum cell width in km."""
        if self.cell_width.size == 0:
            return 0.0
        return float(np.min(self.cell_width))

    @property
    def max_resolution(self) -> float:
        """Maximum cell width in km."""
        if self.cell_width.size == 0:
            return 0.0
        return float(np.max(self.cell_width))

    @property
    def mean_resolution(self) -> float:
        """Mean cell width in km."""
        if self.cell_width.size == 0:
            return 0.0
        return float(np.mean(self.cell_width))

    def summary(self) -> str:
        """Return a summary string of the grid properties."""
        lines = [
            "Grid Summary",
            "=" * 40,
            f"Resolution range: {self.min_resolution:.1f} - {self.max_resolution:.1f} km",
            f"Mean resolution: {self.mean_resolution:.1f} km",
            f"Grid size: {self.lat.size} x {self.lon.size} points",
        ]

        if self.mesh_file:
            lines.append(f"Mesh file: {self.mesh_file}")
        if self.mpas_file:
            lines.append(f"MPAS file: {self.mpas_file}")

        return "\n".join(lines)


def generate_mesh(
    resolution: Optional[float] = None,
    config: Optional[Union[str, Path, Dict]] = None,
    regions: Optional[List] = None,
    background_resolution: float = 150.0,
    grid_density: float = 0.05,
    output_path: Optional[Union[str, Path]] = None,
    generate_jigsaw: bool = True,
    plot: bool = False
) -> Grid:
    """
    Generate an MPAS/MONAN mesh with automatic parameter handling.

    This is the main entry point for grid generation. It supports three
    modes of operation:

    1. Uniform resolution: Pass `resolution` parameter
    2. Configuration file: Pass `config` as file path or dict
    3. Custom regions: Pass `regions` list directly

    Parameters
    ----------
    resolution : float, optional
        For uniform grids: target resolution in km.
    config : str, Path, or dict, optional
        Configuration file path or dictionary with region definitions.
    regions : list of Region, optional
        List of Region objects for custom refinement.
    background_resolution : float, optional
        Resolution outside all regions (default: 150 km).
    grid_density : float, optional
        Grid density factor for cell width specification (default: 0.05).
    output_path : str or Path, optional
        Base path for output files. Uses 'mesh_output' if not specified.
    generate_jigsaw : bool, optional
        Whether to run JIGSAW mesh generation (default: True).
    plot : bool, optional
        Whether to generate diagnostic plots (default: False).

    Returns
    -------
    grid : Grid
        Generated grid object containing cell widths and file paths.

    Examples
    --------
    >>> # Uniform 30 km resolution
    >>> grid = generate_mesh(resolution=30)

    >>> # From configuration file
    >>> grid = generate_mesh(config='brazil_grid.json')

    >>> # Custom regions
    >>> from m_grid import CircularRegion
    >>> region = CircularRegion(
    ...     name='Amazon',
    ...     resolution=5,
    ...     transition_width=50,
    ...     center=(-3.0, -60.0),
    ...     radius=500
    ... )
    >>> grid = generate_mesh(regions=[region], background_resolution=100)
    """
    from .geometry import create_latlon_grid
    from .regions import Region, CircularRegion, PolygonRegion
    from .regions import compute_cell_width, regions_from_config, region_from_dict
    from .io import load_config, validate_config
    from .mesh import generate_spherical_mesh

    # Determine output path
    if output_path is None:
        output_path = Path('mesh_output')
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    grid = Grid()
    grid.config = {
        'background_resolution': background_resolution,
        'grid_density': grid_density
    }

    # Mode 1: Uniform resolution
    if resolution is not None:
        print(f"\nGenerating uniform resolution grid: {resolution} km")

        dlat = resolution / 1000.0
        nlat = int(180.0 / dlat) + 1
        nlon = int(360.0 / dlat) + 1

        grid.lat = np.linspace(-90.0, 90.0, nlat)
        grid.lon = np.linspace(-180.0, 180.0, nlon)
        grid.cell_width = resolution * np.ones((nlat, nlon))

        grid.config['mode'] = 'uniform'
        grid.config['resolution'] = resolution

    # Mode 2: Configuration file/dict
    elif config is not None:
        if isinstance(config, (str, Path)):
            print(f"\nLoading configuration from: {config}")
            config_dict = load_config(config)
        else:
            config_dict = config

        validate_config(config_dict)

        region_list, bg_res = regions_from_config(config_dict)

        # Override background resolution if specified in config
        if 'background_resolution' in config_dict:
            background_resolution = config_dict['background_resolution']

        if 'grid_density' in config_dict:
            grid_density = config_dict['grid_density']

        # Find finest resolution
        finest_res = min(r.resolution for r in region_list)
        dlat = finest_res * grid_density
        nlat = int(180.0 / dlat) + 1
        nlon = int(360.0 / dlat) + 1

        grid.lat = np.linspace(-90.0, 90.0, nlat)
        grid.lon = np.linspace(-180.0, 180.0, nlon)
        lons, lats = np.meshgrid(grid.lon, grid.lat)

        print(f"\nGrid size: {nlat} x {nlon} points")
        print(f"Background resolution: {background_resolution} km")

        grid.cell_width = compute_cell_width(
            lons, lats, region_list, background_resolution
        )

        grid.config['mode'] = 'multi_region'
        grid.config['regions'] = config_dict.get('regions', [])
        grid.config['background_resolution'] = background_resolution

    # Mode 3: Custom regions
    elif regions is not None:
        print(f"\nGenerating grid with {len(regions)} custom regions")

        # Find finest resolution
        finest_res = min(r.resolution for r in regions)
        dlat = finest_res * grid_density
        nlat = int(180.0 / dlat) + 1
        nlon = int(360.0 / dlat) + 1

        grid.lat = np.linspace(-90.0, 90.0, nlat)
        grid.lon = np.linspace(-180.0, 180.0, nlon)
        lons, lats = np.meshgrid(grid.lon, grid.lat)

        grid.cell_width = compute_cell_width(
            lons, lats, regions, background_resolution
        )

        grid.config['mode'] = 'custom_regions'
        grid.config['n_regions'] = len(regions)

    else:
        raise ValueError(
            "Must specify one of: resolution, config, or regions"
        )

    print(f"\nResolution range: {grid.min_resolution:.1f} - {grid.max_resolution:.1f} km")

    # Generate diagnostic plots
    if plot:
        from .plotting import plot_cell_width
        plot_file = output_path.parent / f"{output_path.name}_resolution.png"
        plot_cell_width(
            grid.cell_width, grid.lon, grid.lat,
            output_file=plot_file,
            show=True
        )

    # Run JIGSAW mesh generation
    if generate_jigsaw:
        mesh_file = generate_spherical_mesh(
            grid.cell_width,
            grid.lon,
            grid.lat,
            output_path=output_path
        )
        grid.mesh_file = mesh_file

    return grid


def generate_icosahedral(
    level: int = 4,
    output_path: Optional[Union[str, Path]] = None
) -> Grid:
    """
    Generate an icosahedral mesh.

    This creates a quasi-uniform global mesh by subdividing an icosahedron.

    Parameters
    ----------
    level : int, optional
        Refinement level (default: 4, ~120 km resolution).
        Level 2: ~500 km, Level 6: ~30 km, Level 8: ~7 km
    output_path : str or Path, optional
        Base path for output files.

    Returns
    -------
    grid : Grid
        Generated grid object.

    Examples
    --------
    >>> # Generate ~30 km icosahedral mesh
    >>> grid = generate_icosahedral(level=6)
    """
    from .mesh import generate_icosahedral_mesh
    from .geometry import icosahedral_resolution

    if output_path is None:
        output_path = Path(f'mesh_icos_level{level}')
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    resolution = icosahedral_resolution(level)
    print(f"\nGenerating icosahedral mesh")
    print(f"Level: {level}")
    print(f"Approximate resolution: {resolution:.1f} km")

    mesh_file = generate_icosahedral_mesh(output_path, level)

    grid = Grid()
    grid.mesh_file = mesh_file
    grid.config = {
        'mode': 'icosahedral',
        'level': level,
        'approximate_resolution': resolution
    }

    return grid


def save_grid(
    grid: Grid,
    output_file: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Save a generated grid to MPAS NetCDF format.

    This performs the conversion from JIGSAW mesh format to MPAS format,
    creating the Voronoi dual mesh required by MPAS-Atmosphere.

    Parameters
    ----------
    grid : Grid
        Grid object from generate_mesh() or generate_icosahedral().
    output_file : str or Path
        Output file path (should end in .nc).
    output_dir : str or Path, optional
        Directory for intermediate files.

    Returns
    -------
    mpas_file : Path
        Path to the generated MPAS grid file.

    Examples
    --------
    >>> grid = generate_mesh(resolution=30)
    >>> save_grid(grid, 'my_mpas_grid.nc')
    """
    from .io import convert_to_mpas

    if grid.mesh_file is None:
        raise ValueError(
            "Grid has no mesh file. Run generate_mesh() with "
            "generate_jigsaw=True first."
        )

    output_path = Path(output_file)
    if not output_path.suffix:
        output_path = output_path.with_suffix('.nc')

    mpas_file = convert_to_mpas(
        mesh_file=grid.mesh_file,
        output_file=output_path,
        output_dir=output_dir
    )

    grid.mpas_file = mpas_file

    return mpas_file


def quick_grid(
    resolution: float = 30.0,
    output: str = 'mpas_grid.nc'
) -> Path:
    """
    Generate and save an MPAS grid in one step.

    This is the simplest way to create an MPAS grid file.

    Parameters
    ----------
    resolution : float, optional
        Target resolution in km (default: 30 km).
    output : str, optional
        Output file path.

    Returns
    -------
    mpas_file : Path
        Path to the generated MPAS grid file.

    Examples
    --------
    >>> # Generate a 50 km resolution global grid
    >>> quick_grid(resolution=50, output='global_50km.nc')
    """
    output_path = Path(output)
    mesh_base = output_path.stem

    grid = generate_mesh(
        resolution=resolution,
        output_path=mesh_base,
        generate_jigsaw=True
    )

    return save_grid(grid, output_path)
