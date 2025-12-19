# mgrid

Variable-resolution mesh generation for MPAS-based atmospheric models.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue.svg)](https://mgrid.readthedocs.io)

---

**Documentation:** [https://mgrid.readthedocs.io](https://mgrid.readthedocs.io)

**Source Code:** [https://github.com/otaviomf123/mgrid](https://github.com/otaviomf123/mgrid)

---

## Overview

**mgrid** is a complete solution for generating variable-resolution spherical meshes for MPAS-based atmospheric models. It provides an end-to-end pipeline from geographic data (shapefiles) to production-ready partitioned meshes for parallel execution.

Compatible with:
- **MPAS** (Model for Prediction Across Scales)
- **MONAN** (Model for Ocean-laNd-Atmosphere PredictioN)
- Any model using MPAS mesh format

![Variable Resolution Grid Example](docs/source/_static/example_variable_resolution.png)

*Example: Multi-resolution grid for Goiás state (Brazil) with 1 km metropolitan area, 3 km state coverage, and 30 km global background. Shapefiles from [DIVA-GIS](https://diva-gis.org/data.html).*

## Complete Pipeline

```
Shapefile → Configuration → Cell Width → JIGSAW Mesh → MPAS Format → Regional Cut → MPI Partition
```

| Step | Description | Tool |
|------|-------------|------|
| 1 | Extract polygon from shapefile | GeoPandas |
| 2 | Define resolution zones | mgrid |
| 3 | Compute cell width function | mgrid |
| 4 | Generate spherical mesh | JIGSAW |
| 5 | Convert to MPAS format | mpas_tools |
| 6 | Cut regional domain | MPAS-Limited-Area |
| 7 | Partition for MPI | METIS (gpmetis) |

## Installation

### Recommended: Conda Environment

```bash
# Create new environment
conda create -n mgrid python=3.11 -y
conda activate mgrid

# Install dependencies from conda-forge
conda install -c conda-forge numpy scipy matplotlib cartopy xarray netcdf4 -y
conda install -c conda-forge shapely pyproj geopandas -y
conda install -c conda-forge jigsawpy mpas_tools metis -y

# Install mgrid
pip install -e .
```

### Quick Install (pip only)

```bash
pip install mgrid[full]
```

Note: Some dependencies (jigsawpy, mpas_tools, metis) require conda for full functionality.

### Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| numpy | Core arrays | pip/conda |
| shapely | Polygon operations | pip/conda |
| geopandas | Shapefile reading | conda |
| jigsawpy | Mesh generation | conda |
| mpas_tools | MPAS format conversion | conda |
| metis | Graph partitioning | conda |
| matplotlib | Visualization | pip/conda |
| basemap | Map projections | conda |

## Quick Start

### Simple Variable Resolution Grid

```python
from mgrid import generate_mesh, save_grid, CircularRegion, PolygonRegion

# Define refinement regions
metro_region = CircularRegion(
    name='Metropolitan',
    resolution=3.0,           # 3 km resolution
    transition_width=10.0,    # 10 km transition zone
    center=(-23.55, -46.63),  # São Paulo (lat, lon)
    radius=100.0              # 100 km radius
)

state_region = PolygonRegion(
    name='State',
    resolution=15.0,          # 15 km resolution
    transition_width=30.0,    # 30 km transition zone
    vertices=[
        (-19.0, -53.0),       # (lat, lon)
        (-19.0, -44.0),
        (-25.5, -44.0),
        (-25.5, -53.0),
    ]
)

# Generate mesh with 60 km global background
grid = generate_mesh(
    regions=[metro_region, state_region],
    background_resolution=60.0
)

# Save cell width function
save_grid(grid, 'saopaulo_grid.nc')
```

### Complete Pipeline (Command Line)

```bash
# Full pipeline: shapefile → mesh → cut → partition (64 MPI processes)
python examples/09_goias_shapefile_grid.py \
    --global-grid /path/to/x1.40962.grid.nc \
    --nprocs 64
```

Output files:
```
output/goias_shapefile/
├── goias_shapefile_config.json      # Configuration
├── goias_regional.grid.nc           # Regional MPAS grid
├── goias_regional.graph.info        # Graph file
└── goias_regional.graph.info.part.64  # MPI partition
```

### Run MPAS/MONAN

```bash
# Copy files to run directory
cp output/goias_shapefile/goias_regional.grid.nc ./
cp output/goias_shapefile/goias_regional.graph.info.part.64 ./

# Execute model
mpirun -np 64 ./atmosphere_model
```

## Features

### Mesh Generation
- **Uniform Resolution**: Global meshes with constant cell size
- **Icosahedral Grids**: Quasi-uniform meshes from subdivided icosahedron
- **Variable Resolution**: Multiple nested refinement regions
- **Smooth Transitions**: Configurable transition zones between resolutions

### Region Types
- **CircularRegion**: Circular refinement areas
- **PolygonRegion**: Arbitrary polygon shapes (from shapefiles)

### Integration
- **JIGSAW**: High-quality Voronoi mesh generation
- **MPAS-Limited-Area**: Regional domain extraction
- **METIS**: Graph partitioning for parallel execution
- **Shapefile Support**: Direct import from GADM, Natural Earth, etc.

### Output Formats
- **MPAS NetCDF**: Ready for MPAS/MONAN execution
- **JIGSAW MSH**: Intermediate mesh format
- **Graph Info**: For partitioning tools
- **PTS Files**: MPAS-Limited-Area specifications

## Examples

| Example | Description |
|---------|-------------|
| `01_uniform_grid.py` | Uniform resolution global grid |
| `02_icosahedral_grid.py` | Icosahedral mesh generation |
| `03_variable_resolution.py` | Single circular refinement |
| `04_polygon_region.py` | Polygon-based refinement |
| `05_nested_regions.py` | Multiple nested regions |
| `06_from_config.py` | Configuration file usage |
| `07_quick_grid.py` | One-liner generation |
| `08_goias_nested_grid.py` | Goiás state with Basemap |
| `09_goias_shapefile_grid.py` | **Complete pipeline example** |
| `10_shapefile_polygon_extraction.py` | Extract polygons from shapefiles |

## API Reference

### High-Level Functions

```python
from mgrid import (
    generate_mesh,          # Generate mesh with configuration
    generate_icosahedral,   # Generate icosahedral mesh
    save_grid,              # Save to MPAS format
    quick_grid,             # One-liner generation
)
```

### Region Classes

```python
from mgrid import (
    CircularRegion,         # Circular refinement
    PolygonRegion,          # Polygon refinement
)
```

### Limited-Area Integration

```python
from mgrid import (
    generate_pts_file,      # Generate .pts specification
    create_regional_mesh,   # Cut regional mesh
    partition_mesh,         # Partition with METIS
    run_full_pipeline,      # Complete cut + partition
)
```

### Geometry Utilities

```python
from mgrid import (
    haversine_distance,     # Great circle distance
    degrees_to_km,          # Coordinate conversion
    km_to_degrees,          # Coordinate conversion
)
```

## Configuration File Format

```json
{
    "background_resolution": 60.0,
    "grid_density": 0.05,
    "regions": [
        {
            "name": "HighRes_Metro",
            "type": "circle",
            "center": [-16.71, -49.24],
            "radius": 105,
            "resolution": 1.0,
            "transition_start": 3.0
        },
        {
            "name": "MedRes_State",
            "type": "polygon",
            "polygon": [[-12.4, -50.2], [-19.5, -50.8], ...],
            "resolution": 3.0,
            "transition_start": 5.0
        }
    ]
}
```

## Icosahedral Grid Resolutions

| Level | Resolution | Cells | Use Case |
|-------|------------|-------|----------|
| 4 | ~120 km | ~10,000 | Testing |
| 5 | ~60 km | ~40,000 | Coarse global |
| 6 | ~30 km | ~160,000 | Standard global |
| 7 | ~15 km | ~650,000 | High-res global |
| 8 | ~7 km | ~2,500,000 | Very high-res |

## Contributing

Contributions are welcome. Please submit issues and pull requests on GitHub.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Shapefile Data Sources

The Goiás example uses administrative boundary shapefiles from [DIVA-GIS](https://diva-gis.org/data.html), which provides free geographic data for all countries. The shapefiles follow administrative levels:

| Level | Description | Shapefile | Example |
|-------|-------------|-----------|---------|
| 0 | National boundaries | BRA_adm0.shp | Brazil |
| 1 | State/regional boundaries | BRA_adm1.shp | Goiás |
| 2 | Municipal boundaries | BRA_adm2.shp | Goiânia |

To download shapefiles for your region:
1. Visit [https://diva-gis.org/gdata](https://diva-gis.org/gdata)
2. Select your country
3. Choose "Administrative areas" subject
4. Download and extract the ZIP file

## Acknowledgments

- Pedro S. Peixoto (USP) - Original mesh generation scripts
- JIGSAW by Darren Engwirda - Mesh generation engine
- MPAS-Tools by Los Alamos National Laboratory
- MPAS-Limited-Area by Michael Duda
- [DIVA-GIS](https://diva-gis.org) - Administrative boundary shapefiles

## Citation

```bibtex
@software{mgrid,
  title = {mgrid: Variable-resolution mesh generation for MPAS-based atmospheric models},
  author = {MONAN Development Team},
  year = {2024},
  url = {https://github.com/otaviomf123/mgrid}
}
```
