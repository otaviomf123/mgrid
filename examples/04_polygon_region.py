#!/usr/bin/env python
"""
Example 04: Generate a variable-resolution grid with a polygon region.

This example creates a grid with high resolution over a polygonal area
(Mato Grosso state, Brazil) using vertices to define the refinement region.
"""

from mgrid import (
    generate_mesh,
    save_grid,
    PolygonRegion,
    plot_region_overview
)


def main():
    # Define Mato Grosso polygon (approximate boundaries)
    mato_grosso = PolygonRegion(
        name='Mato_Grosso',
        resolution=5.0,        # 5 km inside polygon
        transition_width=30,   # 30 km transition zone
        vertices=[
            # (lat, lon) coordinates
            (-7.06, -62.02),   # NW corner
            (-7.06, -49.54),   # NE corner
            (-18.50, -49.54),  # SE corner
            (-18.50, -62.02),  # SW corner
        ]
    )

    print("Generating variable-resolution grid with polygon region...")
    print(f"  Region: {mato_grosso.name}")
    print(f"  Vertices: {len(mato_grosso.vertices)}")
    print(f"  Resolution: {mato_grosso.resolution} km")

    # Show region overview
    try:
        plot_region_overview(
            [mato_grosso],
            background_resolution=100,
            lat_bounds=(-25, 5),
            lon_bounds=(-75, -35),
            output_file='output/mt_region_overview.png',
            show=True
        )
    except ImportError:
        print("(matplotlib not available, skipping plot)")

    # Generate the grid
    grid = generate_mesh(
        regions=[mato_grosso],
        background_resolution=100,
        output_path='output/mato_grosso_varres',
        plot=True
    )

    print("\n" + grid.summary())

    # Save to MPAS format
    print("\nConverting to MPAS format...")
    mpas_file = save_grid(grid, 'output/mato_grosso_varres_mpas.nc')

    print(f"\nDone! MPAS grid saved to: {mpas_file}")


if __name__ == '__main__':
    main()
