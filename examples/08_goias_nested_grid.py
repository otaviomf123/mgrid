#!/usr/bin/env python
"""
Example 08: Nested Grid for Goias State - MPAS/MONAN

This example creates a multi-resolution nested grid for the state of Goias,
Brazil, with the following configuration:

Resolution Hierarchy (from finest to coarsest):
==============================================

1. GOIANIA (innermost):
   - Resolution: 1 km
   - Type: Circular
   - Center: Goiania city (-16.68, -49.25)
   - Radius: 50 km (covers metropolitan area)
   - Transition: 1 km -> 3 km over 30 km

2. GOIAS STATE (middle):
   - Resolution: 3 km
   - Type: Circular (approximating state boundaries)
   - Center: Geographic center of Goias (-15.93, -49.86)
   - Radius: 350 km (covers entire state)
   - Transition: 3 km -> 5 km over 50 km

3. REGIONAL BUFFER (outer):
   - Resolution: 5 km
   - Type: Square/Polygon region (~2 degrees around state border)
   - Covers: lat [-20, -10], lon [-54, -45]
   - Transition: 5 km -> 30 km over 200 km

4. GLOBAL BACKGROUND:
   - Resolution: 30 km
   - Covers: Rest of the globe

Transition Zones:
================
- Goiania -> Goias: Smooth transition from 1 km to 3 km
- Goias -> Regional: Smooth transition from 3 km to 5 km
- Regional -> Global: Smooth transition from 5 km to 30 km

This configuration is suitable for:
- High-resolution urban weather prediction for Goiania
- Mesoscale simulations for Goias state
- Regional climate studies for Central Brazil

Author: MONAN Development Team
"""

import json
import numpy as np
from pathlib import Path

# Import mgrid components
from mgrid import (
    generate_mesh,
    save_grid,
    CircularRegion,
    PolygonRegion,
    load_config,
    save_config,
)


def create_goias_config():
    """
    Create the configuration dictionary for the Goias nested grid.

    Returns
    -------
    config : dict
        Configuration dictionary with all region definitions.
    """
    config = {
        "description": "Multi-resolution nested grid for Goias State, Brazil",
        "author": "MONAN Development Team",
        "background_resolution": 30.0,
        "grid_density": 0.5,  # Density factor for faster computation
        "regions": [
            {
                "name": "Regional_Buffer",
                "type": "polygon",
                "description": "5 km resolution square buffer zone around Goias",
                "polygon": [
                    [-10.0, -54.0],  # NW corner (lat, lon)
                    [-10.0, -45.0],  # NE corner
                    [-20.0, -45.0],  # SE corner
                    [-20.0, -54.0],  # SW corner
                ],
                "resolution": 5.0,
                "transition_start": 30.0  # Transitions to 30 km background
            },
            {
                "name": "Goias_State",
                "type": "circle",
                "description": "3 km resolution covering entire Goias state",
                "center": [-15.93, -49.86],  # Geographic center of Goias
                "radius": 350.0,  # km - covers the whole state
                "resolution": 3.0,
                "transition_start": 5.0  # Transitions to 5 km regional buffer
            },
            {
                "name": "Goiania_Metro",
                "type": "circle",
                "description": "1 km resolution for Goiania metropolitan area",
                "center": [-16.68, -49.25],  # Goiania city center
                "radius": 50.0,  # km - metropolitan area
                "resolution": 1.0,
                "transition_start": 3.0  # Transitions to 3 km state resolution
            }
        ],
        "notes": [
            "Goiania coordinates: -16.68 lat, -49.25 lon",
            "Goias state center: -15.93 lat, -49.86 lon",
            "State radius of 350 km covers from Jatai to Formosa",
            "Regional buffer is a square polygon covering lat [-20, -10], lon [-54, -45]",
            "Grid density of 0.5 for fast computation (use 0.05 for production)",
            "Total transition from 1 km to 30 km is smooth and gradual"
        ]
    }

    return config


def create_regions_from_config(config):
    """
    Create Region objects from the configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary.

    Returns
    -------
    regions : list
        List of Region objects.
    """
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


