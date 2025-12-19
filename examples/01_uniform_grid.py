#!/usr/bin/env python
"""
Example 01: Generate a uniform resolution global grid.

This is the simplest use case - creating a global mesh with constant
cell size everywhere on the sphere.
"""

from mgrid import generate_mesh, save_grid


def main():
    # Generate a 30 km uniform resolution grid
    print("Generating 30 km uniform resolution grid...")

    grid = generate_mesh(
        resolution=30,  # 30 km cell size
        output_path='output/uniform_30km',
        plot=True  # Generate diagnostic plot
    )

    # Print grid information
    print("\n" + grid.summary())

    # Convert to MPAS format
    print("\nConverting to MPAS format...")
    mpas_file = save_grid(grid, 'output/uniform_30km_mpas.nc')

    print(f"\nDone! MPAS grid saved to: {mpas_file}")


if __name__ == '__main__':
    main()
