#!/usr/bin/env python
"""
Example 09: Complete MPAS/MONAN Regional Mesh Pipeline

This example demonstrates the COMPLETE workflow from shapefile to
production-ready partitioned MPAS/MONAN mesh:

PIPELINE STEPS:
===============
1. SHAPEFILE → Configuration (extract polygon from shapefile)
2. Configuration → Cell Width Function (define resolution zones)
3. Cell Width → JIGSAW Mesh (generate spherical mesh)
4. JIGSAW Mesh → MPAS Format (convert to MPAS NetCDF)
5. Global Grid → Regional Cut (extract regional domain)
6. Regional Grid → Partition (partition for MPI parallel run)

Resolution Hierarchy:
=====================
1. GOIANIA METROPOLITAN AREA: 1 km
   - Covers all 18 municipalities of the metropolitan region
   - Radius: ~105 km to include entire metro area

2. GOIAS STATE (with buffer): 3 km
   - Uses simplified real polygon from GADM shapefile
   - BUFFERED by ~50 km so 3 km resolution starts BEFORE the state border

3. REGIONAL BUFFER: 5 km
   - Square region based on state bounds + margin

4. GLOBAL BACKGROUND: 30 km

Usage:
======
  # Step 1-3: Configuration + Cell width + Plots (quick, no mesh)
  python examples/09_goias_shapefile_grid.py

  # Step 1-4: Full mesh generation (requires JIGSAW)
  python examples/09_goias_shapefile_grid.py --jigsaw

  # Step 1-6: Complete pipeline with cut and partition
  python examples/09_goias_shapefile_grid.py --jigsaw --nprocs 64

  # Using existing global grid (skip JIGSAW)
  python examples/09_goias_shapefile_grid.py --global-grid x1.40962.grid.nc --nprocs 64

Author: MONAN Development Team

Data Source:
============
Shapefiles from DIVA-GIS (https://diva-gis.org/gdata)
- BRA_adm1.shp: State boundaries (Level 1)
- BRA_adm3.shp: Municipal boundaries (Level 3)
"""

import json
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import transform
import pyproj

from mgrid import (
    generate_mesh,
    save_grid,
    CircularRegion,
    PolygonRegion,
    save_config,
)

# ============================================================================
# GOIAS STATE POLYGON (simplified from shapefile, 65 vertices)
# Original: 3311 points, simplified with tolerance=0.1
# ============================================================================
GOIAS_POLYGON = [
    [-12.4124, -50.1582],
    [-12.8399, -50.2926],
    [-13.2746, -49.3694],
    [-12.7904, -49.1190],
    [-12.9572, -48.9756],
    [-12.8098, -48.8467],
    [-13.0629, -48.6015],
    [-13.3176, -48.5864],
    [-13.1288, -48.5087],
    [-13.2924, -48.4417],
    [-13.1520, -48.1466],
    [-13.3058, -48.1654],
    [-13.3119, -47.8239],
    [-13.4677, -47.6789],
    [-13.1045, -47.6347],
    [-13.2894, -47.4269],
    [-12.9712, -46.4546],
    [-12.8235, -46.4176],
    [-12.9912, -46.3638],
    [-12.9184, -46.1146],
    [-13.0983, -46.3226],
    [-13.3479, -46.2793],
    [-13.2727, -46.0421],
    [-13.4309, -46.2432],
    [-14.0980, -46.2657],
    [-14.3581, -45.9069],
    [-14.9364, -46.0881],
    [-14.7044, -46.5034],
    [-15.0526, -46.5030],
    [-15.0546, -46.9226],
    [-15.8849, -46.8112],
    [-16.0367, -47.3191],
    [-15.5003, -47.4173],
    [-15.5002, -48.2005],
    [-16.0516, -48.2791],
    [-16.0560, -47.3058],
    [-16.5040, -47.4589],
    [-17.0104, -47.1317],
    [-17.4543, -47.5411],
    [-17.6091, -47.2668],
    [-18.0582, -47.2832],
    [-18.5003, -47.9549],
    [-18.3319, -48.2624],
    [-18.3062, -48.9367],
    [-18.5372, -49.0048],
    [-18.6463, -49.3947],
    [-18.4936, -49.5358],
    [-18.6919, -50.2946],
    [-19.4991, -50.8421],
    [-18.6910, -52.4491],
    [-18.6392, -52.9166],
    [-18.3492, -52.7594],
    [-18.3108, -53.1011],
    [-17.5267, -53.2463],
    [-16.8580, -53.0113],
    [-16.5334, -52.6261],
    [-16.2941, -52.6736],
    [-15.8927, -52.2526],
    [-15.8254, -51.8795],
    [-15.0697, -51.5359],
    [-14.9164, -51.0840],
    [-14.0899, -50.8336],
    [-13.7331, -50.8717],
    [-12.7100, -50.4780],
    [-12.4124, -50.1582],
]

