"""
Visualization utilities for MPAS/MONAN grids.

This module provides functions for visualizing cell width functions,
mesh resolution distributions, and region boundaries.
"""

from pathlib import Path
from typing import List, Optional, Union, Tuple

import numpy as np


def plot_cell_width(
    cell_width: np.ndarray,
    lon: np.ndarray,
    lat: np.ndarray,
    regions: Optional[List] = None,
    title: str = "Grid Resolution Distribution",
    output_file: Optional[Union[str, Path]] = None,
    show: bool = True,
    figsize: Tuple[int, int] = (14, 6),
    cmap: str = 'viridis'
) -> None:
    """
    Create diagnostic plots for cell width distribution.

    Generates a two-panel figure showing:
    1. Spatial distribution of cell width (map view)
    2. Histogram of cell width values

    Parameters
    ----------
    cell_width : ndarray
        2D array of cell widths (nlat x nlon).
    lon : ndarray
        1D array of longitudes.
    lat : ndarray
        1D array of latitudes.
    regions : list of Region, optional
        List of regions to overlay on the map.
    title : str, optional
        Plot title.
    output_file : str or Path, optional
        Path to save figure. If None, figure is not saved.
    show : bool, optional
        Whether to display the figure (default: True).
    figsize : tuple, optional
        Figure size in inches (width, height).
    cmap : str, optional
        Colormap for cell width display.

    Notes
    -----
    Requires matplotlib. Install with: pip install matplotlib
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install matplotlib"
        )

    # Create 2D meshgrid
    lons, lats = np.meshgrid(lon, lat)

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Panel 1: Spatial distribution
    ax1 = axes[0]
    levels = 50
    h = ax1.contourf(lons, lats, cell_width, levels=levels, cmap=cmap)
    plt.colorbar(h, ax=ax1, label='Cell Width (km)')
    ax1.set_xlabel('Longitude (degrees)')
    ax1.set_ylabel('Latitude (degrees)')
    ax1.set_title(title)

    # Overlay region boundaries if provided
    if regions is not None:
        _plot_region_boundaries(ax1, regions)

    ax1.set_aspect('equal')

    # Panel 2: Histogram
    ax2 = axes[1]
    ax2.hist(cell_width.flatten(), bins=100, edgecolor='black', alpha=0.7)
    ax2.set_xlabel('Cell Width (km)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Resolution Distribution')
    ax2.set_yscale('log')

    # Add statistics
    stats_text = (
        f"Min: {np.min(cell_width):.1f} km\n"
        f"Max: {np.max(cell_width):.1f} km\n"
        f"Mean: {np.mean(cell_width):.1f} km"
    )
    ax2.text(
        0.95, 0.95, stats_text,
        transform=ax2.transAxes,
        verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )

    plt.tight_layout()

    if output_file is not None:
        output_path = Path(output_file)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Figure saved to: {output_path}")

    if show:
        plt.show()
    else:
        plt.close()


def _plot_region_boundaries(ax, regions: List) -> None:
    """Plot region boundaries on an axis."""
    from .regions import CircularRegion, PolygonRegion

    for region in regions:
        label = getattr(region, 'name', 'Region')

        if isinstance(region, CircularRegion):
            center_lat, center_lon = region.center
            ax.plot(
                center_lon, center_lat, 'r*',
                markersize=15,
                label=f"{label} (center)"
            )

            # Draw circle approximation
            theta = np.linspace(0, 2 * np.pi, 100)
            # Approximate radius in degrees
            radius_deg = region.radius / 111.0
            circle_lon = center_lon + radius_deg * np.cos(theta)
            circle_lat = center_lat + radius_deg * np.sin(theta)
            ax.plot(circle_lon, circle_lat, 'r--', linewidth=1.5)

        elif isinstance(region, PolygonRegion):
            vertices = region.vertices
            poly_lons = [v[1] for v in vertices] + [vertices[0][1]]
            poly_lats = [v[0] for v in vertices] + [vertices[0][0]]
            ax.plot(
                poly_lons, poly_lats, 'r-',
                linewidth=2,
                label=label
            )

    ax.legend(loc='upper right')


def plot_region_overview(
    regions: List,
    background_resolution: float = 150.0,
    lat_bounds: Tuple[float, float] = (-90, 90),
    lon_bounds: Tuple[float, float] = (-180, 180),
    output_file: Optional[Union[str, Path]] = None,
    show: bool = True
) -> None:
    """
    Create an overview plot of refinement regions.

    Parameters
    ----------
    regions : list of Region
        List of refinement regions.
    background_resolution : float, optional
        Background resolution in km.
    lat_bounds : tuple, optional
        Latitude bounds for plot.
    lon_bounds : tuple, optional
        Longitude bounds for plot.
    output_file : str or Path, optional
        Path to save figure.
    show : bool, optional
        Whether to display the figure.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install matplotlib"
        )

    from .regions import CircularRegion, PolygonRegion

    fig, ax = plt.subplots(figsize=(12, 8))

    colors = plt.cm.Set1(np.linspace(0, 1, len(regions)))

    for i, region in enumerate(regions):
        color = colors[i]
        label = f"{region.name} ({region.resolution:.0f} km)"

        if isinstance(region, CircularRegion):
            center_lat, center_lon = region.center
            radius_deg = region.radius / 111.0

            # Draw filled circle
            circle = plt.Circle(
                (center_lon, center_lat),
                radius_deg,
                color=color,
                alpha=0.3,
                label=label
            )
            ax.add_patch(circle)

            # Draw transition zone
            trans_radius = (region.radius + region.transition_width) / 111.0
            trans_circle = plt.Circle(
                (center_lon, center_lat),
                trans_radius,
                color=color,
                alpha=0.1,
                linestyle='--',
                fill=False
            )
            ax.add_patch(trans_circle)

            ax.plot(center_lon, center_lat, 'k*', markersize=10)

        elif isinstance(region, PolygonRegion):
            vertices = region.vertices
            poly_coords = [(v[1], v[0]) for v in vertices]

            polygon = mpatches.Polygon(
                poly_coords,
                closed=True,
                color=color,
                alpha=0.3,
                label=label
            )
            ax.add_patch(polygon)

            # Draw boundary
            poly_lons = [v[1] for v in vertices] + [vertices[0][1]]
            poly_lats = [v[0] for v in vertices] + [vertices[0][0]]
            ax.plot(poly_lons, poly_lats, color=color, linewidth=2)

    ax.set_xlim(lon_bounds)
    ax.set_ylim(lat_bounds)
    ax.set_xlabel('Longitude (degrees)')
    ax.set_ylabel('Latitude (degrees)')
    ax.set_title(f'Refinement Regions (Background: {background_resolution:.0f} km)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')

    plt.tight_layout()

    if output_file is not None:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Figure saved to: {output_file}")

    if show:
        plt.show()
    else:
        plt.close()