def print_grid_info(config):
    """
    Print detailed information about the grid configuration.

    Parameters
    ----------
    config : dict
        Configuration dictionary.
    """
    print("=" * 70)
    print("GOIAS NESTED GRID CONFIGURATION")
    print("=" * 70)
    print(f"\nDescription: {config['description']}")
    print(f"Background Resolution: {config['background_resolution']} km")
    print(f"Grid Density Factor: {config['grid_density']}")

    print("\n" + "-" * 70)
    print("RESOLUTION HIERARCHY (from finest to coarsest):")
    print("-" * 70)

    # Sort regions by resolution (finest first)
    sorted_regions = sorted(config["regions"], key=lambda x: x["resolution"])

    for i, region in enumerate(sorted_regions, 1):
        print(f"\n{i}. {region['name']}")
        print(f"   Type: {region['type'].capitalize()}")
        print(f"   Resolution: {region['resolution']} km")
        print(f"   Transition to: {region['transition_start']} km")

        if region["type"] == "circle":
            print(f"   Center: {region['center']} (lat, lon)")
            print(f"   Radius: {region['radius']} km")
        elif region["type"] == "polygon":
            print(f"   Vertices: {len(region['polygon'])} points")
            print(f"   Bounds: {region['polygon']}")

        if "description" in region:
            print(f"   Description: {region['description']}")

    print("\n" + "-" * 70)
    print("TRANSITION ZONES:")
    print("-" * 70)
    print("  Goiania (1 km) --[30 km zone]--> Goias State (3 km)")
    print("  Goias State (3 km) --[50 km zone]--> Regional Buffer (5 km)")
    print("  Regional Buffer (5 km) --[200 km zone]--> Global (30 km)")

    print("\n" + "=" * 70 + "\n")


