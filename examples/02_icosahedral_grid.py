#!/usr/bin/env python
"""
Example 02: Generate an icosahedral mesh.

Icosahedral meshes are quasi-uniform grids created by recursively
subdividing a regular icosahedron projected onto the sphere.

Refinement levels and approximate resolutions:
- Level 2: ~500 km (~640 cells)
- Level 4: ~120 km (~10,000 cells)
- Level 6: ~30 km (~160,000 cells)
- Level 8: ~7 km (~2,500,000 cells)
"""

from mgrid import generate_icosahedral, save_grid, icosahedral_resolution


def main():
    # Show resolution for different levels
    print("Icosahedral grid resolutions by level:")
    print("-" * 40)
    for level in range(2, 10):
        res = icosahedral_resolution(level)
        print(f"  Level {level}: ~{res:.0f} km")
    print()

    # Generate level 5 icosahedral grid (~60 km)
    level = 5
    print(f"Generating icosahedral grid at level {level}...")

    grid = generate_icosahedral(
        level=level,
        output_path='output/icosahedral_level5'
    )

    print(grid.summary())

    # Convert to MPAS format
    print("\nConverting to MPAS format...")
    mpas_file = save_grid(grid, 'output/icosahedral_level5_mpas.nc')

    print(f"\nDone! MPAS grid saved to: {mpas_file}")


if __name__ == '__main__':
    main()
