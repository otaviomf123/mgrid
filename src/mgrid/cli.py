"""
Command-line interface for mgrid.

Unified workflow: A single configuration file controls the entire pipeline.

Usage:
    # Run complete pipeline from config
    mgrid config.json

    # Override static file (skip JIGSAW, use existing file for regional cut)
    mgrid config.json --static-file path/to/static.nc

    # Show grid info
    mgrid info grid.nc
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='mgrid',
        description='MPAS/MONAN mesh generation tool - Unified workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate mesh from config (complete pipeline)
  mgrid config.json

  # Use existing static file (skip JIGSAW generation)
  mgrid config.json --static-file static.nc

  # Show info about an MPAS grid file
  mgrid info grid.nc

Config file example:
  {
      "name": "my_region",
      "background_resolution": 30.0,
      "regions": [...],
      "output_dir": "output",
      "regional_cut": {
          "type": "circle",
          "inside_point": [-16.0, -49.5],
          "radius": 500000
      },
      "partitions": [32, 64, 128]
  }

Documentation: https://github.com/otaviomf123/mgrid
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Run command (default when positional config is given)
    run_parser = subparsers.add_parser(
        'run',
        help='Run pipeline from configuration file'
    )
    run_parser.add_argument(
        'config',
        type=str,
        help='JSON configuration file'
    )
    run_parser.add_argument(
        '--static-file', '-s',
        type=str,
        default=None,
        help='Static file to use (skips JIGSAW generation)'
    )
    run_parser.add_argument(
        '--jigsaw',
        action='store_true',
        help='Force JIGSAW mesh generation'
    )
    run_parser.add_argument(
        '--no-plot',
        action='store_true',
        help='Skip plot generation'
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

    # Handle case where first argument is a .json file (shortcut for 'run')
    # Check BEFORE parsing if first arg is a .json file
    if len(sys.argv) > 1 and sys.argv[1].endswith('.json'):
        # Insert 'run' command before the json file
        sys.argv.insert(1, 'run')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == 'run':
            _cmd_run(args)
        elif args.command == 'info':
            _cmd_info(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def _cmd_run(args):
    """Handle unified run command."""
    from .api import generate_mesh
    from .io import load_config, save_config
    from .limited_area import (
        generate_pts_file,
        create_regional_mesh_python,
        partition_mesh,
    )

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load configuration
    config = load_config(config_path)

    print("\n" + "=" * 70)
    print("mgrid: MPAS/MONAN Mesh Generation Pipeline")
    print("=" * 70)
    print(f"Configuration: {config_path}")
    print(f"Name: {config.get('name', 'unnamed')}")
    if config.get('description'):
        print(f"Description: {config['description']}")
    print("=" * 70)

    # Determine output directory
    output_dir = Path(config.get('output_dir', 'output'))
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir.absolute()}")

    results = {'config': config}

    # Determine static file source
    static_file = args.static_file or config.get('static_file')

    # =========================================================================
    # STEP 1: Generate mesh with JIGSAW (if no static file provided)
    # =========================================================================
    if static_file is None or args.jigsaw:
        print("\n" + "-" * 70)
        print("STEP 1: Generate mesh with JIGSAW")
        print("-" * 70)

        mesh_name = config.get('name', 'mesh')
        output_path = output_dir / mesh_name

        grid = generate_mesh(
            config=config,
            output_path=str(output_path),
            generate_jigsaw=True,
            plot=not args.no_plot
        )

        print("\n" + grid.summary())
        results['grid'] = grid
        results['mesh_file'] = grid.mesh_file

        # The generated grid.nc file
        generated_grid = output_path.parent / f"{output_path.name}.grid.nc"
        if generated_grid.exists():
            results['grid_file'] = str(generated_grid)
            print(f"\nGrid file: {generated_grid}")
            print("\n" + "=" * 70)
            print("NEXT STEP: Generate static file (external)")
            print("=" * 70)
            print("Configure namelist.init_atmosphere with:")
            print("  - config_static_interp = true")
            print(f"  - Grid file: {generated_grid}")
            print("\nSee: https://www2.mmm.ucar.edu/projects/mpas/site/documentation/")
            print("\nThen re-run with:")
            print(f"  mgrid {args.config} --static-file static.nc")

    # =========================================================================
    # STEP 2: Regional cut (if static file provided)
    # =========================================================================
    if static_file:
        static_path = Path(static_file)
        if not static_path.exists():
            raise FileNotFoundError(f"Static file not found: {static_path}")

        print("\n" + "-" * 70)
        print("STEP 2: Cut regional mesh from static file")
        print("-" * 70)
        print(f"Static file: {static_path}")

        # Get regional cut specification
        regional_cut = config.get('regional_cut', {})

        if not regional_cut:
            # Try to infer from regions
            regions = config.get('regions', [])
            if regions:
                # Use the first polygon region or largest circle
                for r in regions:
                    if r.get('type') == 'polygon':
                        regional_cut = {
                            'type': 'custom',
                            'polygon': r.get('polygon', []),
                        }
                        # Calculate centroid
                        polygon = r.get('polygon', [])
                        if polygon:
                            lats = [p[0] for p in polygon]
                            lons = [p[1] for p in polygon]
                            regional_cut['inside_point'] = [
                                sum(lats) / len(lats),
                                sum(lons) / len(lons)
                            ]
                        break
                    elif r.get('type') == 'circle':
                        regional_cut = {
                            'type': 'circle',
                            'inside_point': r.get('center'),
                            'radius': r.get('radius', 100) * 1000,  # km to m
                        }

        if not regional_cut:
            raise ValueError(
                "No 'regional_cut' specification in config. "
                "Add 'regional_cut' section with type, inside_point, and polygon/radius."
            )

        # Generate .pts file
        mesh_name = config.get('name', 'region')
        pts_file = output_dir / f"{mesh_name}.pts"

        cut_type = regional_cut.get('type', 'custom')
        inside_point = regional_cut.get('inside_point')

        if cut_type == 'circle':
            pts_path = generate_pts_file(
                output_path=pts_file,
                name=mesh_name,
                region_type='circle',
                inside_point=tuple(inside_point),
                radius=regional_cut.get('radius'),
            )
        else:
            polygon = regional_cut.get('polygon', [])
            polygon_tuples = [(p[0], p[1]) for p in polygon]
            pts_path = generate_pts_file(
                output_path=pts_file,
                name=mesh_name,
                region_type='custom',
                inside_point=tuple(inside_point),
                polygon=polygon_tuples,
            )

        print(f"Points file: {pts_path}")

        # Cut regional mesh
        regional_grid, graph_file = create_regional_mesh_python(
            pts_file=pts_path,
            global_grid_file=static_path,
            verbose=1,
        )

        results['regional_grid'] = regional_grid
        results['graph_file'] = graph_file
        results['pts_file'] = str(pts_path)

        print(f"Regional grid: {regional_grid}")
        print(f"Graph file: {graph_file}")

        # =================================================================
        # STEP 3: Partition mesh (if partitions specified)
        # =================================================================
        partitions = config.get('partitions', [])
        if partitions:
            print("\n" + "-" * 70)
            print(f"STEP 3: Partition mesh for MPI ({partitions} processes)")
            print("-" * 70)

            if isinstance(partitions, int):
                partitions = [partitions]

            results['partition_files'] = []
            for nprocs in partitions:
                print(f"\n  Partitioning for {nprocs} processes...")
                partition_file = partition_mesh(
                    graph_file=graph_file,
                    num_partitions=nprocs,
                )
                results['partition_files'].append(str(partition_file))

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir.absolute()}")

    if 'regional_grid' in results:
        print("\nGenerated files:")
        print(f"  Regional grid:  {Path(results['regional_grid']).name}")
        print(f"  Graph file:     {Path(results['graph_file']).name}")
        if 'partition_files' in results:
            for pf in results['partition_files']:
                print(f"  Partition:      {Path(pf).name}")

        print("\nTo run MPAS/MONAN:")
        print(f"  cp {results['regional_grid']} ./")
        if results.get('partition_files'):
            print(f"  cp {results['partition_files'][0]} ./")
            nprocs = Path(results['partition_files'][0]).name.split('.')[-1]
            print(f"  mpirun -np {nprocs} ./atmosphere_model")

    elif 'grid_file' in results:
        print("\nGenerated files:")
        print(f"  Grid file: {results['grid_file']}")
        print("\nNext step: Configure namelist.init_atmosphere (see MPAS docs)")

    print("\n" + "=" * 70 + "\n")

    return results


def _cmd_info(args):
    """Handle info command."""
    from .io import read_mpas_grid

    print(f"\n{'=' * 60}")
    print(f"Grid Information: {args.file}")
    print(f"{'=' * 60}\n")

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
