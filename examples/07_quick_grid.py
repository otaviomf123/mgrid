#!/usr/bin/env python
"""
Example 07: Quick one-liner grid generation.

The simplest possible way to generate an MPAS grid file.
"""

from mgrid import quick_grid


def main():
    # Generate a 50 km global grid in one line
    mpas_file = quick_grid(resolution=50, output='output/quick_50km.nc')

    print(f"MPAS grid generated: {mpas_file}")


if __name__ == '__main__':
    main()
