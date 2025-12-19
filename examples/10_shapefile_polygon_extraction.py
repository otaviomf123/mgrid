#!/usr/bin/env python
"""
Example 10: Extracting Polygon Boundaries from Shapefiles

This example demonstrates how to:
1. Load a shapefile using GeoPandas
2. Filter by attribute (e.g., state name)
3. Extract polygon coordinates
4. Simplify the polygon for computational efficiency
5. Calculate bounds and centroid
6. Export for use with mgrid

Author: MONAN Development Team
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform
import pyproj
from pathlib import Path


def load_shapefile(shapefile_path):
    """
    Load a shapefile and display basic information.

    Parameters
    ----------
    shapefile_path : str
        Path to the shapefile (.shp)

    Returns
    -------
    gdf : GeoDataFrame
        Loaded GeoDataFrame
    """
    gdf = gpd.read_file(shapefile_path)

    print(f"Loaded: {shapefile_path}")
    print(f"  Rows: {len(gdf)}")
    print(f"  Columns: {list(gdf.columns)}")
    print(f"  CRS: {gdf.crs}")
    print(f"  Geometry type: {gdf.geometry.geom_type.unique()}")

    return gdf


def list_available_regions(gdf, name_column):
    """
    List all available regions in the shapefile.

    Parameters
    ----------
    gdf : GeoDataFrame
        Loaded GeoDataFrame
    name_column : str
        Column containing region names
    """
    print(f"\nAvailable regions in '{name_column}':")
    for i, name in enumerate(sorted(gdf[name_column].unique())):
        print(f"  {i+1:3d}. {name}")


def extract_polygon(gdf, name_column, region_name):
    """
    Extract a specific region's polygon from a GeoDataFrame.

    Parameters
    ----------
    gdf : GeoDataFrame
        Loaded GeoDataFrame
    name_column : str
        Column containing region names
    region_name : str
        Name of the region to extract

    Returns
    -------
    geometry : Polygon or MultiPolygon
        The region's geometry
    """
    filtered = gdf[gdf[name_column] == region_name]

    if len(filtered) == 0:
        raise ValueError(f"Region '{region_name}' not found in column '{name_column}'")

    geometry = filtered.geometry.iloc[0]

    print(f"\nExtracted: {region_name}")
    print(f"  Geometry type: {geometry.geom_type}")
    print(f"  Area: {geometry.area:.6f} square degrees")

    return geometry


def get_polygon_bounds(geometry):
    """
    Get the bounding box of a polygon.

    Parameters
    ----------
    geometry : Polygon or MultiPolygon
        The geometry

    Returns
    -------
    bounds : dict
        Dictionary with min_lon, max_lon, min_lat, max_lat
    """
    minx, miny, maxx, maxy = geometry.bounds

    bounds = {
        'min_lon': minx,
        'max_lon': maxx,
        'min_lat': miny,
        'max_lat': maxy
    }

    print(f"\nBounds:")
    print(f"  Latitude:  [{bounds['min_lat']:.4f}, {bounds['max_lat']:.4f}]")
    print(f"  Longitude: [{bounds['min_lon']:.4f}, {bounds['max_lon']:.4f}]")

    return bounds


def get_polygon_centroid(geometry):
    """
    Get the centroid of a polygon.

    Parameters
    ----------
    geometry : Polygon or MultiPolygon
        The geometry

    Returns
    -------
    centroid : tuple
        (latitude, longitude) of centroid
    """
    centroid = geometry.centroid

    result = (centroid.y, centroid.x)  # (lat, lon)

    print(f"\nCentroid:")
    print(f"  Latitude:  {result[0]:.4f}")
    print(f"  Longitude: {result[1]:.4f}")

    return result


def extract_polygon_vertices(geometry, simplify_tolerance=None):
    """
    Extract vertices from a polygon geometry.

    Parameters
    ----------
    geometry : Polygon or MultiPolygon
        The geometry
    simplify_tolerance : float, optional
        Tolerance for simplification (in degrees). If None, no simplification.

    Returns
    -------
    vertices : list
        List of [lat, lon] coordinates
    """
    # Simplify if requested
    if simplify_tolerance is not None:
        original_count = count_vertices(geometry)
        geometry = geometry.simplify(simplify_tolerance, preserve_topology=True)
        simplified_count = count_vertices(geometry)
        print(f"\nSimplification:")
        print(f"  Tolerance: {simplify_tolerance} degrees")
        print(f"  Original vertices: {original_count}")
        print(f"  Simplified vertices: {simplified_count}")
        print(f"  Reduction: {100*(1-simplified_count/original_count):.1f}%")

    vertices = []

    if geometry.geom_type == 'Polygon':
        # Get exterior ring coordinates (skip last point which equals first)
        coords = list(geometry.exterior.coords)[:-1]
        for lon, lat in coords:
            vertices.append([lat, lon])

    elif geometry.geom_type == 'MultiPolygon':
        # Get the largest polygon
        largest = max(geometry.geoms, key=lambda p: p.area)
        coords = list(largest.exterior.coords)[:-1]
        for lon, lat in coords:
            vertices.append([lat, lon])
        print(f"  Note: MultiPolygon - using largest polygon only")

    print(f"\nExtracted vertices: {len(vertices)}")

    return vertices


def count_vertices(geometry):
    """Count total vertices in a geometry."""
    if geometry.geom_type == 'Polygon':
        return len(geometry.exterior.coords) - 1
    elif geometry.geom_type == 'MultiPolygon':
        return sum(len(p.exterior.coords) - 1 for p in geometry.geoms)
    return 0


def create_buffered_polygon(vertices, buffer_km):
    """
    Create a buffered version of the polygon.

    Parameters
    ----------
    vertices : list
        List of [lat, lon] coordinates
    buffer_km : float
        Buffer distance in kilometers

    Returns
    -------
    buffered_vertices : list
        List of [lat, lon] coordinates for buffered polygon
    """
    # Convert to [lon, lat] for shapely
    coords_lonlat = [(v[1], v[0]) for v in vertices]

    # Create polygon
    poly = Polygon(coords_lonlat)

    # Define projections (WGS84 to UTM)
    wgs84 = pyproj.CRS('EPSG:4326')

    # Determine appropriate UTM zone based on centroid
    centroid = poly.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = 'north' if centroid.y >= 0 else 'south'
    utm_crs = pyproj.CRS(f"+proj=utm +zone={utm_zone} +{hemisphere} +datum=WGS84")

    # Create transformers
    to_utm = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True).transform

    # Transform, buffer, transform back
    poly_utm = transform(to_utm, poly)
    poly_buffered = poly_utm.buffer(buffer_km * 1000)  # km to meters
    poly_back = transform(to_wgs84, poly_buffered)

    # Simplify to reduce vertices
    poly_simplified = poly_back.simplify(0.05, preserve_topology=True)

    # Extract coordinates
    buffered_vertices = []
    coords = list(poly_simplified.exterior.coords)[:-1]
    for lon, lat in coords:
        buffered_vertices.append([lat, lon])

    print(f"\nBuffer applied:")
    print(f"  Buffer distance: {buffer_km} km")
    print(f"  Original vertices: {len(vertices)}")
    print(f"  Buffered vertices: {len(buffered_vertices)}")

    return buffered_vertices


def export_to_python(vertices, variable_name="POLYGON"):
    """
    Export vertices as Python code for use in mgrid.

    Parameters
    ----------
    vertices : list
        List of [lat, lon] coordinates
    variable_name : str
        Name for the Python variable

    Returns
    -------
    code : str
        Python code string
    """
    lines = [f"{variable_name} = ["]
    for lat, lon in vertices:
        lines.append(f"    [{lat:.4f}, {lon:.4f}],")
    lines.append("]")

    return "\n".join(lines)


def export_to_pts(vertices, centroid, name, output_path):
    """
    Export as MPAS Limited-Area .pts file.

    Parameters
    ----------
    vertices : list
        List of [lat, lon] coordinates
    centroid : tuple
        (lat, lon) of centroid (inside point)
    name : str
        Region name
    output_path : str
        Path for output file
    """
    lines = [
        f"Name: {name}",
        "Type: custom",
        f"Point: {centroid[0]}, {centroid[1]}"
    ]

    for lat, lon in vertices:
        lines.append(f"{lat}, {lon}")

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"\nExported to: {output_path}")


# =============================================================================
# MAIN EXAMPLE
# =============================================================================

def main():
    """Main example demonstrating polygon extraction from shapefiles."""

    print("=" * 70)
    print("EXAMPLE: Extracting Polygon Boundaries from Shapefiles")
    print("=" * 70)

    # Path to shapefiles
    shapefile_dir = Path("examples/BRA_adm")

    # ==========================================================================
    # EXAMPLE 1: Extract a Brazilian State (Goiás)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 1: Extract Brazilian State (Goiás)")
    print("-" * 70)

    # Load states shapefile
    states_shp = shapefile_dir / "BRA_adm1.shp"
    states = load_shapefile(states_shp)

    # List available states
    list_available_regions(states, 'NAME_1')

    # Extract Goiás
    goias_geom = extract_polygon(states, 'NAME_1', 'Goiás')

    # Get bounds and centroid
    bounds = get_polygon_bounds(goias_geom)
    centroid = get_polygon_centroid(goias_geom)

    # Extract vertices (simplified)
    vertices = extract_polygon_vertices(goias_geom, simplify_tolerance=0.1)

    # Show first 5 vertices
    print("\nFirst 5 vertices [lat, lon]:")
    for v in vertices[:5]:
        print(f"  {v}")

    # Export as Python code
    print("\n" + "-" * 40)
    print("Python code for mgrid:")
    print("-" * 40)
    code = export_to_python(vertices[:10], "GOIAS_POLYGON")  # First 10 for display
    print(code)
    print("    # ... more vertices")

    # ==========================================================================
    # EXAMPLE 2: Extract with Buffer
    # ==========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 2: Add Buffer Around Polygon")
    print("-" * 70)

    # Create 50km buffer
    buffered = create_buffered_polygon(vertices, buffer_km=50.0)

    # ==========================================================================
    # EXAMPLE 3: Extract Municipalities
    # ==========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 3: Extract Municipalities (Cities)")
    print("-" * 70)

    # Load municipalities shapefile
    cities_shp = shapefile_dir / "BRA_adm3.shp"
    cities = load_shapefile(cities_shp)

    # Filter cities in Goiás
    goias_cities = cities[cities['NAME_1'] == 'Goiás']
    print(f"\nCities in Goiás: {len(goias_cities)}")

    # Extract Goiânia (note: shapefile uses 'Goiania' without accent)
    goiania_geom = extract_polygon(goias_cities, 'NAME_3', 'Goiania')
    goiania_bounds = get_polygon_bounds(goiania_geom)
    goiania_centroid = get_polygon_centroid(goiania_geom)

    # ==========================================================================
    # EXAMPLE 4: Multiple Municipalities (Metropolitan Area)
    # ==========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 4: Metropolitan Area (Multiple Municipalities)")
    print("-" * 70)

    # Define metropolitan area municipalities
    # Note: 'Goiania' in shapefile is without accent, others have accents
    metro_names = [
        'Goiania', 'Aparecida de Goiânia', 'Anápolis', 'Trindade',
        'Senador Canedo', 'Goianira', 'Nerópolis'
    ]

    # Filter and merge
    metro_cities = goias_cities[goias_cities['NAME_3'].isin(metro_names)]
    print(f"Found {len(metro_cities)} municipalities")

    # Dissolve into single geometry
    metro_merged = metro_cities.dissolve()
    metro_geom = metro_merged.geometry.iloc[0]

    # Get bounds of metropolitan area
    metro_bounds = get_polygon_bounds(metro_geom)
    metro_centroid = get_polygon_centroid(metro_geom)

    # Calculate recommended circle radius
    lat_range = metro_bounds['max_lat'] - metro_bounds['min_lat']
    lon_range = metro_bounds['max_lon'] - metro_bounds['min_lon']
    max_extent_deg = max(lat_range, lon_range)
    radius_km = max_extent_deg * 111 / 2 * 1.2  # 20% margin

    print(f"\nRecommended circle for mgrid:")
    print(f"  Center: ({metro_centroid[0]:.4f}, {metro_centroid[1]:.4f})")
    print(f"  Radius: {radius_km:.1f} km")

    # ==========================================================================
    # EXAMPLE 5: Export to .pts file
    # ==========================================================================
    print("\n" + "-" * 70)
    print("EXAMPLE 5: Export to MPAS Limited-Area .pts file")
    print("-" * 70)

    output_dir = Path("output/shapefile_example")
    output_dir.mkdir(parents=True, exist_ok=True)

    export_to_pts(
        vertices=vertices,
        centroid=centroid,
        name="goias_state",
        output_path=output_dir / "goias_state.pts"
    )

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY - Using Extracted Data with mgrid")
    print("=" * 70)
    print("""
To use the extracted polygon with mgrid:

1. For PolygonRegion:

   from mgrid import PolygonRegion

   region = PolygonRegion(
       name="Goias_State",
       resolution=3.0,
       transition_width=2.0,
       vertices=GOIAS_POLYGON  # Use extracted vertices
   )

2. For CircularRegion (metro area):

   from mgrid import CircularRegion

   region = CircularRegion(
       name="Goiania_Metro",
       resolution=1.0,
       transition_width=2.0,
       center=(-16.7128, -49.2418),  # Use extracted centroid
       radius=105.0  # Use calculated radius
   )

3. For MPAS Limited-Area cut:

   ./MPAS-Limited-Area/create_region output/shapefile_example/goias_state.pts \\
       /path/to/global/grid.nc
""")

    return {
        'goias_bounds': bounds,
        'goias_centroid': centroid,
        'goias_vertices': vertices,
        'buffered_vertices': buffered,
        'metro_bounds': metro_bounds,
        'metro_centroid': metro_centroid,
        'metro_radius_km': radius_km
    }


if __name__ == "__main__":
    results = main()