def plot_with_basemap(grid, config, output_dir):
    """
    Create publication-quality plots using Basemap with Brazilian states.

    Parameters
    ----------
    grid : Grid
        Generated grid object.
    config : dict
        Configuration dictionary.
    output_dir : Path
        Output directory for plots.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from mpl_toolkits.basemap import Basemap

    # Create meshgrid for plotting
    lons, lats = np.meshgrid(grid.lon, grid.lat)

    # =========================================================================
    # PLOT 1: Regional View with Brazilian States
    # =========================================================================
    fig, ax = plt.subplots(figsize=(14, 12))

    # Create Basemap for regional view
    m = Basemap(
        projection='merc',
        llcrnrlat=-22,
        urcrnrlat=-8,
        llcrnrlon=-56,
        urcrnrlon=-43,
        resolution='i',  # intermediate resolution
        ax=ax
    )

    # Draw map features
    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    m.drawstates(linewidth=0.8, color='darkgray')  # Brazilian states
    m.drawparallels(np.arange(-22, -6, 2), labels=[1, 0, 0, 0], fontsize=10)
    m.drawmeridians(np.arange(-56, -42, 2), labels=[0, 0, 0, 1], fontsize=10)

    # Convert grid coordinates to map projection
    x, y = m(lons, lats)

    # Plot cell width as filled contours
    levels = np.linspace(1, 30, 30)
    cs = m.contourf(x, y, grid.cell_width, levels=levels, cmap='viridis', extend='both')

    # Add colorbar
    cbar = m.colorbar(cs, location='right', pad='5%')
    cbar.set_label('Cell Width (km)', fontsize=12)

    # Plot region boundaries
    # Regional buffer (square polygon)
    regional_poly = config["regions"][0]["polygon"]
    poly_lons = [p[1] for p in regional_poly] + [regional_poly[0][1]]
    poly_lats = [p[0] for p in regional_poly] + [regional_poly[0][0]]
    px, py = m(poly_lons, poly_lats)
    m.plot(px, py, 'w-', linewidth=3, label='Regional Buffer (5 km)')
    m.plot(px, py, 'k--', linewidth=1.5)

    # Goias state circle
    theta = np.linspace(0, 2 * np.pi, 100)
    state_center = config["regions"][1]["center"]
    state_radius_deg = config["regions"][1]["radius"] / 111.0
    state_lons = state_center[1] + state_radius_deg * np.cos(theta)
    state_lats = state_center[0] + state_radius_deg * np.sin(theta)
    sx, sy = m(state_lons, state_lats)
    m.plot(sx, sy, 'w-', linewidth=2.5)
    m.plot(sx, sy, 'r--', linewidth=1.5, label='Goias State (3 km)')

    # Goiania metro circle
    metro_center = config["regions"][2]["center"]
    metro_radius_deg = config["regions"][2]["radius"] / 111.0
    metro_lons = metro_center[1] + metro_radius_deg * np.cos(theta)
    metro_lats = metro_center[0] + metro_radius_deg * np.sin(theta)
    mx, my = m(metro_lons, metro_lats)
    m.plot(mx, my, 'w-', linewidth=2)
    m.plot(mx, my, 'm-', linewidth=1.5, label='Goiania Metro (1 km)')

    # Mark cities
    cities = {
        'Goiania': (-16.68, -49.25),
        'Brasilia': (-15.79, -47.88),
        'Uberlandia': (-18.92, -48.28),
        'Cuiaba': (-15.60, -56.10),
    }

    for city, (lat, lon) in cities.items():
        cx, cy = m(lon, lat)
        m.plot(cx, cy, 'r*', markersize=12, markeredgecolor='white', markeredgewidth=0.5)
        ax.text(cx, cy + 30000, city, fontsize=9, ha='center', fontweight='bold',
                color='white', path_effects=[pe.withStroke(linewidth=2, foreground='black')])

    # Title and legend
    ax.set_title('Goias Nested Grid - Regional View\nMPAS/MONAN Variable Resolution Mesh',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'goias_regional_basemap.png', dpi=150, bbox_inches='tight')
    print(f"       Saved: {output_dir / 'goias_regional_basemap.png'}")
    plt.close()

    # =========================================================================
    # PLOT 2: Zoomed view of Goiania
    # =========================================================================
    fig, ax = plt.subplots(figsize=(12, 10))

    # Create Basemap for Goiania zoom
    m2 = Basemap(
        projection='merc',
        llcrnrlat=-18.0,
        urcrnrlat=-15.0,
        llcrnrlon=-50.5,
        urcrnrlon=-47.5,
        resolution='h',  # high resolution
        ax=ax
    )

    # Draw map features
    m2.drawcoastlines(linewidth=0.5)
    m2.drawcountries(linewidth=0.5)
    m2.drawstates(linewidth=1.0, color='darkgray')
    m2.drawparallels(np.arange(-18, -14, 0.5), labels=[1, 0, 0, 0], fontsize=10)
    m2.drawmeridians(np.arange(-51, -47, 0.5), labels=[0, 0, 0, 1], fontsize=10)

    # Convert coordinates
    x2, y2 = m2(lons, lats)

    # Plot cell width
    levels2 = np.linspace(1, 5, 20)
    cs2 = m2.contourf(x2, y2, grid.cell_width, levels=levels2, cmap='viridis', extend='both')

    cbar2 = m2.colorbar(cs2, location='right', pad='5%')
    cbar2.set_label('Cell Width (km)', fontsize=12)

    # Draw Goiania metro circle
    mx2, my2 = m2(metro_lons, metro_lats)
    m2.plot(mx2, my2, 'r-', linewidth=2.5, label='Metro Area (50 km)')

    # Mark Goiania center
    gx, gy = m2(metro_center[1], metro_center[0])
    m2.plot(gx, gy, 'r*', markersize=20, markeredgecolor='white', markeredgewidth=1)
    ax.text(gx, gy + 8000, 'Goiania', fontsize=12, ha='center', fontweight='bold',
            color='white', path_effects=[pe.withStroke(linewidth=3, foreground='black')])

    # Mark nearby cities
    nearby_cities = {
        'Anapolis': (-16.33, -48.95),
        'Aparecida': (-16.82, -49.24),
        'Trindade': (-16.65, -49.49),
    }

    for city, (lat, lon) in nearby_cities.items():
        cx, cy = m2(lon, lat)
        m2.plot(cx, cy, 'wo', markersize=6, markeredgecolor='black')
        ax.text(cx + 5000, cy, city, fontsize=8, va='center')

    ax.set_title('Goiania Metropolitan Area - High Resolution Zone (1 km)',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'goias_goiania_zoom_basemap.png', dpi=150, bbox_inches='tight')
    print(f"       Saved: {output_dir / 'goias_goiania_zoom_basemap.png'}")
    plt.close()

    # =========================================================================
    # PLOT 3: South America Context
    # =========================================================================
    fig, ax = plt.subplots(figsize=(12, 10))

    # Create Basemap for South America
    m3 = Basemap(
        projection='merc',
        llcrnrlat=-35,
        urcrnrlat=5,
        llcrnrlon=-75,
        urcrnrlon=-35,
        resolution='l',  # low resolution for speed
        ax=ax
    )

    # Draw map features
    m3.drawcoastlines(linewidth=0.5)
    m3.drawcountries(linewidth=0.8)
    m3.drawstates(linewidth=0.3, color='gray')
    m3.fillcontinents(color='lightgray', lake_color='lightblue', alpha=0.3)
    m3.drawmapboundary(fill_color='lightblue')
    m3.drawparallels(np.arange(-35, 10, 5), labels=[1, 0, 0, 0], fontsize=9)
    m3.drawmeridians(np.arange(-75, -30, 5), labels=[0, 0, 0, 1], fontsize=9)

    # Convert coordinates
    x3, y3 = m3(lons, lats)

    # Plot cell width
    levels3 = np.linspace(1, 30, 30)
    cs3 = m3.contourf(x3, y3, grid.cell_width, levels=levels3, cmap='viridis',
                       extend='both', alpha=0.8)

    cbar3 = m3.colorbar(cs3, location='right', pad='5%')
    cbar3.set_label('Cell Width (km)', fontsize=12)

    # Draw regional buffer polygon
    px3, py3 = m3(poly_lons, poly_lats)
    m3.plot(px3, py3, 'r-', linewidth=2, label='Regional Buffer')

    # Draw state circle
    sx3, sy3 = m3(state_lons, state_lats)
    m3.plot(sx3, sy3, 'm--', linewidth=1.5, label='Goias State')

    # Mark Goiania
    gx3, gy3 = m3(metro_center[1], metro_center[0])
    m3.plot(gx3, gy3, 'r*', markersize=15)
    ax.text(gx3, gy3 + 100000, 'Goiania', fontsize=10, ha='center', fontweight='bold')

    ax.set_title('South America Context - Goias Nested Grid\nVariable Resolution: 1 km to 30 km',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_dir / 'goias_south_america_context.png', dpi=150, bbox_inches='tight')
    print(f"       Saved: {output_dir / 'goias_south_america_context.png'}")
    plt.close()

    # =========================================================================
    # PLOT 4: Resolution histogram
    # =========================================================================
    fig, ax = plt.subplots(figsize=(10, 6))

    # Histogram of cell widths
    hist_data = grid.cell_width.flatten()
    bins = np.linspace(0, 32, 65)

    ax.hist(hist_data, bins=bins, edgecolor='black', alpha=0.7, color='steelblue')
    ax.set_xlabel('Cell Width (km)', fontsize=12)
    ax.set_ylabel('Frequency (log scale)', fontsize=12)
    ax.set_yscale('log')
    ax.set_title('Grid Resolution Distribution', fontsize=14, fontweight='bold')

    # Add vertical lines for target resolutions
    ax.axvline(x=1, color='red', linestyle='--', linewidth=2, label='Goiania (1 km)')
    ax.axvline(x=3, color='orange', linestyle='--', linewidth=2, label='Goias (3 km)')
    ax.axvline(x=5, color='green', linestyle='--', linewidth=2, label='Regional (5 km)')
    ax.axvline(x=30, color='purple', linestyle='--', linewidth=2, label='Global (30 km)')

    # Add statistics text
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


def main():
    """
    Main function to generate the Goias nested grid.
    """
    # Create output directory
    output_dir = Path("output/goias_grid")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create configuration
    print("\n[1/5] Creating grid configuration...")
    config = create_goias_config()

    # Print detailed information
    print_grid_info(config)

    # Save configuration to JSON file
    config_file = output_dir / "goias_config.json"
    save_config(config, config_file)
    print(f"[2/5] Configuration saved to: {config_file}")

    # Generate the mesh (cell width only, without JIGSAW)
    print("\n[3/5] Computing cell width function...")
    grid = generate_mesh(
        config=config,
        output_path=str(output_dir / "goias_mesh"),
        generate_jigsaw=False,  # Set to True when JIGSAW is available
        plot=False
    )

    # Print grid summary
    print("\n" + grid.summary())

    # Generate plots with Basemap
    print("\n[4/5] Generating plots with Basemap...")
    try:
        plot_with_basemap(grid, config, output_dir)
    except ImportError as e:
        print(f"       Warning: Could not import Basemap - {e}")
        print("       Install with: conda install -c conda-forge basemap basemap-data-hires")

    # Final summary
    print("\n[5/5] Generation complete!")
    print("\n" + "=" * 70)
    print("OUTPUT FILES")
    print("=" * 70)
    print(f"\nDirectory: {output_dir.absolute()}")
    print(f"  - goias_config.json              : Grid configuration")
    print(f"  - goias_regional_basemap.png     : Regional view with states")
    print(f"  - goias_goiania_zoom_basemap.png : Goiania metropolitan zoom")
    print(f"  - goias_south_america_context.png: South America context")
    print(f"  - goias_resolution_histogram.png : Resolution distribution")

    print("\n" + "-" * 70)
    print("RESOLUTION SUMMARY")
    print("-" * 70)
    print(f"  Minimum: {grid.min_resolution:.1f} km (Goiania center)")
    print(f"  Maximum: {grid.max_resolution:.1f} km (Global background)")
    print(f"  Mean:    {grid.mean_resolution:.1f} km")
    print(f"  Grid:    {grid.lat.size} x {grid.lon.size} points")

    print("\n" + "-" * 70)
    print("NEXT STEPS")
    print("-" * 70)
    print("  To generate the actual JIGSAW mesh for MPAS:")
    print("  1. Set generate_jigsaw=True in the code")
    print("  2. Reduce grid_density to 0.05 for production quality")
    print("  3. Run: save_grid(grid, 'goias_mpas.nc')")
    print("=" * 70 + "\n")

    return grid, config


if __name__ == "__main__":
    grid, config = main()
