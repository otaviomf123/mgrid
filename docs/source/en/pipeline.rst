Complete Pipeline
=================

This guide describes the complete workflow from geographic data to
production-ready MPAS/MONAN meshes.

Pipeline Overview
-----------------

.. code-block:: text

   Shapefile → Config → Cell Width → JIGSAW → MPAS grid → Static File → Regional Cut → Partition

.. list-table::
   :header-rows: 1
   :widths: 10 35 20

   * - Step
     - Description
     - Tool
   * - 1
     - Extract polygon from shapefile
     - GeoPandas
   * - 2
     - Define resolution zones
     - mgrid
   * - 3
     - Compute cell width function
     - mgrid
   * - 4
     - Generate spherical mesh
     - JIGSAW
   * - 5
     - Convert to MPAS format
     - mpas_tools
   * - 6
     - **Generate static file (geographic data)**
     - **MPAS init_atmosphere**
   * - 7
     - Cut regional domain
     - mgrid (MPAS-Limited-Area)
   * - 8
     - Partition for MPI
     - METIS (gpmetis)

.. important::

   **Step 6 (Static File Generation)** is performed **outside mgrid** using MPAS ``init_atmosphere``.
   The static file combines the grid with geographic data (terrain, land use, soil type, etc.)
   required for simulation. See `MPAS Documentation <https://www2.mmm.ucar.edu/projects/mpas/site/documentation/mpas_overview.html>`_
   for detailed instructions.

Pre-made Grids (Alternative)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For quick testing or when custom resolution is not needed, you can skip steps 1-5
and download pre-generated MPAS grids from:

`MPAS Atmosphere Meshes <https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html>`_

Available resolutions: 3km, 7.5km, 15km, 30km, 60km, 120km, 240km, 480km.

Step-by-Step Guide
------------------

Step 1: Extract Polygon from Shapefile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use GeoPandas to load and extract geographic boundaries. Shapefiles can be
downloaded from `DIVA-GIS <https://diva-gis.org/gdata>`_, which provides free
administrative boundary data for all countries:

- **Level 0** (BRA_adm0.shp): National boundaries (Brazil)
- **Level 1** (BRA_adm1.shp): State/regional boundaries (Goiás, São Paulo, etc.)
- **Level 2** (BRA_adm2.shp): Municipal boundaries (Goiânia, São Paulo, etc.)

To download shapefiles:

1. Visit https://diva-gis.org/gdata
2. Select your country
3. Choose "Administrative areas" as subject
4. Download and extract the ZIP file

.. code-block:: python

   import geopandas as gpd

   # Load shapefile (downloaded from DIVA-GIS)
   states = gpd.read_file('BRA_adm1.shp')

   # Filter by attribute
   goias = states[states['NAME_1'] == 'Goiás']

   # Get geometry
   geometry = goias.geometry.iloc[0]

   # Simplify for efficiency
   simplified = geometry.simplify(0.1, preserve_topology=True)

   # Extract coordinates as [lat, lon]
   vertices = []
   for lon, lat in simplified.exterior.coords[:-1]:
       vertices.append([lat, lon])

Step 2: Create Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Define the resolution hierarchy:

.. code-block:: python

   config = {
       "background_resolution": 30.0,
       "regions": [
           {
               "name": "Regional_Buffer",
               "type": "polygon",
               "polygon": [[-10.9, -54.8], [-10.9, -44.4],
                          [-21.0, -44.4], [-21.0, -54.8]],
               "resolution": 5.0,
               "transition_start": 30.0
           },
           {
               "name": "State",
               "type": "polygon",
               "polygon": vertices,  # From step 1
               "resolution": 3.0,
               "transition_start": 5.0
           },
           {
               "name": "Metropolitan",
               "type": "circle",
               "center": [-16.71, -49.24],
               "radius": 105,
               "resolution": 1.0,
               "transition_start": 3.0
           }
       ]
   }

Step 3: Compute Cell Width Function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate the mesh sizing field:

.. code-block:: python

   from mgrid import generate_mesh, save_config

   # Save configuration
   save_config(config, 'my_config.json')

   # Generate cell width function
   grid = generate_mesh(
       config=config,
       output_path='output/my_mesh',
       generate_jigsaw=True  # Run JIGSAW
   )

   print(grid.summary())

Step 4-5: Generate JIGSAW Mesh and Convert to MPAS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This happens automatically when ``generate_jigsaw=True``:

.. code-block:: python

   from mgrid.io import convert_to_mpas

   # If mesh was generated
   if grid.mesh_file:
       convert_to_mpas(
           mesh_file=grid.mesh_file,
           output_file='output/my_grid.nc'
       )

