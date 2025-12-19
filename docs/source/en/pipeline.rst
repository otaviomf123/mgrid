Complete Pipeline
=================

This guide describes the complete workflow from geographic data to
production-ready MPAS/MONAN meshes.

Pipeline Overview
-----------------

.. code-block:: text

   Shapefile → Configuration → Cell Width → JIGSAW Mesh → MPAS Format → Regional Cut → MPI Partition

.. list-table::
   :header-rows: 1
   :widths: 10 30 20

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
     - Cut regional domain
     - MPAS-Limited-Area
   * - 7
     - Partition for MPI
     - METIS (gpmetis)

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

Step 6: Cut Regional Domain
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Generate a specification file and cut the regional mesh:

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

   # Cut regional mesh from global grid
   regional_grid, graph_file = create_regional_mesh_python(
       pts_file=pts_file,
       global_grid_file='x1.40962.grid.nc'
   )

   print(f"Regional grid: {regional_grid}")
   print(f"Graph file: {graph_file}")

Step 7: Partition for MPI
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

Use ``run_full_pipeline`` for steps 6-7:

.. code-block:: python

   from mgrid import run_full_pipeline

   results = run_full_pipeline(
       pts_file='output/my_region.pts',
       global_grid_file='x1.40962.grid.nc',
       num_partitions=64
   )

   print(f"Regional grid: {results['regional_grid']}")
   print(f"Partition file: {results['partition_file']}")

Command-Line Example
--------------------

The ``09_goias_shapefile_grid.py`` example demonstrates the complete pipeline:

.. code-block:: bash

   # Quick run: configuration + cell width + plots
   python examples/09_goias_shapefile_grid.py

   # Full pipeline with JIGSAW mesh generation
   python examples/09_goias_shapefile_grid.py --jigsaw

   # Complete pipeline with existing global grid
   python examples/09_goias_shapefile_grid.py \
       --global-grid /path/to/x1.40962.grid.nc \
       --nprocs 64

Output Files
------------

The complete pipeline generates:

.. code-block:: text

   output/
   ├── my_config.json                    # Configuration
   ├── my_mesh-HFUN.msh                  # JIGSAW cell width
   ├── my_mesh-MESH.msh                  # JIGSAW mesh
   ├── my_grid.nc                        # Global MPAS grid
   ├── my_region.pts                     # Region specification
   ├── my_region.grid.nc                 # Regional MPAS grid
   ├── my_region.graph.info              # Graph file
   └── my_region.graph.info.part.64      # MPI partition

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
- **Regional cut**: Much faster, typically seconds to minutes
- **Use existing global grids**: Download pre-generated grids when possible

Pre-generated global grids are available from MPAS download servers with
various resolutions (3km, 7km, 15km, 30km, 60km, 120km).
