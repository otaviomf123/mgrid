Region Types
============

mgrid supports two types of refinement regions: circular and polygonal.

CircularRegion
--------------

A circular region is defined by a center point and radius.

Parameters
^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - name
     - str
     - Unique identifier for the region
   * - resolution
     - float
     - Target resolution inside the region (km)
   * - transition_width
     - float
     - Width of the transition zone (km)
   * - center
     - tuple
     - Center point as (latitude, longitude)
   * - radius
     - float
     - Radius of the circular region (km)

Example
^^^^^^^

.. code-block:: python

   from mgrid import CircularRegion

   # High-resolution region over São Paulo metropolitan area
   metro = CircularRegion(
       name='SaoPaulo_Metro',
       resolution=3.0,           # 3 km inside
       transition_width=15.0,    # 15 km transition
       center=(-23.55, -46.63),  # (lat, lon)
       radius=100.0              # 100 km radius
   )

The resolution transitions smoothly from ``resolution`` at the center
to ``resolution + transition_width`` at the edge.

PolygonRegion
-------------

A polygon region is defined by a list of vertices forming a closed boundary.

Parameters
^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - name
     - str
     - Unique identifier for the region
   * - resolution
     - float
     - Target resolution inside the region (km)
   * - transition_width
     - float
     - Width of the transition zone (km)
   * - vertices
     - list
     - List of (latitude, longitude) tuples

Example
^^^^^^^

.. code-block:: python

   from mgrid import PolygonRegion

   # State boundary
   goias = PolygonRegion(
       name='Goias_State',
       resolution=10.0,
       transition_width=20.0,
       vertices=[
           (-12.4, -50.2),
           (-13.3, -49.4),
           (-14.4, -45.9),
           (-19.5, -50.8),
           (-18.7, -52.4),
           # ... more vertices
       ]
   )

Extracting Vertices from Shapefiles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import geopandas as gpd

   # Load shapefile
   gdf = gpd.read_file('BRA_adm1.shp')

   # Filter by attribute
   state = gdf[gdf['NAME_1'] == 'Goiás']
   geometry = state.geometry.iloc[0]

   # Simplify to reduce vertices
   simplified = geometry.simplify(0.1, preserve_topology=True)

   # Extract as [lat, lon]
   vertices = []
   for lon, lat in simplified.exterior.coords[:-1]:
       vertices.append((lat, lon))

   # Create region
   region = PolygonRegion(
       name='Goias',
       resolution=5.0,
       transition_width=15.0,
       vertices=vertices
   )

Adding Buffer Around Polygon
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start the high-resolution zone before reaching the boundary:

.. code-block:: python

   from shapely.geometry import Polygon
   from shapely.ops import transform
   import pyproj

   def buffer_polygon(vertices, buffer_km):
       """Add buffer around polygon."""
       # Convert to (lon, lat) for shapely
       coords = [(lon, lat) for lat, lon in vertices]
       poly = Polygon(coords)

       # Transform to UTM for accurate buffering
       wgs84 = pyproj.CRS('EPSG:4326')
       utm = pyproj.CRS('EPSG:32722')  # UTM zone for Brazil

       to_utm = pyproj.Transformer.from_crs(
           wgs84, utm, always_xy=True
       ).transform
       to_wgs84 = pyproj.Transformer.from_crs(
           utm, wgs84, always_xy=True
       ).transform

       poly_utm = transform(to_utm, poly)
       poly_buffered = poly_utm.buffer(buffer_km * 1000)
       poly_back = transform(to_wgs84, poly_buffered)

       # Simplify
       poly_simple = poly_back.simplify(0.1, preserve_topology=True)

       # Return as [lat, lon]
       return [(lat, lon) for lon, lat in
               poly_simple.exterior.coords[:-1]]

   # Add 50 km buffer
   buffered = buffer_polygon(vertices, 50.0)

Nesting Regions
---------------

Multiple regions can be nested for hierarchical resolution:

.. code-block:: python

   from mgrid import generate_mesh, CircularRegion, PolygonRegion

   # Outer: regional buffer (5 km)
   regional = PolygonRegion(
       name='Regional',
       resolution=5.0,
       transition_width=25.0,
       vertices=regional_bounds
   )

   # Middle: state boundary (3 km)
   state = PolygonRegion(
       name='State',
       resolution=3.0,
       transition_width=2.0,
       vertices=state_vertices
   )

   # Inner: metropolitan area (1 km)
   metro = CircularRegion(
       name='Metro',
       resolution=1.0,
       transition_width=2.0,
       center=(-16.71, -49.24),
       radius=105.0
   )

   # Order doesn't matter - mgrid handles overlaps
   grid = generate_mesh(
       regions=[regional, state, metro],
       background_resolution=30.0
   )

The finest resolution takes precedence in overlapping areas.

Configuration File Format
-------------------------

Regions can be defined in JSON configuration files:

.. code-block:: json

   {
       "background_resolution": 30.0,
       "regions": [
           {
               "name": "Metro",
               "type": "circle",
               "center": [-16.71, -49.24],
               "radius": 105,
               "resolution": 1.0,
               "transition_start": 3.0
           },
           {
               "name": "State",
               "type": "polygon",
               "polygon": [
                   [-12.4, -50.2],
                   [-19.5, -50.8],
                   [-18.7, -52.4]
               ],
               "resolution": 3.0,
               "transition_start": 5.0
           }
       ]
   }

Note: In configuration files, use ``transition_start`` instead of
``transition_width``. The width is calculated as
``transition_start - resolution``.
