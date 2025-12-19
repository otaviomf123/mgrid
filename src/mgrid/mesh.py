"""
Mesh generation module for MPAS/MONAN grids.

This module provides the core functionality for generating spherical meshes
using JIGSAW, including uniform resolution, icosahedral, and variable-density
Voronoi meshes.
"""

import subprocess
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Union
from dataclasses import dataclass, field

from .geometry import EARTH_RADIUS_M, EARTH_RADIUS_KM, create_latlon_grid


@dataclass
class MeshConfig:
    """
    Configuration parameters for mesh generation.

    Attributes
    ----------
    earth_radius : float
        Earth radius in meters.
    mesh_iterations : int
        Maximum iterations for mesh optimization.
    quality_limit : float
        Target mesh quality (0-1, higher is better).
    quality_tolerance : float
        Convergence tolerance for optimization.
    optimization_iterations : int
        Maximum optimization iterations.
    verbosity : int
        JIGSAW verbosity level (0-3).
    """
    earth_radius: float = EARTH_RADIUS_M
    mesh_iterations: int = 5_000_000
    quality_limit: float = 0.9375
    quality_tolerance: float = 1.0e-6
    optimization_iterations: int = 5_000_000
    verbosity: int = 1


def _check_jigsaw_available() -> bool:
    """Check if JIGSAW is available in the system."""
    try:
        result = subprocess.run(
            ['jigsaw', '--help'],
            capture_output=True,
            timeout=5
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _check_jigsawpy_available() -> bool:
    """Check if jigsawpy Python package is available."""
    try:
        import jigsawpy
        return True
    except ImportError:
        return False


def generate_spherical_mesh(
    cell_width: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    output_path: Union[str, Path],
    config: Optional[MeshConfig] = None
) -> Path:
    """
    Generate a spherical mesh using JIGSAW.

    Creates a variable-resolution spherical mesh based on the provided
    cell width function. The mesh is generated using Delaunay triangulation
    and optimized for cell quality.

    Parameters
    ----------
    cell_width : ndarray
        2D array (nlat x nlon) of target cell widths in km.
    lon : ndarray
        1D array of longitudes in degrees.
    lat : ndarray
        1D array of latitudes in degrees.
    output_path : str or Path
        Base path for output files (without extension).
    config : MeshConfig, optional
        Mesh generation configuration. Uses defaults if not provided.

    Returns
    -------
    mesh_file : Path
        Path to the generated mesh file (.msh format).

    Raises
    ------
    ImportError
        If jigsawpy is not installed.
    RuntimeError
        If JIGSAW mesh generation fails.

    Notes
    -----
    JIGSAW generates a triangular mesh on the sphere. The mesh is later
    converted to MPAS format (Voronoi dual) using mpas_tools.
    """
    if not _check_jigsawpy_available():
        raise ImportError(
            "jigsawpy is required for mesh generation. "
            "Install with: conda install -c conda-forge jigsawpy"
        )

    import jigsawpy as jig

    if config is None:
        config = MeshConfig()

    output_path = Path(output_path)
    basename = str(output_path)

    # Setup JIGSAW options
    opts = jig.jigsaw_jig_t()
    opts.geom_file = basename + '.msh'
    opts.jcfg_file = basename + '.jig'
    opts.mesh_file = basename + '-MESH.msh'
    opts.hfun_file = basename + '-HFUN.msh'

    # Save cell width function (HFUN - mesh sizing function)
    hmat = jig.jigsaw_msh_t()
    hmat.mshID = 'ELLIPSOID-GRID'
    hmat.xgrid = np.radians(lon)
    hmat.ygrid = np.radians(lat)
    hmat.value = cell_width
    jig.savemsh(opts.hfun_file, hmat)

    # Define geometry (ellipsoidal Earth)
    geom = jig.jigsaw_msh_t()
    geom.mshID = 'ELLIPSOID-MESH'
    geom.radii = config.earth_radius * 1e-3 * np.ones(3, float)  # km
    jig.savemsh(opts.geom_file, geom)

    # Configure mesh generation parameters
    opts.hfun_scal = 'absolute'
    opts.hfun_hmax = float("inf")
    opts.hfun_hmin = 0.0
    opts.mesh_dims = +2  # 2D surface mesh
    opts.mesh_iter = config.mesh_iterations
    opts.optm_qlim = config.quality_limit
    opts.optm_qtol = config.quality_tolerance
    opts.optm_iter = config.optimization_iterations
    opts.verbosity = config.verbosity

    jig.savejig(opts.jcfg_file, opts)

    # Run JIGSAW
    print("\n" + "=" * 60)
    print("JIGSAW Mesh Generator")
    print("=" * 60)
    print(f"Output: {opts.mesh_file}")
    print(f"Resolution range: {np.min(cell_width):.1f} - {np.max(cell_width):.1f} km")
    print("This may take several minutes for high-resolution meshes...")
    print("=" * 60 + "\n")

    return_code = subprocess.call(['jigsaw', opts.jcfg_file])

    if return_code != 0:
        raise RuntimeError(f"JIGSAW failed with return code {return_code}")

    print("\n" + "=" * 60)
    print("JIGSAW completed successfully!")
    print("=" * 60 + "\n")

    return Path(opts.mesh_file)


def generate_icosahedral_mesh(
    output_path: Union[str, Path],
    level: int = 4
) -> Path:
    """
    Generate an icosahedral mesh using JIGSAW.

    Creates a quasi-uniform spherical mesh by recursively subdividing
    an icosahedron. This is the most common choice for global uniform
    resolution simulations.

    Parameters
    ----------
    output_path : str or Path
        Base path for output files.
    level : int, optional
        Refinement level (default: 4). Each level approximately doubles
        the number of cells:
        - Level 2: ~640 cells (~500 km)
        - Level 4: ~10,000 cells (~120 km)
        - Level 6: ~160,000 cells (~30 km)
        - Level 8: ~2,500,000 cells (~7 km)

    Returns
    -------
    mesh_file : Path
        Path to the generated mesh file.

    Raises
    ------
    ImportError
        If jigsawpy is not installed.
    ValueError
        If level is outside valid range.
    """
    if not _check_jigsawpy_available():
        raise ImportError(
            "jigsawpy is required for mesh generation. "
            "Install with: conda install -c conda-forge jigsawpy"
        )

    if level < 0 or level > 12:
        raise ValueError(f"Level must be between 0 and 12, got {level}")

    import jigsawpy as jig

    output_path = Path(output_path)
    basename = str(output_path)

    # Setup JIGSAW
    opts = jig.jigsaw_jig_t()
    icos = jig.jigsaw_msh_t()
    geom = jig.jigsaw_msh_t()

    opts.geom_file = basename + '.msh'
    opts.jcfg_file = basename + '.jig'
    opts.mesh_file = basename + '-MESH.msh'

    # Unit sphere geometry
    geom.mshID = "ellipsoid-mesh"
    geom.radii = np.full(3, 1.0, dtype=geom.REALS_t)
    jig.savemsh(opts.geom_file, geom)

    # JIGSAW options for icosahedral mesh
    opts.hfun_hmax = +1.0
    opts.mesh_dims = +2
    opts.optm_iter = +5120
    opts.optm_qtol = +1.0e-08

    print("\n" + "=" * 60)
    print("Generating Icosahedral Mesh")
    print("=" * 60)
    print(f"Level: {level}")
    print(f"Approximate resolution: {7054 / (2**level):.1f} km")
    print("=" * 60 + "\n")

    # Generate icosahedral mesh
    jig.cmd.icosahedron(opts, level, icos)

    print("\n" + "=" * 60)
    print("Icosahedral mesh generated successfully!")
    print("=" * 60 + "\n")

    return Path(opts.mesh_file)


def generate_uniform_mesh(
    resolution_km: float,
    output_path: Union[str, Path],
    config: Optional[MeshConfig] = None
) -> Path:
    """
    Generate a uniform-resolution spherical mesh.

    This is a convenience function that creates a mesh with constant
    cell size across the entire sphere.

    Parameters
    ----------
    resolution_km : float
        Target cell size in kilometers.
    output_path : str or Path
        Base path for output files.
    config : MeshConfig, optional
        Mesh generation configuration.

    Returns
    -------
    mesh_file : Path
        Path to the generated mesh file.
    """
    # Create lat-lon grid for cell width function
    dlat = resolution_km / 1000.0
    nlat = int(180.0 / dlat) + 1
    nlon = int(360.0 / dlat) + 1

    lat = np.linspace(-90.0, 90.0, nlat)
    lon = np.linspace(-180.0, 180.0, nlon)

    # Constant cell width
    cell_width = resolution_km * np.ones((nlat, nlon))

    return generate_spherical_mesh(
        cell_width=cell_width,
        lon=lon,
        lat=lat,
        output_path=output_path,
        config=config
    )


@dataclass
class MeshInfo:
    """
    Information about a generated mesh.

    Attributes
    ----------
    n_cells : int
        Number of mesh cells.
    n_vertices : int
        Number of mesh vertices.
    n_edges : int
        Number of mesh edges.
    min_resolution : float
        Minimum cell size in km.
    max_resolution : float
        Maximum cell size in km.
    mean_resolution : float
        Mean cell size in km.
    mesh_file : Path
        Path to mesh file.
    """
    n_cells: int = 0
    n_vertices: int = 0
    n_edges: int = 0
    min_resolution: float = 0.0
    max_resolution: float = 0.0
    mean_resolution: float = 0.0
    mesh_file: Path = field(default_factory=Path)


def get_mesh_info(mesh_file: Union[str, Path]) -> MeshInfo:
    """
    Extract information from a JIGSAW mesh file.

    Parameters
    ----------
    mesh_file : str or Path
        Path to the mesh file.

    Returns
    -------
    info : MeshInfo
        Mesh statistics and information.
    """
    if not _check_jigsawpy_available():
        raise ImportError("jigsawpy is required to read mesh files")

    import jigsawpy as jig

    mesh = jig.jigsaw_msh_t()
    jig.loadmsh(str(mesh_file), mesh)

    info = MeshInfo(mesh_file=Path(mesh_file))

    # Extract mesh statistics
    if hasattr(mesh, 'tria3') and mesh.tria3 is not None:
        info.n_cells = len(mesh.tria3.index)

    if hasattr(mesh, 'vert3') and mesh.vert3 is not None:
        info.n_vertices = len(mesh.vert3.coord)

    if hasattr(mesh, 'edge2') and mesh.edge2 is not None:
        info.n_edges = len(mesh.edge2.index)

    return info
