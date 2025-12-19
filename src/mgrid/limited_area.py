"""
MPAS Limited-Area Integration Module

This module provides integration with the MPAS Limited-Area tool for creating
regional subsets from global MPAS grids.

The MPAS Limited-Area tool takes a global MPAS grid and produces a regional
area grid given a region specification. This module provides utilities to:

1. Generate points specification files (.pts) for different region types
2. Execute the MPAS Limited-Area tool programmatically
3. Integrate with mgrid configurations

Reference: https://github.com/MiCurry/MPAS-Limited-Area
"""

from pathlib import Path
from typing import List, Tuple, Optional, Union
import subprocess
import sys
import os


def generate_pts_file(
    output_path: Union[str, Path],
    name: str,
    region_type: str,
    inside_point: Tuple[float, float],
    polygon: Optional[List[Tuple[float, float]]] = None,
    radius: Optional[float] = None,
    semi_major_axis: Optional[float] = None,
    semi_minor_axis: Optional[float] = None,
    orientation_angle: Optional[float] = None,
    upper_lat: Optional[float] = None,
    lower_lat: Optional[float] = None,
) -> Path:
    """
    Generate a points specification file (.pts) for MPAS Limited-Area.

    Parameters
    ----------
    output_path : str or Path
        Path where the .pts file will be saved.
    name : str
        Name for the regional mesh (will be appended to output filename).
    region_type : str
        Type of region: 'custom' (polygon), 'circle', 'ellipse', or 'channel'.
    inside_point : tuple
        (latitude, longitude) of a point inside the region.
        For circle/ellipse, this is the center point.
    polygon : list, optional
        List of (lat, lon) tuples defining the polygon boundary.
        Required for 'custom' type. Points should be in counter-clockwise order.
    radius : float, optional
        Radius in meters. Required for 'circle' type.
    semi_major_axis : float, optional
        Semi-major axis in meters. Required for 'ellipse' type.
    semi_minor_axis : float, optional
        Semi-minor axis in meters. Required for 'ellipse' type.
    orientation_angle : float, optional
        Clockwise rotation from due north in degrees. Required for 'ellipse' type.
    upper_lat : float, optional
        Upper latitude in degrees. Required for 'channel' type.
    lower_lat : float, optional
        Lower latitude in degrees. Required for 'channel' type.

    Returns
    -------
    Path
        Path to the generated .pts file.

    Examples
    --------
    Generate a polygon (custom) region:
    >>> generate_pts_file(
    ...     'goias.pts',
    ...     name='goias',
    ...     region_type='custom',
    ...     inside_point=(-16.0, -49.5),
    ...     polygon=[(-12.4, -50.2), (-19.5, -50.8), (-18.7, -52.4), ...]
    ... )

    Generate a circular region:
    >>> generate_pts_file(
    ...     'metro.pts',
    ...     name='goiania_metro',
    ...     region_type='circle',
    ...     inside_point=(-16.71, -49.24),
    ...     radius=105000.0  # 105 km in meters
    ... )
    """
    output_path = Path(output_path)

    lines = []
    lines.append(f"Name: {name}")
    lines.append(f"Type: {region_type}")
    lines.append(f"Point: {inside_point[0]}, {inside_point[1]}")

    if region_type.lower() == 'custom':
        if polygon is None:
            raise ValueError("polygon is required for 'custom' region type")
        # Add polygon vertices
        for lat, lon in polygon:
            lines.append(f"{lat}, {lon}")

    elif region_type.lower() == 'circle':
        if radius is None:
            raise ValueError("radius is required for 'circle' region type")
        lines.append(f"Radius: {radius}")

    elif region_type.lower() == 'ellipse':
        if semi_major_axis is None or semi_minor_axis is None:
            raise ValueError("semi_major_axis and semi_minor_axis are required for 'ellipse' type")
        lines.append(f"Semi-major-axis: {semi_major_axis}")
        lines.append(f"Semi-minor-axis: {semi_minor_axis}")
        if orientation_angle is not None:
            lines.append(f"Orientation-angle: {orientation_angle}")

    elif region_type.lower() == 'channel':
        if upper_lat is None or lower_lat is None:
            raise ValueError("upper_lat and lower_lat are required for 'channel' type")
        lines.append(f"Upper-lat: {upper_lat}")
        lines.append(f"Lower-lat: {lower_lat}")
    else:
        raise ValueError(f"Unknown region type: {region_type}. Use 'custom', 'circle', 'ellipse', or 'channel'")

    # Write the file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    return output_path