# ============================================================================
# GOIANIA METROPOLITAN AREA DATA (from shapefile analysis)
# ============================================================================
METRO_DATA = {
    'center': (-16.7128, -49.2418),  # Centroid of 18 municipalities
    'bounds': {
        'min_lon': -49.7493,
        'max_lon': -48.6382,
        'min_lat': -17.1942,
        'max_lat': -16.1509
    },
    'recommended_radius': 105.0,  # km (with safety margin)
    'municipalities': [
        'Goiânia', 'Aparecida de Goiânia', 'Anápolis', 'Trindade',
        'Senador Canedo', 'Goianira', 'Nerópolis', 'Abadia de Goiás',
        'Aragoiânia', 'Hidrolândia', 'Bela Vista de Goiás', 'Guapó',
        'Bonfinópolis', 'Caldazinha', 'Caturaí', 'Inhumas',
        'Nova Veneza', 'Santo Antônio de Goiás', 'Terezópolis de Goiás'
    ]
}

# ============================================================================
# GOIAS STATE DATA (from shapefile analysis)
# ============================================================================
STATE_DATA = {
    'centroid': (-16.0444, -49.6233),
    'bounds': {
        'min_lon': -53.2511,
        'max_lon': -45.9069,
        'min_lat': -19.4991,
        'max_lat': -12.3959
    }
}

# Buffer distance in km - resolution transitions from 5km to 3km over this distance
# This ensures 3km resolution is reached BEFORE the state border
STATE_BUFFER_KM = 50.0


def create_buffered_polygon(polygon_coords, buffer_km):
    """
    Create a buffered version of the polygon.

    The buffer is applied in metric space (UTM) for accuracy,
    then converted back to lat/lon coordinates.

    Parameters
    ----------
    polygon_coords : list
        List of [lat, lon] coordinates
    buffer_km : float
        Buffer distance in kilometers

    Returns
    -------
    list
        Buffered polygon coordinates as [lat, lon] pairs
    """
    # Convert to [lon, lat] for shapely (it expects x, y order)
    coords_lonlat = [(lon, lat) for lat, lon in polygon_coords]

    # Create shapely polygon
    poly = Polygon(coords_lonlat)

    # Define projections
    # WGS84 (lat/lon)
    wgs84 = pyproj.CRS('EPSG:4326')
    # UTM zone 22S (appropriate for central Brazil/Goiás)
    utm = pyproj.CRS('EPSG:32722')

    # Create transformers
    to_utm = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    to_wgs84 = pyproj.Transformer.from_crs(utm, wgs84, always_xy=True).transform

    # Transform to UTM, apply buffer, transform back
    poly_utm = transform(to_utm, poly)
    poly_buffered_utm = poly_utm.buffer(buffer_km * 1000)  # Convert km to meters
    poly_buffered = transform(to_wgs84, poly_buffered_utm)

    # Simplify to reduce vertex count
    poly_simplified = poly_buffered.simplify(0.1, preserve_topology=True)

    # Extract coordinates and convert back to [lat, lon] format
    buffered_coords = []
    if poly_simplified.geom_type == 'Polygon':
        for lon, lat in poly_simplified.exterior.coords[:-1]:  # Skip closing point
            buffered_coords.append([lat, lon])

    return buffered_coords


