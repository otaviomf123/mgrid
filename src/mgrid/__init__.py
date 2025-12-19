"""
mgrid: Variable-resolution mesh generation for MPAS-based atmospheric models.

This package provides tools for creating variable-resolution spherical
meshes for MPAS-based atmospheric models, including MPAS (Model for
Prediction Across Scales) and MONAN (Modelo para Previsão do Tempo
e Oceanos em Novas Arquiteturas).

Quick Start
-----------
Generate a simple uniform resolution grid:

    >>> from mgrid import generate_mesh, save_grid
    >>> grid = generate_mesh(resolution=30)  # 30 km
    >>> save_grid(grid, 'my_grid.nc')

Generate from a configuration file:

    >>> grid = generate_mesh(config='my_config.json')
    >>> save_grid(grid, 'variable_res_grid.nc')

One-liner for quick grid generation:

    >>> from mgrid import quick_grid
    >>> quick_grid(resolution=50, output='global_50km.nc')

Features
--------
- Uniform resolution spherical meshes
- Icosahedral quasi-uniform meshes
- Variable resolution with circular and polygonal refinement regions
- Smooth transition zones between resolutions
- JIGSAW integration for high-quality Voronoi mesh generation
- Export to MPAS-compatible NetCDF format

Classes
-------
Grid
    Container for generated grid data and metadata.
CircularRegion
    Circular refinement region defined by center and radius.
PolygonRegion
    Polygonal refinement region defined by vertices.

Functions
---------
generate_mesh
    Main function for generating meshes with various configurations.
generate_icosahedral
    Generate quasi-uniform icosahedral mesh.
save_grid
    Save grid to MPAS NetCDF format.
quick_grid
    Generate and save a grid in one step.
load_config
    Load configuration from JSON file.
plot_cell_width
    Visualize cell width distribution.

Author
------
Based on scripts by Pedro S. Peixoto <ppeixoto@usp.br>
Packaged and extended for MONAN project.

License
-------
MIT License
"""

__version__ = "0.1.0"
__author__ = "MONAN Development Team"

# High-level API functions
from .api import (
    Grid,
    generate_mesh,
    generate_icosahedral,
    save_grid,
    quick_grid,
)

# Region classes for custom refinement
from .regions import (
    Region,
    CircularRegion,
    PolygonRegion,
    compute_cell_width,
    region_from_dict,
    regions_from_config,
)

# I/O utilities
from .io import (
    load_config,
    save_config,
    validate_config,
    convert_to_mpas,
    read_mpas_grid,
    save_cell_width,
)

# Geometry utilities
from .geometry import (
    haversine_distance,
    degrees_to_km,
    km_to_degrees,
    spherical_to_cartesian,
    cartesian_to_spherical,
    icosahedral_resolution,
    level_for_resolution,
    EARTH_RADIUS_KM,
    EARTH_RADIUS_M,
)

# Mesh generation
from .mesh import (
    MeshConfig,
    generate_spherical_mesh,
    generate_icosahedral_mesh,
    generate_uniform_mesh,
    get_mesh_info,
)

# Visualization (optional import)
try:
    from .plotting import (
        plot_cell_width,
        plot_region_overview,
    )
except ImportError:
    # matplotlib not available
    pass

# MPAS Limited-Area integration (optional)
try:
    from .limited_area import (
        generate_pts_file,
        generate_pts_from_config,
        create_regional_mesh,
        create_regional_mesh_python,
        plot_region,
        partition_mesh,
        run_full_pipeline,
    )
except ImportError:
    # MPAS-Limited-Area not available
    pass


__all__ = [
    # Version
    "__version__",
    # High-level API
    "Grid",
    "generate_mesh",
    "generate_icosahedral",
    "save_grid",
    "quick_grid",
    # Regions
    "Region",
    "CircularRegion",
    "PolygonRegion",
    "compute_cell_width",
    "region_from_dict",
    "regions_from_config",
    # I/O
    "load_config",
    "save_config",
    "validate_config",
    "convert_to_mpas",
    "read_mpas_grid",
    "save_cell_width",
    # Geometry
    "haversine_distance",
    "degrees_to_km",
    "km_to_degrees",
    "spherical_to_cartesian",
    "cartesian_to_spherical",
    "icosahedral_resolution",
    "level_for_resolution",
    "EARTH_RADIUS_KM",
    "EARTH_RADIUS_M",
    # Mesh
    "MeshConfig",
    "generate_spherical_mesh",
    "generate_icosahedral_mesh",
    "generate_uniform_mesh",
    "get_mesh_info",
    # Plotting
    "plot_cell_width",
    "plot_region_overview",
    # Limited-Area
    "generate_pts_file",
    "generate_pts_from_config",
    "create_regional_mesh",
    "create_regional_mesh_python",
    "plot_region",
    "partition_mesh",
    "run_full_pipeline",
]