def generate_pts_from_config(
    config: dict,
    output_path: Union[str, Path],
    region_name: Optional[str] = None,
    buffer_margin_deg: float = 1.0,
) -> Path:
    """
    Generate a .pts file from an mgrid configuration.

    This function extracts the outermost region (typically the regional buffer)
    from an mgrid configuration and generates a .pts file suitable for
    MPAS Limited-Area.

    Parameters
    ----------
    config : dict
        mgrid configuration dictionary.
    output_path : str or Path
        Path where the .pts file will be saved.
    region_name : str, optional
        Name for the region. If not provided, uses config name or 'region'.
    buffer_margin_deg : float, optional
        Additional margin in degrees to add around the region. Default is 1.0.

    Returns
    -------
    Path
        Path to the generated .pts file.
    """
    output_path = Path(output_path)

    # Find the outermost polygon region (lowest resolution)
    regions = config.get('regions', [])
    polygon_regions = [r for r in regions if r.get('type') == 'polygon']

    if not polygon_regions:
        raise ValueError("No polygon regions found in configuration")

    # Sort by resolution (descending) to get the outermost region
    polygon_regions.sort(key=lambda x: x.get('transition_start', 0), reverse=True)
    outer_region = polygon_regions[0]

    # Get polygon vertices
    polygon = outer_region.get('polygon', [])
    if not polygon:
        raise ValueError("No polygon vertices found in outer region")

    # Calculate centroid as inside point
    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    centroid = (sum(lats) / len(lats), sum(lons) / len(lons))

    # Convert to list of tuples
    polygon_tuples = [(p[0], p[1]) for p in polygon]

    # Determine name
    if region_name is None:
        region_name = config.get('name', outer_region.get('name', 'region'))

    return generate_pts_file(
        output_path=output_path,
        name=region_name,
        region_type='custom',
        inside_point=centroid,
        polygon=polygon_tuples,
    )


