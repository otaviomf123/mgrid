Quick Start
===========

This guide shows how to generate variable-resolution meshes with mgrid.

Basic Usage
-----------

Generate a uniform resolution grid:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   # Generate a 30 km global grid
   grid = generate_mesh(resolution=30)

   # Save to MPAS format
   save_grid(grid, 'global_30km.nc')

Variable Resolution with Circular Region
----------------------------------------

Create a high-resolution region within a coarser global mesh:

.. code-block:: python

   from mgrid import generate_mesh, save_grid, CircularRegion

   # Define a refinement region
   region = CircularRegion(
       name='Amazon',
       resolution=5.0,          # 5 km inside the region
       transition_width=50.0,   # 50 km smooth transition
       center=(-3.0, -60.0),    # (lat, lon) center point
       radius=500.0             # 500 km radius
   )

   # Generate with 100 km background resolution
   grid = generate_mesh(
       regions=[region],
       background_resolution=100.0
   )

   save_grid(grid, 'amazon_5km.nc')

Variable Resolution with Polygon Region
---------------------------------------

Use a polygonal boundary for the refinement region:

.. code-block:: python

   from mgrid import generate_mesh, save_grid, PolygonRegion

   # Define a state boundary (example: Goiás, Brazil)
   region = PolygonRegion(
       name='Goias',
       resolution=10.0,         # 10 km inside
       transition_width=30.0,   # 30 km transition
       vertices=[
           (-12.4, -50.2),      # (lat, lon)
           (-19.5, -50.8),
           (-18.7, -52.4),
           (-16.5, -53.2),
           (-14.0, -50.8),
       ]
   )

   grid = generate_mesh(regions=[region], background_resolution=100.0)
   save_grid(grid, 'goias_10km.nc')

Multiple Nested Regions
-----------------------

Create a hierarchy of resolutions:

.. code-block:: python

   from mgrid import generate_mesh, save_grid, CircularRegion, PolygonRegion

   # Outer region: state-level (15 km)
   state = PolygonRegion(
       name='State',
       resolution=15.0,
       transition_width=30.0,
       vertices=[
           (-19.0, -53.0),
           (-19.0, -44.0),
           (-25.5, -44.0),
           (-25.5, -53.0),
       ]
   )

   # Inner region: metropolitan area (3 km)
   metro = CircularRegion(
       name='Metropolitan',
       resolution=3.0,
       transition_width=10.0,
       center=(-23.55, -46.63),  # São Paulo
       radius=80.0
   )

   # Generate with 60 km background
   grid = generate_mesh(
       regions=[state, metro],
       background_resolution=60.0
   )

   save_grid(grid, 'saopaulo_nested.nc')

Using Configuration Files
-------------------------

Create a JSON configuration file:

.. code-block:: json

   {
       "background_resolution": 60.0,
       "grid_density": 0.05,
       "regions": [
           {
               "name": "State",
               "type": "polygon",
               "polygon": [
                   [-19.0, -53.0],
                   [-19.0, -44.0],
                   [-25.5, -44.0],
                   [-25.5, -53.0]
               ],
               "resolution": 15.0,
               "transition_start": 30.0
           },
           {
               "name": "Metro",
               "type": "circle",
               "center": [-23.55, -46.63],
               "radius": 80,
               "resolution": 3.0,
               "transition_start": 15.0
           }
       ]
   }

Load and use it:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   grid = generate_mesh(config='my_config.json')
   save_grid(grid, 'my_grid.nc')

Visualization
-------------

Plot the cell width distribution:

.. code-block:: python

   from mgrid import generate_mesh, plot_cell_width

   grid = generate_mesh(config='my_config.json')
   plot_cell_width(grid, output='cell_width.png')

Next Steps
----------

- See :doc:`pipeline` for the complete mesh generation workflow
- See :doc:`regions` for detailed region configuration
- See :doc:`examples` for more complex examples
