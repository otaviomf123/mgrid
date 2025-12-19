"""
Command-line interface for m-grid.

Usage examples:

    # Generate uniform 30 km grid
    m-grid uniform --resolution 30 --output my_grid

    # Generate icosahedral grid
    m-grid icosahedral --level 6 --output icos_grid

    # Generate from configuration file
    m-grid config --file my_config.json --output var_res_grid
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='m-grid',
        description='MPAS/MONAN mesh generation tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  m-grid uniform -r 30 -o global_30km
  m-grid icosahedral -l 6 -o icos_level6
  m-grid config -f config.json -o my_grid --plot
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Grid type')

    # Uniform resolution grid
    uniform_parser = subparsers.add_parser(
        'uniform',
        help='Generate uniform resolution grid'
    )
    uniform_parser.add_argument(
        '-r', '--resolution',
        type=float,
        required=True,
        help='Target resolution in km'
    )
    uniform_parser.add_argument(
        '-o', '--output',
        type=str,
        default='mesh_uniform',
        help='Output basename (default: mesh_uniform)'
    )
    uniform_parser.add_argument(
        '--mpas',
        action='store_true',
        help='Convert to MPAS format'
    )
    uniform_parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate diagnostic plots'
    )

    # Icosahedral grid
    icos_parser = subparsers.add_parser(
        'icosahedral',
        aliases=['icos'],
        help='Generate icosahedral grid'
    )
    icos_parser.add_argument(
        '-l', '--level',
        type=int,
        default=4,
        help='Refinement level (default: 4, ~120 km)'
    )
    icos_parser.add_argument(
        '-o', '--output',
        type=str,
        default='mesh_icos',
        help='Output basename'
    )
    icos_parser.add_argument(
        '--mpas',
        action='store_true',
        help='Convert to MPAS format'
    )

    # Configuration file
    config_parser = subparsers.add_parser(
        'config',
        help='Generate grid from configuration file'
    )
    config_parser.add_argument(
        '-f', '--file',
        type=str,
        required=True,
        help='JSON configuration file'
    )
    config_parser.add_argument(
        '-o', '--output',
        type=str,
        default='mesh_config',
        help='Output basename'
    )
    config_parser.add_argument(
        '--mpas',
        action='store_true',
        help='Convert to MPAS format'
    )
    config_parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate diagnostic plots'
    )

    # Info command
    info_parser = subparsers.add_parser(
        'info',
        help='Show information about an MPAS grid file'
    )
    info_parser.add_argument(
        'file',
        type=str,
        help='MPAS grid file (.nc)'
    )

    # Version
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == 'uniform':
            _cmd_uniform(args)
        elif args.command in ['icosahedral', 'icos']:
            _cmd_icosahedral(args)
        elif args.command == 'config':
            _cmd_config(args)
        elif args.command == 'info':
            _cmd_info(args)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_uniform(args):
    """Handle uniform grid command."""
    from .api import generate_mesh, save_grid

    print(f"\n{'='*60}")
    print("m-grid: Uniform Resolution Grid")
    print(f"{'='*60}")
    print(f"Resolution: {args.resolution} km")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")

    grid = generate_mesh(
        resolution=args.resolution,
        output_path=args.output,
        plot=args.plot
    )

    print(grid.summary())

    if args.mpas:
        output_file = f"{args.output}_mpas.nc"
        save_grid(grid, output_file)
        print(f"\nMPAS grid saved to: {output_file}")


def _cmd_icosahedral(args):
    """Handle icosahedral grid command."""
    from .api import generate_icosahedral, save_grid

    print(f"\n{'='*60}")
    print("m-grid: Icosahedral Grid")
    print(f"{'='*60}")
    print(f"Level: {args.level}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")

    grid = generate_icosahedral(
        level=args.level,
        output_path=args.output
    )

    print(grid.summary())

    if args.mpas:
        output_file = f"{args.output}_mpas.nc"
        save_grid(grid, output_file)
        print(f"\nMPAS grid saved to: {output_file}")


def _cmd_config(args):
    """Handle config file command."""
    from .api import generate_mesh, save_grid

    print(f"\n{'='*60}")
    print("m-grid: Configuration-based Grid")
    print(f"{'='*60}")
    print(f"Config: {args.file}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")

    grid = generate_mesh(
        config=args.file,
        output_path=args.output,
        plot=args.plot
    )

    print(grid.summary())

    if args.mpas:
        output_file = f"{args.output}_mpas.nc"
        save_grid(grid, output_file)
        print(f"\nMPAS grid saved to: {output_file}")


def _cmd_info(args):
    """Handle info command."""
    from .io import read_mpas_grid

    print(f"\n{'='*60}")
    print(f"Grid Information: {args.file}")
    print(f"{'='*60}\n")

    info = read_mpas_grid(args.file)

    print(f"Number of cells: {info['n_cells']:,}")
    print(f"Number of edges: {info['n_edges']:,}")
    print(f"Number of vertices: {info['n_vertices']:,}")

    if 'sphere_radius' in info:
        print(f"Sphere radius: {info['sphere_radius']}")

    print(f"\nVariables: {len(info['variables'])}")
    for var in sorted(info['variables'])[:20]:
        print(f"  - {var}")
    if len(info['variables']) > 20:
        print(f"  ... and {len(info['variables']) - 20} more")


if __name__ == '__main__':
    main()