Step 6: Generate Static File (External - MPAS init)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important::

   This step is performed **outside mgrid** using MPAS ``init_atmosphere``.

The static file combines the grid with geographic data (terrain, land use,
soil type, vegetation, etc.) required for atmospheric simulation.

**Prerequisites:**

- MPAS ``init_atmosphere`` executable (compiled from MPAS source)
- Geographic data files (GEOGRID, terrain, land use datasets)

**Configuration:**

Configure ``namelist.init_atmosphere`` with:

- ``config_static_interp = true``
- Path to the grid file generated in Step 5

For detailed instructions, see the official documentation:

- `MPAS Overview <https://www2.mmm.ucar.edu/projects/mpas/site/documentation/mpas_overview.html>`_
- `MPAS-Atmosphere Tutorial <https://www2.mmm.ucar.edu/projects/mpas/tutorial/>`_

Step 7: Cut Regional Domain
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate a specification file and cut the regional mesh from the static file:

.. code-block:: python

   from mgrid import generate_pts_file, create_regional_mesh_python

   # Generate .pts file
   pts_file = generate_pts_file(
       output_path='output/my_region.pts',
       name='my_region',
       region_type='custom',
       inside_point=(-16.0, -49.5),  # (lat, lon) inside the region
       polygon=vertices
   )

   # Cut regional mesh from static file
   regional_grid, graph_file = create_regional_mesh_python(
       pts_file=pts_file,
       global_grid_file='static.nc'  # Use the static file generated in Step 6
   )

   print(f"Regional grid: {regional_grid}")
   print(f"Graph file: {graph_file}")

Step 8: Partition for MPI
^^^^^^^^^^^^^^^^^^^^^^^^^

Partition the mesh for parallel execution:

.. code-block:: python

   from mgrid import partition_mesh

   # Partition for 64 MPI processes
   partition_file = partition_mesh(
       graph_file=graph_file,
       num_partitions=64,
       minconn=True,   # Minimize connectivity
       contig=True,    # Force contiguous partitions
       niter=200       # Refinement iterations
   )

   print(f"Partition file: {partition_file}")

Complete Pipeline Function
--------------------------

Use ``run_full_pipeline`` for steps 7-8 (after generating static file):

.. code-block:: python

   from mgrid import run_full_pipeline

   results = run_full_pipeline(
       pts_file='output/my_region.pts',
       global_grid_file='static.nc',  # Use static file from Step 6
       num_partitions=[32, 64, 128]   # Multiple partitions supported
   )

   print(f"Regional grid: {results['regional_grid']}")
   print(f"Partition files: {results['partition_files']}")

Command-Line Example
--------------------

The ``09_goias_shapefile_grid.py`` example demonstrates the complete pipeline:

.. code-block:: bash

   # Quick run: configuration + cell width + plots only
   python examples/09_goias_shapefile_grid.py

   # Full pipeline with JIGSAW mesh generation
   python examples/09_goias_shapefile_grid.py --jigsaw

   # Complete pipeline with existing static file + multiple partitions
   python examples/09_goias_shapefile_grid.py \
       --global-grid static.nc \
       --nprocs 32 64 128

Output Files
------------

The complete pipeline generates:

.. code-block:: text

   output/
   ├── my_config.json                    # Configuration
   ├── my_mesh-HFUN.msh                  # JIGSAW cell width
   ├── my_mesh-MESH.msh                  # JIGSAW mesh
   ├── my_grid.nc                        # Global MPAS grid
   │
   │   [External: Generate static.nc using MPAS init_atmosphere]
   │
   ├── my_region.pts                     # Region specification
   ├── my_region.grid.nc                 # Regional MPAS grid
   ├── my_region.graph.info              # Graph file
   ├── my_region.graph.info.part.32      # MPI partition (32 procs)
   ├── my_region.graph.info.part.64      # MPI partition (64 procs)
   └── my_region.graph.info.part.128     # MPI partition (128 procs)

Running MPAS/MONAN
------------------

After the pipeline completes:

.. code-block:: bash

   # Copy files to run directory
   cp output/my_region.grid.nc ./
   cp output/my_region.graph.info.part.64 ./

   # Execute model with 64 MPI processes
   mpirun -np 64 ./atmosphere_model

The model will automatically use the partition file to distribute cells
across MPI processes.

Performance Considerations
--------------------------

- **JIGSAW mesh generation**: Can take hours for high-resolution global meshes
- **Static file generation**: Depends on geographic data resolution
- **Regional cut**: Much faster, typically seconds to minutes
- **Use existing global grids**: Download pre-generated grids when possible

Pre-generated global grids are available from:

- `MPAS Atmosphere Meshes <https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html>`_
- Resolutions: 3km, 7.5km, 15km, 30km, 60km, 120km, 240km, 480km
