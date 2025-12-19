Configuration
=============

mgrid uses JSON configuration files for reproducible mesh generation.

Basic Structure
---------------

.. code-block:: json

   {
       "description": "Grid description",
       "author": "Author name",
       "background_resolution": 60.0,
       "grid_density": 0.05,
       "regions": [
           {
               "name": "Region1",
               "type": "circle",
               ...
           }
       ]
   }

Global Parameters
-----------------

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Default
     - Description
   * - background_resolution
     - float
     - 100.0
     - Background resolution in km
   * - grid_density
     - float
     - 0.1
     - Grid density parameter (lower = finer)
   * - description
     - string
     - ""
     - Description of the grid
   * - author
     - string
     - ""
     - Author information

Region Parameters
-----------------

Circle Region
^^^^^^^^^^^^^

.. code-block:: json

   {
       "name": "Metropolitan",
       "type": "circle",
       "center": [-23.55, -46.63],
       "radius": 100,
       "resolution": 3.0,
       "transition_start": 15.0
   }

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - name
     - string
     - Region identifier
   * - type
     - string
     - Must be "circle"
   * - center
     - [lat, lon]
     - Center coordinates
   * - radius
     - float
     - Radius in km
   * - resolution
     - float
     - Target resolution in km
   * - transition_start
     - float
     - Outer edge resolution in km

Polygon Region
^^^^^^^^^^^^^^

.. code-block:: json

   {
       "name": "State",
       "type": "polygon",
       "polygon": [
           [-12.4, -50.2],
           [-19.5, -50.8],
           [-18.7, -52.4],
           [-12.4, -50.2]
       ],
       "resolution": 5.0,
       "transition_start": 15.0
   }

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - name
     - string
     - Region identifier
   * - type
     - string
     - Must be "polygon"
   * - polygon
     - [[lat, lon], ...]
     - List of vertices
   * - resolution
     - float
     - Target resolution in km
   * - transition_start
     - float
     - Outer edge resolution in km

Complete Example
----------------

Multi-resolution grid for Goiás state:

.. code-block:: json

   {
       "description": "Multi-resolution grid for Goiás state",
       "author": "MONAN Team",
       "data_source": "GADM Brazil shapefiles",
       "background_resolution": 30.0,
       "grid_density": 0.05,
       "state_buffer_km": 50.0,
       "regions": [
           {
               "name": "Regional_Buffer",
               "type": "polygon",
               "description": "5 km buffer zone",
               "polygon": [
                   [-10.9, -54.8],
                   [-10.9, -44.4],
                   [-21.0, -44.4],
                   [-21.0, -54.8]
               ],
               "resolution": 5.0,
               "transition_start": 30.0
           },
           {
               "name": "Goias_State",
               "type": "polygon",
               "description": "3 km state coverage",
               "polygon": [
                   [-12.4, -50.2],
                   [-13.3, -49.4],
                   [-14.4, -45.9],
                   [-19.5, -50.8],
                   [-18.7, -52.4],
                   [-16.5, -53.2],
                   [-14.0, -50.8]
               ],
               "resolution": 3.0,
               "transition_start": 5.0
           },
           {
               "name": "Goiania_Metro",
               "type": "circle",
               "description": "1 km metropolitan area",
               "center": [-16.7128, -49.2418],
               "radius": 105.0,
               "resolution": 1.0,
               "transition_start": 3.0
           }
       ],
       "metadata": {
           "goias_state": {
               "original_vertices": 3311,
               "simplified_vertices": 65,
               "buffer_km": 50.0
           }
       },
       "notes": [
           "State polygon simplified from 3311 to 65 vertices",
           "Buffer ensures 3 km resolution before state border"
       ]
   }

Loading Configuration
---------------------

.. code-block:: python

   from mgrid import load_config, generate_mesh, save_grid

   # Load configuration
   config = load_config('my_config.json')

   # Generate mesh
   grid = generate_mesh(config=config)

   # Or directly
   grid = generate_mesh(config='my_config.json')

   save_grid(grid, 'my_grid.nc')

Saving Configuration
--------------------

.. code-block:: python

   from mgrid import save_config

   config = {
       "background_resolution": 30.0,
       "regions": [...]
   }

   save_config(config, 'my_config.json')

Validation
----------

Validate configuration before generation:

.. code-block:: python

   from mgrid import validate_config

   config = load_config('my_config.json')

   if validate_config(config):
       grid = generate_mesh(config=config)
   else:
       print("Invalid configuration")
