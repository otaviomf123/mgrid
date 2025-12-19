Examples
========

This section provides complete working examples.

Example 1: Uniform Resolution Grid
----------------------------------

Generate a global grid with uniform 30 km resolution:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   # Generate uniform grid
   grid = generate_mesh(resolution=30)

   print(grid.summary())
   save_grid(grid, 'global_30km.nc')

Example 2: Icosahedral Grid
---------------------------

Generate a quasi-uniform icosahedral mesh:

.. code-block:: python

   from mgrid import generate_icosahedral, save_grid

   # Level 6 gives approximately 30 km resolution
   grid = generate_icosahedral(level=6)

   print(f"Cells: {grid.ncells}")
   print(f"Resolution: ~{grid.resolution} km")

   save_grid(grid, 'icosahedral_L6.nc')

Icosahedral levels:

- Level 4: ~120 km, ~10,000 cells
- Level 5: ~60 km, ~40,000 cells
- Level 6: ~30 km, ~160,000 cells
- Level 7: ~15 km, ~650,000 cells

Example 3: Single Circular Region
---------------------------------

High-resolution region over the Amazon:

.. code-block:: python

   from mgrid import generate_mesh, save_grid, CircularRegion

   amazon = CircularRegion(
       name='Amazon',
       resolution=5.0,          # 5 km inside
       transition_width=50.0,   # 50 km transition
       center=(-3.0, -60.0),    # Manaus area
       radius=800.0             # 800 km radius
   )

   grid = generate_mesh(
       regions=[amazon],
       background_resolution=120.0
   )

   save_grid(grid, 'amazon_5km.nc')

Example 4: State Boundary from Shapefile
----------------------------------------

Load state boundary from DIVA-GIS shapefile. Shapefiles can be downloaded from
`DIVA-GIS <https://diva-gis.org/gdata>`_, which provides free administrative boundary
data for all countries with the following levels:

- **Level 0** (BRA_adm0.shp): National boundaries
- **Level 1** (BRA_adm1.shp): State/regional boundaries
- **Level 2** (BRA_adm2.shp): Municipal boundaries

.. code-block:: python

   import geopandas as gpd
   from mgrid import generate_mesh, save_grid, PolygonRegion

   # Load shapefile (download from https://diva-gis.org/gdata)
   states = gpd.read_file('BRA_adm1.shp')
   goias = states[states['NAME_1'] == 'Goiás']

   # Extract and simplify geometry
   geom = goias.geometry.iloc[0]
   simplified = geom.simplify(0.1, preserve_topology=True)

   # Extract vertices
   vertices = [(lat, lon) for lon, lat in
               simplified.exterior.coords[:-1]]

   # Create region
   goias_region = PolygonRegion(
       name='Goias',
       resolution=10.0,
       transition_width=20.0,
       vertices=vertices
   )

   grid = generate_mesh(
       regions=[goias_region],
       background_resolution=100.0
   )

   save_grid(grid, 'goias_10km.nc')

Example 5: Multi-Resolution Nested Grid
---------------------------------------

Three-level resolution hierarchy:

.. code-block:: python

   from mgrid import (
       generate_mesh, save_grid,
       CircularRegion, PolygonRegion
   )

   # Level 1: Regional buffer (5 km)
   regional = PolygonRegion(
       name='Regional',
       resolution=5.0,
       transition_width=25.0,
       vertices=[
           (-10.9, -54.8),
           (-10.9, -44.4),
           (-21.0, -44.4),
           (-21.0, -54.8),
       ]
   )

   # Level 2: State boundary (3 km)
   state = PolygonRegion(
       name='State',
       resolution=3.0,
       transition_width=2.0,
       vertices=[
           (-12.4, -50.2),
           (-14.4, -45.9),
           (-19.5, -50.8),
           (-18.7, -52.4),
           (-14.0, -50.8),
       ]
   )

   # Level 3: Metropolitan area (1 km)
   metro = CircularRegion(
       name='Metro',
       resolution=1.0,
       transition_width=2.0,
       center=(-16.71, -49.24),
       radius=105.0
   )

   grid = generate_mesh(
       regions=[regional, state, metro],
       background_resolution=30.0
   )

   save_grid(grid, 'nested_grid.nc')

Example 6: Complete Pipeline
----------------------------

From shapefile to partitioned MPAS mesh:

.. code-block:: python

   import geopandas as gpd
   from mgrid import (
       generate_mesh, save_config, save_grid,
       CircularRegion, PolygonRegion,
       generate_pts_file, create_regional_mesh_python,
       partition_mesh
   )

   # Step 1: Load shapefile
   states = gpd.read_file('BRA_adm1.shp')
   goias = states[states['NAME_1'] == 'Goiás']
   geom = goias.geometry.iloc[0].simplify(0.1)

   vertices = [(lat, lon) for lon, lat in
               geom.exterior.coords[:-1]]

   # Step 2: Define regions
   state = PolygonRegion(
       name='State',
       resolution=3.0,
       transition_width=2.0,
       vertices=vertices
   )

   metro = CircularRegion(
       name='Metro',
       resolution=1.0,
       transition_width=2.0,
       center=(-16.71, -49.24),
       radius=105.0
   )

   # Step 3: Generate mesh
   grid = generate_mesh(
       regions=[state, metro],
       background_resolution=30.0,
       output_path='output/goias',
       generate_jigsaw=True
   )

   # Step 4: Generate .pts file
   pts_file = generate_pts_file(
       output_path='output/goias.pts',
       name='goias',
       region_type='custom',
       inside_point=(-16.0, -49.5),
       polygon=[(v[0], v[1]) for v in vertices]
   )

   # Step 5: Cut regional mesh
   regional_grid, graph_file = create_regional_mesh_python(
       pts_file=pts_file,
       global_grid_file='x1.40962.grid.nc'
   )

   # Step 6: Partition for 64 MPI processes
   partition_file = partition_mesh(
       graph_file=graph_file,
       num_partitions=64
   )

   print(f"Regional grid: {regional_grid}")
   print(f"Partition: {partition_file}")

Example 7: Command-Line Pipeline
--------------------------------

Using the example script directly:

.. code-block:: bash

   # Quick test (no mesh generation)
   python examples/09_goias_shapefile_grid.py

   # Full pipeline with JIGSAW
   python examples/09_goias_shapefile_grid.py --jigsaw

   # Use existing global grid and partition
   python examples/09_goias_shapefile_grid.py \
       --global-grid x1.40962.grid.nc \
       --nprocs 64

Example 8: Extract Polygon from Shapefile
-----------------------------------------

Utility functions for shapefile processing:

.. code-block:: python

   import geopandas as gpd
   from shapely.geometry import Polygon
   from shapely.ops import transform
   import pyproj

   def load_state_polygon(shapefile, state_name, column='NAME_1'):
       """Load and simplify state polygon."""
       gdf = gpd.read_file(shapefile)
       filtered = gdf[gdf[column] == state_name]

       if len(filtered) == 0:
           raise ValueError(f"State not found: {state_name}")

       geom = filtered.geometry.iloc[0]
       simplified = geom.simplify(0.1, preserve_topology=True)

       return [(lat, lon) for lon, lat in
               simplified.exterior.coords[:-1]]

   def buffer_polygon(vertices, buffer_km):
       """Add buffer around polygon."""
       coords = [(lon, lat) for lat, lon in vertices]
       poly = Polygon(coords)

       wgs84 = pyproj.CRS('EPSG:4326')
       utm = pyproj.CRS('EPSG:32722')

       to_utm = pyproj.Transformer.from_crs(
           wgs84, utm, always_xy=True).transform
       to_wgs84 = pyproj.Transformer.from_crs(
           utm, wgs84, always_xy=True).transform

       poly_utm = transform(to_utm, poly)
       poly_buffered = poly_utm.buffer(buffer_km * 1000)
       poly_back = transform(to_wgs84, poly_buffered)

       simplified = poly_back.simplify(0.1, preserve_topology=True)
       return [(lat, lon) for lon, lat in
               simplified.exterior.coords[:-1]]

   def get_bounds(vertices):
       """Get bounding box."""
       lats = [v[0] for v in vertices]
       lons = [v[1] for v in vertices]
       return {
           'min_lat': min(lats),
           'max_lat': max(lats),
           'min_lon': min(lons),
           'max_lon': max(lons)
       }

   # Usage
   vertices = load_state_polygon('BRA_adm1.shp', 'Goiás')
   buffered = buffer_polygon(vertices, 50.0)
   bounds = get_bounds(vertices)

   print(f"Vertices: {len(vertices)}")
   print(f"Bounds: {bounds}")