def create_regional_mesh(
    pts_file: Union[str, Path],
    global_grid_file: Union[str, Path],
    limited_area_path: Optional[Union[str, Path]] = None,
    verbose: int = 0,
    plot_only: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a regional MPAS mesh using the MPAS Limited-Area tool.

    Parameters
    ----------
    pts_file : str or Path
        Path to the points specification file (.pts).
    global_grid_file : str or Path
        Path to the global MPAS grid file (.nc).
    limited_area_path : str or Path, optional
        Path to the MPAS-Limited-Area directory. If not provided, will search
        in common locations or use the bundled version.
    verbose : int, optional
        Verbosity level (0-5). Default is 0.
    plot_only : bool, optional
        If True, only generate a plot of the region without creating the mesh.

    Returns
    -------
    tuple
        (regional_grid_file, graph_file) paths, or (None, None) if plot_only.

    Raises
    ------
    FileNotFoundError
        If the MPAS Limited-Area tool is not found.
    subprocess.CalledProcessError
        If the tool execution fails.
    """
    pts_file = Path(pts_file).resolve()

    if not plot_only:
        global_grid_file = Path(global_grid_file).resolve()
        if not global_grid_file.exists():
            raise FileNotFoundError(f"Global grid file not found: {global_grid_file}")

    if not pts_file.exists():
        raise FileNotFoundError(f"Points file not found: {pts_file}")

    # Find the create_region script
    if limited_area_path:
        create_region_script = Path(limited_area_path) / 'create_region'
    else:
        # Search in common locations
        search_paths = [
            Path(__file__).parent.parent.parent.parent / 'MPAS-Limited-Area' / 'create_region',
            Path.cwd() / 'MPAS-Limited-Area' / 'create_region',
            Path.home() / 'MPAS-Limited-Area' / 'create_region',
        ]

        create_region_script = None
        for p in search_paths:
            if p.exists():
                create_region_script = p
                break

        if create_region_script is None:
            raise FileNotFoundError(
                "MPAS-Limited-Area not found. Please clone it from "
                "https://github.com/MiCurry/MPAS-Limited-Area.git"
            )

    # Add the limited_area module to Python path
    limited_area_dir = create_region_script.parent
    if str(limited_area_dir) not in sys.path:
        sys.path.insert(0, str(limited_area_dir))

    # Build command
    cmd = [sys.executable, str(create_region_script)]

    if verbose > 0:
        cmd.extend(['-v', str(verbose)])

    if plot_only:
        cmd.append('-p')

    cmd.append(str(pts_file))

    if not plot_only:
        cmd.append(str(global_grid_file))

    print(f"Running: {' '.join(cmd)}")

    # Execute
    result = subprocess.run(
        cmd,
        cwd=str(pts_file.parent),
        capture_output=False,
        text=True,
    )

    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)

    if plot_only:
        return None, None

    # Find the output files
    # The output filename is based on the Name in the .pts file
    with open(pts_file, 'r') as f:
        for line in f:
            if line.strip().startswith('Name:'):
                region_name = line.split(':')[1].strip()
                break

    # Determine output type based on input file
    input_name = global_grid_file.name
    if 'static' in input_name:
        mesh_type = 'static'
    elif 'grid' in input_name:
        mesh_type = 'grid'
    elif 'init' in input_name:
        mesh_type = 'init'
    else:
        mesh_type = 'region'

    regional_grid = pts_file.parent / f"{region_name}.{mesh_type}.nc"
    graph_file = pts_file.parent / f"{region_name}.graph.info"

    return str(regional_grid), str(graph_file)


def create_regional_mesh_python(
    pts_file: Union[str, Path],
    global_grid_file: Union[str, Path],
    limited_area_path: Optional[Union[str, Path]] = None,
    verbose: int = 0,
    output_format: str = 'NETCDF3_64BIT_OFFSET',
) -> Tuple[str, str]:
    """
    Create a regional MPAS mesh using the MPAS Limited-Area Python API directly.

    This method imports and uses the LimitedArea class directly rather than
    calling the command-line script. This is more efficient for integration.

    Parameters
    ----------
    pts_file : str or Path
        Path to the points specification file (.pts).
    global_grid_file : str or Path
        Path to the global MPAS grid file (.nc).
    limited_area_path : str or Path, optional
        Path to the MPAS-Limited-Area directory.
    verbose : int, optional
        Verbosity level (0-5). Default is 0.
    output_format : str, optional
        NetCDF format. Use 'NETCDF3_64BIT_DATA' for large regions (>2M cells).

    Returns
    -------
    tuple
        (regional_grid_file, graph_file) paths.
    """
    pts_file = Path(pts_file).resolve()
    global_grid_file = Path(global_grid_file).resolve()

    if not pts_file.exists():
        raise FileNotFoundError(f"Points file not found: {pts_file}")
    if not global_grid_file.exists():
        raise FileNotFoundError(f"Global grid file not found: {global_grid_file}")

    # Find and add MPAS-Limited-Area to path
    if limited_area_path:
        limited_area_dir = Path(limited_area_path)
    else:
        search_paths = [
            Path(__file__).parent.parent.parent.parent / 'MPAS-Limited-Area',
            Path.cwd() / 'MPAS-Limited-Area',
            Path.home() / 'MPAS-Limited-Area',
        ]

        limited_area_dir = None
        for p in search_paths:
            if p.exists() and (p / 'limited_area').exists():
                limited_area_dir = p
                break

        if limited_area_dir is None:
            raise FileNotFoundError(
                "MPAS-Limited-Area not found. Please clone it from "
                "https://github.com/MiCurry/MPAS-Limited-Area.git"
            )

    # Add to Python path
    if str(limited_area_dir) not in sys.path:
        sys.path.insert(0, str(limited_area_dir))

    # Change to output directory
    original_cwd = os.getcwd()
    os.chdir(pts_file.parent)

    try:
        from limited_area.limited_area import LimitedArea

        kwargs = {'DEBUG': verbose}

        regional_area = LimitedArea(
            str(global_grid_file),
            str(pts_file),
            plotting=False,
            format=output_format,
            **kwargs
        )

        regional_grid, graph_file = regional_area.gen_region(**kwargs)

        return str(pts_file.parent / regional_grid), str(pts_file.parent / graph_file)

    finally:
        os.chdir(original_cwd)


def plot_region(
    pts_file: Union[str, Path],
    limited_area_path: Optional[Union[str, Path]] = None,
) -> None:
    """
    Generate a plot of the specified region without creating a mesh.

    This is useful for visualizing and verifying the region specification
    before running the full mesh creation.

    Parameters
    ----------
    pts_file : str or Path
        Path to the points specification file (.pts).
    limited_area_path : str or Path, optional
        Path to the MPAS-Limited-Area directory.
    """
    create_regional_mesh(
        pts_file=pts_file,
        global_grid_file='',  # Not used for plot_only
        limited_area_path=limited_area_path,
        plot_only=True,
    )


def partition_mesh(
    graph_file: Union[str, Path],
    num_partitions: int,
    gpmetis_path: Optional[str] = None,
    minconn: bool = True,
    contig: bool = True,
    niter: int = 200,
) -> Path:
    """
    Partition a mesh graph using METIS (gpmetis) for parallel MPAS/MONAN execution.

    This function calls gpmetis to partition the mesh graph file (.graph.info)
    generated by the MPAS Limited-Area tool. The output is a partition file
    that MPAS/MONAN uses to distribute cells across MPI processes.

    Parameters
    ----------
    graph_file : str or Path
        Path to the graph file (.graph.info) generated by create_regional_mesh.
    num_partitions : int
        Number of partitions (typically equal to the number of MPI processes).
    gpmetis_path : str, optional
        Path to the gpmetis executable. If not provided, searches in PATH.
    minconn : bool, optional
        Minimize connectivity between partitions. Default True.
    contig : bool, optional
        Force contiguous partitions. Default True.
    niter : int, optional
        Number of refinement iterations. Default 200.

    Returns
    -------
    Path
        Path to the generated partition file (.graph.info.part.N).

    Raises
    ------
    FileNotFoundError
        If graph_file or gpmetis is not found.
    subprocess.CalledProcessError
        If gpmetis execution fails.
    ValueError
        If num_partitions < 2.

    Examples
    --------
    >>> # Partition for 64 MPI processes
    >>> partition_file = partition_mesh(
    ...     'output/goias_regional.graph.info',
    ...     num_partitions=64
    ... )
    >>> print(partition_file)
    output/goias_regional.graph.info.part.64

    Notes
    -----
    The gpmetis options used are:
    - -minconn: Minimize the maximum degree of the subdomain graph
    - -contig: Force contiguous partitions
    - -niter=N: Number of iterations for refinement algorithms

    For MPAS/MONAN, use the partition file with:
        mpirun -np 64 ./atmosphere_model
    The model will look for the .graph.info.part.64 file automatically.
    """
    graph_file = Path(graph_file).resolve()

    if not graph_file.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_file}")

    if num_partitions < 2:
        raise ValueError(f"num_partitions must be >= 2, got {num_partitions}")

    # Find gpmetis executable
    if gpmetis_path:
        gpmetis = gpmetis_path
    else:
        # Search in PATH and common locations
        import shutil
        gpmetis = shutil.which('gpmetis')

        if gpmetis is None:
            # Try common conda/local locations
            search_paths = [
                Path.home() / 'local' / 'bin' / 'gpmetis',
                Path.home() / 'miniconda3' / 'bin' / 'gpmetis',
                Path.home() / 'anaconda3' / 'bin' / 'gpmetis',
                Path('/usr/local/bin/gpmetis'),
                Path('/usr/bin/gpmetis'),
            ]
            for p in search_paths:
                if p.exists():
                    gpmetis = str(p)
                    break

        if gpmetis is None:
            raise FileNotFoundError(
                "gpmetis not found. Install METIS with:\n"
                "  conda install -c conda-forge metis\n"
                "or provide the path via gpmetis_path parameter."
            )

    # Build command
    cmd = [gpmetis]

    if minconn:
        cmd.append('-minconn')
    if contig:
        cmd.append('-contig')
    if niter > 0:
        cmd.append(f'-niter={niter}')

    cmd.append(str(graph_file))
    cmd.append(str(num_partitions))

    print(f"Partitioning mesh into {num_partitions} partitions...")
    print(f"Running: {' '.join(cmd)}")

    # Execute gpmetis
    result = subprocess.run(
        cmd,
        cwd=str(graph_file.parent),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

    # Print gpmetis output
    if result.stdout:
        # Extract key statistics from output
        for line in result.stdout.split('\n'):
            if any(key in line.lower() for key in ['partitioning', 'edgecut', 'balance', 'timing']):
                print(f"  {line.strip()}")

    # Output file is: graph_file.part.N
    partition_file = Path(f"{graph_file}.part.{num_partitions}")

    if not partition_file.exists():
        raise FileNotFoundError(
            f"Expected partition file not created: {partition_file}\n"
            f"gpmetis output: {result.stdout}"
        )

    print(f"Partition file created: {partition_file}")

    return partition_file


def run_full_pipeline(
    pts_file: Union[str, Path],
    global_grid_file: Union[str, Path],
    num_partitions: int,
    limited_area_path: Optional[Union[str, Path]] = None,
    gpmetis_path: Optional[str] = None,
    verbose: int = 0,
) -> dict:
    """
    Run the complete regional mesh pipeline: cut + partition.

    This function combines the MPAS Limited-Area mesh cutting and METIS
    partitioning into a single workflow for convenience.

    Parameters
    ----------
    pts_file : str or Path
        Path to the points specification file (.pts).
    global_grid_file : str or Path
        Path to the global MPAS grid file (.nc).
    num_partitions : int
        Number of partitions for parallel execution.
    limited_area_path : str or Path, optional
        Path to the MPAS-Limited-Area directory.
    gpmetis_path : str, optional
        Path to the gpmetis executable.
    verbose : int, optional
        Verbosity level (0-5). Default is 0.

    Returns
    -------
    dict
        Dictionary with paths to output files:
        - 'regional_grid': Path to the regional mesh NetCDF file
        - 'graph_file': Path to the graph info file
        - 'partition_file': Path to the partition file

    Examples
    --------
    >>> results = run_full_pipeline(
    ...     pts_file='goias.pts',
    ...     global_grid_file='x1.40962.grid.nc',
    ...     num_partitions=64,
    ... )
    >>> print(results['regional_grid'])
    goias.grid.nc
    >>> print(results['partition_file'])
    goias.graph.info.part.64
    """
    print("=" * 70)
    print("MPAS/MONAN Regional Mesh Pipeline")
    print("=" * 70)

    # Step 1: Cut regional mesh
    print("\n" + "-" * 40)
    print("Step 1: Cutting regional mesh from global grid")
    print("-" * 40)

    regional_grid, graph_file = create_regional_mesh_python(
        pts_file=pts_file,
        global_grid_file=global_grid_file,
        limited_area_path=limited_area_path,
        verbose=verbose,
    )

    print(f"  Regional grid: {regional_grid}")
    print(f"  Graph file: {graph_file}")

    # Step 2: Partition mesh
    print("\n" + "-" * 40)
    print(f"Step 2: Partitioning mesh into {num_partitions} parts")
    print("-" * 40)

    partition_file = partition_mesh(
        graph_file=graph_file,
        num_partitions=num_partitions,
        gpmetis_path=gpmetis_path,
    )

    # Summary
    print("\n" + "=" * 70)
    print("Pipeline Complete")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  Regional mesh:   {regional_grid}")
    print(f"  Graph file:      {graph_file}")
    print(f"  Partition file:  {partition_file}")
    print(f"\nTo run MPAS/MONAN with {num_partitions} processes:")
    print(f"  mpirun -np {num_partitions} ./atmosphere_model")

    return {
        'regional_grid': regional_grid,
        'graph_file': graph_file,
        'partition_file': str(partition_file),
    }
