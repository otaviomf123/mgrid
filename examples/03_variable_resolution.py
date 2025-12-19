#!/usr/bin/env python
"""
Example 03: Generate a variable-resolution grid with a circular region.

This example creates a grid with high resolution (5 km) in a circular
area centered on Sao Paulo, Brazil, with a smooth transition to coarser
background resolution (100 km).
"""

from mgrid import (
    generate_mesh,
    save_grid,
    CircularRegion,
    plot_cell_width
)


def main():
    # Define a circular refinement region
    sao_paulo = CircularRegion(
        name='Sao_Paulo',
        resolution=5.0,       # 5 km inside the circle
        transition_width=50,  # 50 km transition zone
        center=(-23.55, -46.63),  # (lat, lon) of Sao Paulo
        radius=200            # 200 km radius high-res area
    )

    print("Generating variable-resolution grid...")
    print(f"  Region: {sao_paulo.name}")
    print(f"  Center: {sao_paulo.center}")
    print(f"  Radius: {sao_paulo.radius} km")
    print(f"  Resolution: {sao_paulo.resolution} km")

    # Generate the grid
    grid = generate_mesh(
        regions=[sao_paulo],
        background_resolution=100,  # 100 km outside the region
        output_path='output/saopaulo_varres',
        plot=True
    )

    print("\n" + grid.summary())

    # Save to MPAS format
    print("\nConverting to MPAS format...")
    mpas_file = save_grid(grid, 'output/saopaulo_varres_mpas.nc')

    print(f"\nDone! MPAS grid saved to: {mpas_file}")


if __name__ == '__main__':
    main()
