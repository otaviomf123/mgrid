API Reference
=============

High-Level Functions
--------------------

generate_mesh
^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import generate_mesh

   grid = generate_mesh(
       resolution=None,          # Uniform resolution (km)
       regions=None,             # List of Region objects
       background_resolution=100.0,
       config=None,              # Path to JSON config or dict
       output_path=None,         # Output file prefix
       generate_jigsaw=False,    # Run JIGSAW mesh generation
       plot=False                # Generate plots
   )

Parameters:

- **resolution**: Uniform resolution in km (for simple grids)
- **regions**: List of CircularRegion or PolygonRegion objects
- **background_resolution**: Resolution outside all regions (km)
- **config**: Path to JSON file or dict with configuration
- **output_path**: Prefix for output files
- **generate_jigsaw**: If True, run JIGSAW mesh generation
- **plot**: If True, generate visualization plots

Returns: Grid object with cell width data.

generate_icosahedral
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import generate_icosahedral

   grid = generate_icosahedral(
       level=6,                  # Subdivision level
       output_path=None
   )

Parameters:

- **level**: Icosahedral subdivision level (4-8)
- **output_path**: Output file prefix

Returns: Grid object.

save_grid
^^^^^^^^^

.. code-block:: python

   from mgrid import save_grid

   save_grid(
       grid,                     # Grid object
       output_path,              # Output file path
       format='netcdf'           # Output format
   )

quick_grid
^^^^^^^^^^

.. code-block:: python

   from mgrid import quick_grid

   quick_grid(
       resolution=30,
       output='grid.nc'
   )

Generate and save in one step.

Region Classes
--------------

CircularRegion
^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import CircularRegion

   region = CircularRegion(
       name='MyRegion',
       resolution=5.0,           # km inside region
       transition_width=20.0,    # km transition zone
       center=(-23.55, -46.63),  # (lat, lon)
       radius=100.0              # km
   )

PolygonRegion
^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import PolygonRegion

   region = PolygonRegion(
       name='MyRegion',
       resolution=10.0,
       transition_width=30.0,
       vertices=[
           (-12.4, -50.2),
           (-19.5, -50.8),
           (-18.7, -52.4),
       ]
   )

I/O Functions
-------------

load_config
^^^^^^^^^^^

.. code-block:: python

   from mgrid import load_config

   config = load_config('config.json')

save_config
^^^^^^^^^^^

.. code-block:: python

   from mgrid import save_config

   save_config(config, 'config.json')

convert_to_mpas
^^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import convert_to_mpas

   convert_to_mpas(
       mesh_file='mesh.msh',     # JIGSAW mesh
       output_file='grid.nc'     # MPAS NetCDF
   )

Limited-Area Integration
------------------------

generate_pts_file
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import generate_pts_file

   pts_file = generate_pts_file(
       output_path='region.pts',
       name='my_region',
       region_type='custom',     # 'custom', 'circle', 'ellipse', 'channel'
       inside_point=(-16.0, -49.5),
       polygon=[(-12.4, -50.2), (-19.5, -50.8), ...],
       # For circle:
       # radius=100000.0  # meters
   )

create_regional_mesh_python
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import create_regional_mesh_python

   regional_grid, graph_file = create_regional_mesh_python(
       pts_file='region.pts',
       global_grid_file='x1.40962.grid.nc',
       verbose=0
   )

partition_mesh
^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import partition_mesh

   partition_file = partition_mesh(
       graph_file='region.graph.info',
       num_partitions=64,
       minconn=True,
       contig=True,
       niter=200
   )

run_full_pipeline
^^^^^^^^^^^^^^^^^

.. code-block:: python

   from mgrid import run_full_pipeline

   results = run_full_pipeline(
       pts_file='region.pts',
       global_grid_file='x1.40962.grid.nc',
       num_partitions=64
   )

   # results['regional_grid']
   # results['graph_file']
   # results['partition_file']

Geometry Utilities
------------------

.. code-block:: python

   from mgrid import (
       haversine_distance,
       degrees_to_km,
       km_to_degrees,
       spherical_to_cartesian,
       cartesian_to_spherical,
       icosahedral_resolution,
       level_for_resolution,
       EARTH_RADIUS_KM
   )

   # Great circle distance
   dist = haversine_distance(lat1, lon1, lat2, lon2)

   # Coordinate conversion
   km = degrees_to_km(degrees, latitude=0)
   deg = km_to_degrees(km, latitude=0)

   # Icosahedral levels
   res = icosahedral_resolution(level=6)  # ~30 km
   level = level_for_resolution(30)       # 6

Grid Object
-----------

The Grid object contains:

.. code-block:: python

   grid.lat          # Latitude array
   grid.lon          # Longitude array
   grid.cell_width   # Cell width array (km)
   grid.min_resolution
   grid.max_resolution
   grid.mesh_file    # Path to JIGSAW mesh (if generated)
   grid.mpas_file    # Path to MPAS file (if converted)

   # Methods
   grid.summary()    # Print summary statistics