def create_goias_config():
    """
    Create configuration using real shapefile data.

    The state polygon is BUFFERED outward so that the 3 km resolution zone
    starts before reaching the actual state border. This ensures the border
    itself is already at 3 km resolution.

    Returns
    -------
    config : dict
        Configuration dictionary with precise region definitions.
    """
    # Create buffered polygon for the 3 km zone
    # This extends the state boundary outward so 3 km resolution starts earlier
    print(f"  Creating {STATE_BUFFER_KM} km buffer around state polygon...")
    buffered_polygon = create_buffered_polygon(GOIAS_POLYGON, STATE_BUFFER_KM)
    print(f"  Buffered polygon: {len(buffered_polygon)} vertices")

    # Calculate regional buffer bounds (state bounds + 1.5 degree margin for buffered poly)
    margin = 1.5
    regional_bounds = {
        'min_lat': STATE_DATA['bounds']['min_lat'] - margin,
        'max_lat': STATE_DATA['bounds']['max_lat'] + margin,
        'min_lon': STATE_DATA['bounds']['min_lon'] - margin,
        'max_lon': STATE_DATA['bounds']['max_lon'] + margin
    }

    config = {
        "description": "Multi-resolution grid for Goias using real shapefile boundaries (with buffer)",
        "author": "MONAN Development Team",
        "data_source": "GADM Brazil Administrative Boundaries (BRA_adm1.shp, BRA_adm3.shp)",
        "background_resolution": 30.0,
        "grid_density": 0.5,  # Use 0.05 for production
        "state_buffer_km": STATE_BUFFER_KM,
        "regions": [
            {
                "name": "Regional_Buffer",
                "type": "polygon",
                "description": "5 km buffer zone around Goias state (state bounds + 1.5 degree)",
                "polygon": [
                    [regional_bounds['max_lat'], regional_bounds['min_lon']],  # NW
                    [regional_bounds['max_lat'], regional_bounds['max_lon']],  # NE
                    [regional_bounds['min_lat'], regional_bounds['max_lon']],  # SE
                    [regional_bounds['min_lat'], regional_bounds['min_lon']],  # SW
                ],
                "resolution": 5.0,
                "transition_start": 30.0
            },
            {
                "name": "Goias_State_Buffered",
                "type": "polygon",
                "description": f"3 km resolution with {STATE_BUFFER_KM} km buffer outside state border",
                "polygon": buffered_polygon,
                "resolution": 3.0,
                "transition_start": 5.0
            },
            {
                "name": "Goiania_Metropolitan",
                "type": "circle",
                "description": f"1 km resolution covering {len(METRO_DATA['municipalities'])} municipalities",
                "center": list(METRO_DATA['center']),
                "radius": METRO_DATA['recommended_radius'],
                "resolution": 1.0,
                "transition_start": 3.0
            }
        ],
        "metadata": {
            "goias_state": {
                "original_vertices": 3311,
                "simplified_vertices": 65,
                "buffered_vertices": len(buffered_polygon),
                "buffer_km": STATE_BUFFER_KM,
                "simplification_tolerance": 0.1,
                "centroid": list(STATE_DATA['centroid']),
                "bounds": STATE_DATA['bounds']
            },
            "metropolitan_area": {
                "center": list(METRO_DATA['center']),
                "radius_km": METRO_DATA['recommended_radius'],
                "municipalities": METRO_DATA['municipalities'],
                "bounds": METRO_DATA['bounds']
            }
        },
        "notes": [
            "Goias polygon simplified from 3311 to 65 vertices for efficiency",
            f"State polygon buffered outward by {STATE_BUFFER_KM} km",
            "Buffer ensures 3 km resolution is reached BEFORE the state border",
            "Metropolitan area covers all 19 official municipalities",
            "Metro radius (105 km) ensures complete coverage with margin",
            "Regional buffer extends 1.5 degrees beyond state boundaries",
            "Use grid_density=0.05 for production quality meshes"
        ]
    }

    return config, buffered_polygon


def create_regions_from_config(config):
    """Create Region objects from configuration."""
    regions = []

    for region_config in config["regions"]:
        name = region_config["name"]
        resolution = region_config["resolution"]
        transition_start = region_config["transition_start"]
        transition_width = transition_start - resolution

        if region_config["type"] == "circle":
            region = CircularRegion(
                name=name,
                resolution=resolution,
                transition_width=transition_width,
                center=tuple(region_config["center"]),
                radius=region_config["radius"]
            )
        elif region_config["type"] == "polygon":
            region = PolygonRegion(
                name=name,
                resolution=resolution,
                transition_width=transition_width,
                vertices=[tuple(v) for v in region_config["polygon"]]
            )

        regions.append(region)

    return regions


