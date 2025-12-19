#!/usr/bin/env python
"""
Example 06: Generate a grid from a JSON configuration file.

This is the recommended approach for complex grids that need to be
reproduced or shared. The configuration file stores all parameters
in a human-readable format.
"""

from pathlib import Path
from mgrid import generate_mesh, save_grid, load_config, validate_config


# Example configuration (saved to file)
EXAMPLE_CONFIG = {
    "description": "Example multi-region grid for South America",
    "background_resolution": 120.0,
    "grid_density": 0.05,
    "regions": [
        {
            "name": "Southeast_Brazil",
            "type": "polygon",
            "polygon": [
                [-19.0, -48.0],
                [-19.0, -40.0],
                [-25.0, -40.0],
                [-25.0, -48.0]
            ],
            "resolution": 10.0,
            "transition_start": 40.0,
            "description": "10 km resolution over SE Brazil"
        },
        {
            "name": "Sao_Paulo_Metro",
            "type": "circle",
            "center": [-23.55, -46.63],
            "radius": 80,
            "resolution": 3.0,
            "transition_start": 10.0,
            "description": "3 km resolution over SP metropolitan area"
        }
    ],
    "notes": [
        "Background covers global domain at 120 km",
        "Southeast Brazil polygon at 10 km for regional features",
        "Sao Paulo metropolitan area at 3 km for urban effects"
    ]
}


def main():
    import json

    # Create output directory
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # Save example configuration
    config_file = output_dir / 'example_config.json'
    with open(config_file, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f, indent=2)
    print(f"Saved example configuration to: {config_file}")

    # Load and validate configuration
    print("\nLoading configuration...")
    config = load_config(config_file)
    validate_config(config)
    print("Configuration validated successfully!")

    # Generate grid from config
    print("\nGenerating grid from configuration...")
    grid = generate_mesh(
        config=config_file,
        output_path='output/from_config',
        plot=True
    )

    print("\n" + grid.summary())

    # Save to MPAS format
    print("\nConverting to MPAS format...")
    mpas_file = save_grid(grid, 'output/from_config_mpas.nc')

    print(f"\nDone! MPAS grid saved to: {mpas_file}")

    # Also demonstrate passing config as dict directly
    print("\n--- Alternative: Pass config dict directly ---")
    grid2 = generate_mesh(
        config=EXAMPLE_CONFIG,  # Dict instead of file
        output_path='output/from_dict',
        generate_jigsaw=False  # Skip mesh generation, just compute cell width
    )
    print(f"Cell width computed: {grid2.min_resolution:.1f} - {grid2.max_resolution:.1f} km")


if __name__ == '__main__':
    main()
