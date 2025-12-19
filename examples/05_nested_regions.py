#!/usr/bin/env python
"""
Example 05: Generate a grid with nested refinement regions.

This example demonstrates creating multiple nested regions with
progressively finer resolution - useful for regional weather prediction
where you need very high resolution in a specific area.

Configuration:
- Background: 150 km (global)
- Mato Grosso state: 10 km (regional)
- Sapezal farm: 2 km (local)
"""

from mgrid import (
    generate_mesh,
    save_grid,
    CircularRegion,
    PolygonRegion,
    plot_region_overview
)


def main():
    # Define nested regions (from coarse to fine)

    # Region 1: Mato Grosso state polygon (10 km)
    mato_grosso = PolygonRegion(
        name='Mato_Grosso',
        resolution=10.0,
        transition_width=40,  # 40 km transition
        vertices=[
            (-7.06, -62.02),
            (-7.06, -49.54),
            (-18.50, -49.54),
            (-18.50, -62.02),
        ]
    )

    # Region 2: Sapezal area (2 km) - nested inside Mato Grosso
    sapezal = CircularRegion(
        name='Fazenda_Sapezal',
        resolution=2.0,
        transition_width=8,  # 8 km transition to 10 km
        center=(-13.30, -56.03),  # Sapezal coordinates
        radius=100  # 100 km radius
    )

    regions = [mato_grosso, sapezal]

    print("Generating nested variable-resolution grid...")
    print("\nRegion hierarchy:")
    print("  1. Background: 150 km")
    print("  2. Mato Grosso: 10 km")
    print("  3. Sapezal: 2 km")

    # Plot region overview
    try:
        plot_region_overview(
            regions,
            background_resolution=150,
            lat_bounds=(-25, 0),
            lon_bounds=(-70, -45),
            output_file='output/nested_regions_overview.png',
            show=True
        )
    except ImportError:
        print("(matplotlib not available, skipping plot)")

    # Generate the grid
    # Note: grid_density may need to be smaller for very fine resolution
    grid = generate_mesh(
        regions=regions,
        background_resolution=150,
        grid_density=0.05,  # Adjust for finest resolution
        output_path='output/nested_varres',
        plot=True
    )

    print("\n" + grid.summary())

    # Save to MPAS format
    print("\nConverting to MPAS format...")
    mpas_file = save_grid(grid, 'output/nested_varres_mpas.nc')

    print(f"\nDone! MPAS grid saved to: {mpas_file}")


if __name__ == '__main__':
    main()