def plot_with_basemap_and_shapefile(grid, config, output_dir, buffered_polygon):
    """
    Create plots using Basemap with actual shapefile overlay.

    Shows both the original state boundary and the buffered 3km zone.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from mpl_toolkits.basemap import Basemap
    import geopandas as gpd

    # Load shapefiles
    states = gpd.read_file('examples/BRA_adm/BRA_adm1.shp')
    cities = gpd.read_file('examples/BRA_adm/BRA_adm3.shp')
    goias_state = states[states['NAME_1'] == 'Goiás']
    goias_cities = cities[cities['NAME_1'] == 'Goiás']

    # Get metropolitan municipalities
    metro_names = METRO_DATA['municipalities']
    metro_cities = goias_cities[goias_cities['NAME_3'].isin(metro_names)]

    # Create meshgrid for plotting
    lons, lats = np.meshgrid(grid.lon, grid.lat)

    # =========================================================================
    # PLOT 1: Regional View with Real Shapefile Boundaries
    # =========================================================================
    fig, ax = plt.subplots(figsize=(14, 12))

    m = Basemap(
        projection='merc',
        llcrnrlat=-22, urcrnrlat=-10,
        llcrnrlon=-56, urcrnrlon=-43,
        resolution='i', ax=ax
    )

    # Draw base map
    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    m.drawstates(linewidth=0.5, color='gray')
    m.drawparallels(np.arange(-22, -9, 2), labels=[1, 0, 0, 0], fontsize=10)
    m.drawmeridians(np.arange(-56, -42, 2), labels=[0, 0, 0, 1], fontsize=10)

    # Plot cell width
    x, y = m(lons, lats)
    levels = np.linspace(1, 30, 30)
    cs = m.contourf(x, y, grid.cell_width, levels=levels, cmap='jet', extend='both')
    cbar = m.colorbar(cs, location='right', pad='5%')
    cbar.set_label('Cell Width (km)', fontsize=12)

    # Plot BUFFERED polygon (3 km zone boundary) - yellow dashed
    buff_lons = [p[1] for p in buffered_polygon] + [buffered_polygon[0][1]]
    buff_lats = [p[0] for p in buffered_polygon] + [buffered_polygon[0][0]]
    bx, by = m(buff_lons, buff_lats)
    m.plot(bx, by, 'w-', linewidth=3)
    m.plot(bx, by, 'y--', linewidth=2, label=f'3 km zone ({STATE_BUFFER_KM:.0f} km buffer)')

    # Plot REAL Goias state boundary from shapefile - solid red
    for geom in goias_state.geometry:
        if geom.geom_type == 'Polygon':
            coords = np.array(geom.exterior.coords)
            px, py = m(coords[:, 0], coords[:, 1])
            m.plot(px, py, 'w-', linewidth=3)
            m.plot(px, py, 'r-', linewidth=2, label='Goiás State (real border)')
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                coords = np.array(poly.exterior.coords)
                px, py = m(coords[:, 0], coords[:, 1])
                m.plot(px, py, 'w-', linewidth=3)
                m.plot(px, py, 'r-', linewidth=2)

    # Plot metropolitan area municipalities
    for geom in metro_cities.geometry:
        if geom.geom_type == 'Polygon':
            coords = np.array(geom.exterior.coords)
            px, py = m(coords[:, 0], coords[:, 1])
            m.plot(px, py, 'm-', linewidth=1.5, alpha=0.7)
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                coords = np.array(poly.exterior.coords)
                px, py = m(coords[:, 0], coords[:, 1])
                m.plot(px, py, 'm-', linewidth=1.5, alpha=0.7)

    # Draw metro circle
    theta = np.linspace(0, 2 * np.pi, 100)
    metro_center = METRO_DATA['center']
    metro_radius_deg = METRO_DATA['recommended_radius'] / 111.0
    metro_lons = metro_center[1] + metro_radius_deg * np.cos(theta)
    metro_lats = metro_center[0] + metro_radius_deg * np.sin(theta)
    mx, my = m(metro_lons, metro_lats)
    m.plot(mx, my, 'w-', linewidth=2.5)
    m.plot(mx, my, 'c-', linewidth=2, label='Metro Area (1 km zone)')

    # Regional buffer
    regional_poly = config["regions"][0]["polygon"]
    poly_lons = [p[1] for p in regional_poly] + [regional_poly[0][1]]
    poly_lats = [p[0] for p in regional_poly] + [regional_poly[0][0]]
    rpx, rpy = m(poly_lons, poly_lats)
    m.plot(rpx, rpy, 'w-', linewidth=2)
    m.plot(rpx, rpy, 'k--', linewidth=1.5, label='Regional Buffer (5 km)')

    # Mark cities
    cities_to_mark = {
        'Goiânia': (-16.68, -49.25),
        'Brasília': (-15.79, -47.88),
        'Anápolis': (-16.33, -48.95),
        'Rio Verde': (-17.80, -50.92),
        'Itumbiara': (-18.42, -49.22),
    }
    for city, (lat, lon) in cities_to_mark.items():
        cx, cy = m(lon, lat)
        m.plot(cx, cy, 'r*', markersize=12, markeredgecolor='white', markeredgewidth=0.5)
        ax.text(cx, cy + 25000, city, fontsize=9, ha='center', fontweight='bold',
                color='white', path_effects=[pe.withStroke(linewidth=2, foreground='black')])

    ax.set_title(f'Goiás Grid with {STATE_BUFFER_KM:.0f} km Buffer\n'
                 f'3 km zone starts BEFORE state border (yellow dashed)',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'goias_shapefile_regional.png', dpi=150, bbox_inches='tight')
    print(f"       Saved: {output_dir / 'goias_shapefile_regional.png'}")
    plt.close()

    # =========================================================================
    # PLOT 2: Metropolitan Area Zoom with Municipality Boundaries
    # =========================================================================
    fig, ax = plt.subplots(figsize=(14, 12))

    # Metro area bounds with margin
    metro_bounds = METRO_DATA['bounds']
    margin = 0.5
    m2 = Basemap(
        projection='merc',
        llcrnrlat=metro_bounds['min_lat'] - margin,
        urcrnrlat=metro_bounds['max_lat'] + margin,
        llcrnrlon=metro_bounds['min_lon'] - margin,
        urcrnrlon=metro_bounds['max_lon'] + margin,
        resolution='h', ax=ax
    )

    m2.drawstates(linewidth=0.5, color='gray')
    m2.drawparallels(np.arange(-18, -15, 0.5), labels=[1, 0, 0, 0], fontsize=10)
    m2.drawmeridians(np.arange(-51, -47, 0.5), labels=[0, 0, 0, 1], fontsize=10)

    # Plot cell width
    x2, y2 = m2(lons, lats)
    levels2 = np.linspace(1, 5, 20)
    cs2 = m2.contourf(x2, y2, grid.cell_width, levels=levels2, cmap='jet', extend='both')
    cbar2 = m2.colorbar(cs2, location='right', pad='5%')
    cbar2.set_label('Cell Width (km)', fontsize=12)

    # Plot ALL metropolitan municipalities with labels
    for idx, row in metro_cities.iterrows():
        geom = row.geometry
        name = row['NAME_3']

        if geom.geom_type == 'Polygon':
            coords = np.array(geom.exterior.coords)
            px, py = m2(coords[:, 0], coords[:, 1])
            m2.plot(px, py, 'w-', linewidth=2)
            m2.plot(px, py, 'm-', linewidth=1.5)

            # Label municipality
            cx, cy = m2(geom.centroid.x, geom.centroid.y)
            ax.text(cx, cy, name, fontsize=7, ha='center', va='center',
                    color='white', fontweight='bold',
                    path_effects=[pe.withStroke(linewidth=1.5, foreground='black')])

    # Draw metro circle
    mx2, my2 = m2(metro_lons, metro_lats)
    m2.plot(mx2, my2, 'c-', linewidth=3, label=f'Metro Circle ({METRO_DATA["recommended_radius"]:.0f} km)')

    # Mark metro centroid
    mcx, mcy = m2(METRO_DATA['center'][1], METRO_DATA['center'][0])
    m2.plot(mcx, mcy, 'c*', markersize=20, markeredgecolor='white', markeredgewidth=1)

    ax.set_title(f'Goiânia Metropolitan Area - {len(METRO_DATA["municipalities"])} Municipalities\n'
                 f'Resolution: 1 km | Radius: {METRO_DATA["recommended_radius"]:.0f} km',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'goias_metro_municipalities.png', dpi=150, bbox_inches='tight')
    print(f"       Saved: {output_dir / 'goias_metro_municipalities.png'}")
    plt.close()

    # =========================================================================
    # PLOT 3: Resolution Histogram
    # =========================================================================
    fig, ax = plt.subplots(figsize=(10, 6))

    hist_data = grid.cell_width.flatten()
    bins = np.linspace(0, 32, 65)

    ax.hist(hist_data, bins=bins, edgecolor='black', alpha=0.7, color='steelblue')
    ax.set_xlabel('Cell Width (km)', fontsize=12)
    ax.set_ylabel('Frequency (log scale)', fontsize=12)
    ax.set_yscale('log')
    ax.set_title('Grid Resolution Distribution', fontsize=14, fontweight='bold')

    ax.axvline(x=1, color='red', linestyle='--', linewidth=2, label='Metro (1 km)')
    ax.axvline(x=3, color='orange', linestyle='--', linewidth=2, label='Goiás (3 km)')
    ax.axvline(x=5, color='green', linestyle='--', linewidth=2, label='Regional (5 km)')
    ax.axvline(x=30, color='purple', linestyle='--', linewidth=2, label='Global (30 km)')

    stats_text = (
        f"Statistics:\n"
        f"Min: {np.min(hist_data):.1f} km\n"
        f"Max: {np.max(hist_data):.1f} km\n"
        f"Mean: {np.mean(hist_data):.1f} km\n"
        f"Grid points: {len(hist_data):,}"
    )
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax.legend(loc='upper center', fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'goias_resolution_histogram.png', dpi=150, bbox_inches='tight')
    print(f"       Saved: {output_dir / 'goias_resolution_histogram.png'}")
    plt.close()


def print_grid_info(config):
    """Print detailed grid configuration information."""
    print("=" * 70)
    print("GOIAS GRID CONFIGURATION (from Shapefile)")
    print("=" * 70)

    print(f"\nData Source: {config['data_source']}")
    print(f"Background Resolution: {config['background_resolution']} km")

    print("\n" + "-" * 70)
    print("STATE DATA (from BRA_adm1.shp):")
    print("-" * 70)
    meta = config['metadata']['goias_state']
    print(f"  Original vertices: {meta['original_vertices']}")
    print(f"  Simplified vertices: {meta['simplified_vertices']}")
    print(f"  Buffer distance: {meta.get('buffer_km', 0)} km")
    print(f"  Buffered vertices: {meta.get('buffered_vertices', 'N/A')}")
    print(f"  Centroid: {meta['centroid']}")
    print(f"  Bounds: Lat [{meta['bounds']['min_lat']:.2f}, {meta['bounds']['max_lat']:.2f}]")
    print(f"          Lon [{meta['bounds']['min_lon']:.2f}, {meta['bounds']['max_lon']:.2f}]")
    print(f"\n  NOTE: 3 km zone extends {meta.get('buffer_km', 0)} km OUTSIDE state border")

    print("\n" + "-" * 70)
    print("METROPOLITAN AREA (from BRA_adm3.shp):")
    print("-" * 70)
    meta = config['metadata']['metropolitan_area']
    print(f"  Center: {meta['center']}")
    print(f"  Radius: {meta['radius_km']} km")
    print(f"  Municipalities ({len(meta['municipalities'])}):")
    for i, name in enumerate(meta['municipalities'], 1):
        print(f"    {i:2d}. {name}")

    print("\n" + "-" * 70)
    print("RESOLUTION HIERARCHY:")
    print("-" * 70)
    sorted_regions = sorted(config["regions"], key=lambda x: x["resolution"])
    for i, region in enumerate(sorted_regions, 1):
        print(f"\n  {i}. {region['name']}")
        print(f"     Resolution: {region['resolution']} km -> {region['transition_start']} km")
        print(f"     Type: {region['type']}")
        if region['type'] == 'polygon':
            print(f"     Vertices: {len(region['polygon'])}")

    print("\n" + "=" * 70)


def main(run_jigsaw=False, global_grid_file=None, num_partitions=None):
    """
    Main function - Complete MPAS/MONAN regional mesh pipeline.

    This function runs the complete workflow:
    1. Create configuration from shapefile
    2. Compute cell width function
    3. Generate visualization plots
    4. Generate JIGSAW mesh (optional)
    5. Convert to MPAS format (optional)
    6. Generate .pts specification files
    7. Cut regional mesh (if global grid available)
    8. Partition for MPI (if num_partitions specified)

    Parameters
    ----------
    run_jigsaw : bool
        If True, run JIGSAW to generate the mesh and convert to MPAS format.
    global_grid_file : str or Path, optional
        Path to existing global MPAS grid. If provided, skips JIGSAW and uses
        this grid for the regional cut.
    num_partitions : int, optional
        Number of MPI partitions. If provided, partitions the regional mesh
        using METIS (gpmetis).

    Returns
    -------
    dict
        Dictionary with paths to all generated files.
    """
    output_dir = Path("output/goias_shapefile")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    # Determine the grid file to use for cutting
    mpas_grid = None
    if global_grid_file:
        mpas_grid = Path(global_grid_file)
        if not mpas_grid.exists():
            raise FileNotFoundError(f"Global grid file not found: {mpas_grid}")

    # =========================================================================
    # STEP 1: Create configuration from shapefile data
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: CREATE CONFIGURATION FROM SHAPEFILE DATA")
    print("=" * 70)
    config, buffered_polygon = create_goias_config()
    print_grid_info(config)

    config_file = output_dir / "goias_shapefile_config.json"
    save_config(config, config_file)
    print(f"\nConfiguration saved to: {config_file}")

    results['config'] = config
    results['config_file'] = str(config_file)
    results['buffered_polygon'] = buffered_polygon

    # =========================================================================
    # STEP 2: Compute cell width function
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: COMPUTE CELL WIDTH FUNCTION")
    print("=" * 70)
    grid = generate_mesh(
        config=config,
        output_path=str(output_dir / "goias_mesh"),
        generate_jigsaw=run_jigsaw,
        plot=False
    )
    print("\n" + grid.summary())
    results['grid'] = grid

    # =========================================================================
    # STEP 3: Generate visualization plots
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: GENERATE VISUALIZATION PLOTS")
    print("=" * 70)
    try:
        plot_with_basemap_and_shapefile(grid, config, output_dir, buffered_polygon)
    except Exception as e:
        print(f"  Warning: Could not generate plots - {e}")

    # =========================================================================
    # STEP 4: Convert to MPAS format (if JIGSAW was run)
    # =========================================================================
    if run_jigsaw and grid.mesh_file:
        print("\n" + "=" * 70)
        print("STEP 4: CONVERT TO MPAS FORMAT")
        print("=" * 70)
        try:
            from mgrid.io import convert_to_mpas

            mpas_file = output_dir / "goias.grid.nc"
            convert_to_mpas(
                mesh_file=grid.mesh_file,
                output_file=mpas_file
            )
            mpas_grid = mpas_file
            results['mpas_file'] = str(mpas_file)
            print(f"\nMPAS grid file: {mpas_file}")
        except ImportError as e:
            print(f"  Warning: mpas_tools not available - {e}")
            print("  Install with: conda install -c conda-forge mpas_tools")
        except Exception as e:
            print(f"  Warning: Conversion failed - {e}")

    # =========================================================================
    # STEP 5: Generate MPAS Limited-Area specification files
    # =========================================================================
    print("\n" + "=" * 70)
    print("STEP 5: GENERATE MPAS LIMITED-AREA SPECIFICATION FILES")
    print("=" * 70)
    try:
        pts_state, pts_metro, pts_regional = generate_limited_area_pts(
            config, buffered_polygon, output_dir
        )
        results['pts_state'] = str(pts_state)
        results['pts_metro'] = str(pts_metro)
        results['pts_regional'] = str(pts_regional)

        print("\n  Generated .pts files:")
        print(f"    - goias_region.pts    : State polygon ({len(buffered_polygon)} vertices)")
        print(f"    - goiania_metro.pts   : Metro circle (r={METRO_DATA['recommended_radius']} km)")
        print(f"    - goias_regional.pts  : Regional buffer (square)")
    except Exception as e:
        print(f"  Warning: Could not generate .pts files - {e}")
        pts_regional = None

    # =========================================================================
    # STEP 6: Cut regional mesh (if global grid available)
    # =========================================================================
    if mpas_grid and pts_regional:
        print("\n" + "=" * 70)
        print("STEP 6: CUT REGIONAL MESH FROM GLOBAL GRID")
        print("=" * 70)
        try:
            regional_grid, graph_file = create_regional_grid(
                pts_file=pts_regional,
                global_grid_file=mpas_grid,
                output_dir=output_dir
            )
            results['regional_grid'] = regional_grid
            results['graph_file'] = graph_file
            print(f"\n  Regional grid: {regional_grid}")
            print(f"  Graph file: {graph_file}")
        except Exception as e:
            print(f"  Warning: Regional mesh creation failed - {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # STEP 7: Partition for MPI (if num_partitions specified)
    # =========================================================================
    if num_partitions and 'graph_file' in results:
        print("\n" + "=" * 70)
        print(f"STEP 7: PARTITION MESH FOR {num_partitions} MPI PROCESSES")
        print("=" * 70)
        try:
            from mgrid.limited_area import partition_mesh

            partition_file = partition_mesh(
                graph_file=results['graph_file'],
                num_partitions=num_partitions,
            )
            results['partition_file'] = str(partition_file)
            print(f"\n  Partition file: {partition_file}")
        except Exception as e:
            print(f"  Warning: Partitioning failed - {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_summary(results, output_dir, run_jigsaw, num_partitions)

    return results


def print_summary(results, output_dir, run_jigsaw, num_partitions):
    """Print final summary of all generated files."""
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE - OUTPUT FILES")
    print("=" * 70)
    print(f"\nDirectory: {output_dir.absolute()}")

    print("\n" + "-" * 40)
    print("Configuration & Visualization:")
    print("-" * 40)
    print(f"  goias_shapefile_config.json")
    print(f"  goias_shapefile_regional.png")
    print(f"  goias_metro_municipalities.png")
    print(f"  goias_resolution_histogram.png")

    print("\n" + "-" * 40)
    print("MPAS Limited-Area Specifications:")
    print("-" * 40)
    print(f"  goias_region.pts     (state polygon)")
    print(f"  goiania_metro.pts    (metro circle)")
    print(f"  goias_regional.pts   (regional buffer)")

    if run_jigsaw:
        print("\n" + "-" * 40)
        print("JIGSAW Mesh:")
        print("-" * 40)
        print(f"  goias_mesh-MESH.msh")
        print(f"  goias_mesh-HFUN.msh")
        if 'mpas_file' in results:
            print(f"  goias.grid.nc  (MPAS format)")

    if 'regional_grid' in results:
        print("\n" + "-" * 40)
        print("Regional MPAS Grid:")
        print("-" * 40)
        print(f"  {Path(results['regional_grid']).name}")
        print(f"  {Path(results['graph_file']).name}")

        if 'partition_file' in results:
            print(f"  {Path(results['partition_file']).name}")

    # Print usage instructions
    if 'partition_file' in results:
        print("\n" + "=" * 70)
        print("READY FOR MPAS/MONAN EXECUTION")
        print("=" * 70)
        print(f"\nTo run MPAS/MONAN with {num_partitions} MPI processes:")
        print(f"  1. Copy regional grid to your run directory:")
        print(f"     cp {results['regional_grid']} ./")
        print(f"     cp {results['partition_file']} ./")
        print(f"\n  2. Run the model:")
        print(f"     mpirun -np {num_partitions} ./atmosphere_model")

    grid = results.get('grid')
    if grid:
        print("\n" + "-" * 40)
        print("Grid Statistics:")
        print("-" * 40)
        print(f"  Min resolution: {grid.min_resolution:.1f} km")
        print(f"  Max resolution: {grid.max_resolution:.1f} km")
        print(f"  State polygon:  {len(GOIAS_POLYGON)} vertices")
        print(f"  State buffer:   {STATE_BUFFER_KM} km")
        print(f"  Metro area:     {len(METRO_DATA['municipalities'])} municipalities")

    print("\n" + "=" * 70 + "\n")


def generate_limited_area_pts(config, buffered_polygon, output_dir):
    """
    Generate MPAS Limited-Area points specification file (.pts).

    This creates a .pts file that can be used with the MPAS Limited-Area tool
    to cut a regional mesh from a global MPAS grid.

    The region is defined using the buffered state polygon to ensure
    the 3 km resolution zone is fully included.
    """
    from mgrid.limited_area import generate_pts_file

    output_dir = Path(output_dir)

    # Use the buffered polygon (which includes the 50km buffer)
    # This ensures the entire 3km resolution zone is included in the regional cut
    polygon_tuples = [(p[0], p[1]) for p in buffered_polygon]

    # Calculate centroid as the inside point
    lats = [p[0] for p in buffered_polygon]
    lons = [p[1] for p in buffered_polygon]
    centroid = (sum(lats) / len(lats), sum(lons) / len(lons))

    # Generate custom (polygon) .pts file for the state region
    pts_file = generate_pts_file(
        output_path=output_dir / "goias_region.pts",
        name="goias",
        region_type="custom",
        inside_point=centroid,
        polygon=polygon_tuples,
    )
    print(f"  Generated: {pts_file}")

    # Also generate a circle .pts for the metropolitan area (alternative)
    metro_pts = generate_pts_file(
        output_path=output_dir / "goiania_metro.pts",
        name="goiania_metro",
        region_type="circle",
        inside_point=METRO_DATA['center'],
        radius=METRO_DATA['recommended_radius'] * 1000,  # Convert km to meters
    )
    print(f"  Generated: {metro_pts}")

    # Generate regional buffer (square) .pts file
    regional_poly = config["regions"][0]["polygon"]
    regional_tuples = [(p[0], p[1]) for p in regional_poly]
    regional_centroid = (
        sum(p[0] for p in regional_poly) / len(regional_poly),
        sum(p[1] for p in regional_poly) / len(regional_poly)
    )

    regional_pts = generate_pts_file(
        output_path=output_dir / "goias_regional.pts",
        name="goias_regional",
        region_type="custom",
        inside_point=regional_centroid,
        polygon=regional_tuples,
    )
    print(f"  Generated: {regional_pts}")

    return pts_file, metro_pts, regional_pts


def create_regional_grid(pts_file, global_grid_file, output_dir):
    """
    Create a regional MPAS grid using the Limited-Area tool.

    Parameters
    ----------
    pts_file : str or Path
        Path to the .pts file defining the region.
    global_grid_file : str or Path
        Path to a global MPAS grid file (grid.nc or static.nc).
    output_dir : Path
        Output directory.

    Returns
    -------
    tuple
        (regional_grid_file, graph_file) paths.
    """
    from mgrid.limited_area import create_regional_mesh_python

    print(f"\n  Points file: {pts_file}")
    print(f"  Global grid: {global_grid_file}")

    regional_grid, graph_file = create_regional_mesh_python(
        pts_file=pts_file,
        global_grid_file=global_grid_file,
        verbose=1,
    )

    print(f"  Regional grid created: {regional_grid}")
    print(f"  Graph file created: {graph_file}")

    return regional_grid, graph_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Complete MPAS/MONAN Regional Mesh Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PIPELINE STEPS:
===============
1. Shapefile → Configuration (extract polygon from shapefile)
2. Configuration → Cell Width Function (define resolution zones)
3. Cell Width → Visualization Plots
4. Cell Width → JIGSAW Mesh (--jigsaw)
5. JIGSAW → MPAS Format (--jigsaw)
6. Global Grid → Regional Cut (--global-grid or --jigsaw)
7. Regional Grid → Partition (--nprocs N)

Examples:
---------
  # Quick: Configuration + Cell width + Plots only
  python examples/09_goias_shapefile_grid.py

  # Full: JIGSAW mesh + MPAS conversion
  python examples/09_goias_shapefile_grid.py --jigsaw

  # Complete: Use existing global grid, cut + partition for 64 MPI processes
  python examples/09_goias_shapefile_grid.py --global-grid x1.40962.grid.nc --nprocs 64

  # Production: Full pipeline with partition
  python examples/09_goias_shapefile_grid.py --jigsaw --nprocs 128
        """
    )
    parser.add_argument(
        '--jigsaw',
        action='store_true',
        help='Run JIGSAW mesh generation and convert to MPAS format'
    )
    parser.add_argument(
        '--global-grid',
        type=str,
        default=None,
        help='Path to existing global MPAS grid file (skips JIGSAW, uses this for cut)'
    )
    parser.add_argument(
        '--nprocs', '-n',
        type=int,
        default=None,
        help='Number of MPI processes for partitioning (requires cut step)'
    )

    args = parser.parse_args()

    # Run the complete pipeline
    results = main(
        run_jigsaw=args.jigsaw,
        global_grid_file=args.global_grid,
        num_partitions=args.nprocs,
    )
