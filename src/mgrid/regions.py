"""
Refinement regions for variable-resolution MPAS/MONAN grids.

This module provides classes and functions for defining regions with
different mesh resolutions, including circular and polygonal areas
with smooth transition zones.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union

from .geometry import haversine_distance, EARTH_RADIUS_KM


@dataclass
class Region(ABC):
    """
    Abstract base class for refinement regions.

    Attributes
    ----------
    name : str
        Human-readable region name.
    resolution : float
        Target resolution inside the region (km).
    transition_width : float
        Width of transition zone from region edge to background (km).
    """
    name: str
    resolution: float
    transition_width: float

    @abstractmethod
    def contains(
        self,
        lons: np.ndarray,
        lats: np.ndarray
    ) -> np.ndarray:
        """
        Check which points are inside the region.

        Parameters
        ----------
        lons : ndarray
            2D array of longitudes.
        lats : ndarray
            2D array of latitudes.

        Returns
        -------
        mask : ndarray
            Boolean array, True where points are inside.
        """
        pass

    @abstractmethod
    def distance_to_boundary(
        self,
        lons: np.ndarray,
        lats: np.ndarray
    ) -> np.ndarray:
        """
        Calculate distance from points to region boundary.

        Parameters
        ----------
        lons : ndarray
            2D array of longitudes.
        lats : ndarray
            2D array of latitudes.

        Returns
        -------
        distances : ndarray
            Distance to boundary in km (negative inside, positive outside).
        """
        pass


@dataclass
class CircularRegion(Region):
    """
    Circular refinement region defined by center point and radius.

    Attributes
    ----------
    center : tuple
        Center coordinates as (latitude, longitude) in degrees.
    radius : float
        Radius of the high-resolution area in km.
    """
    center: Tuple[float, float] = (0.0, 0.0)
    radius: float = 100.0

    def contains(
        self,
        lons: np.ndarray,
        lats: np.ndarray
    ) -> np.ndarray:
        """Check if points are inside the circular region."""
        center_lat, center_lon = self.center
        distances = haversine_distance(lons, lats, center_lon, center_lat)
        return distances <= self.radius

    def distance_to_boundary(
        self,
        lons: np.ndarray,
        lats: np.ndarray
    ) -> np.ndarray:
        """Calculate distance to circle boundary (negative inside)."""
        center_lat, center_lon = self.center
        distances = haversine_distance(lons, lats, center_lon, center_lat)
        return distances - self.radius


@dataclass
class PolygonRegion(Region):
    """
    Polygonal refinement region defined by vertex coordinates.

    Attributes
    ----------
    vertices : list
        List of (latitude, longitude) tuples defining the polygon vertices.
        The polygon is automatically closed.
    """
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    _polygon: object = field(default=None, repr=False, init=False)

    def __post_init__(self):
        """Initialize shapely polygon for geometric operations."""
        try:
            from shapely.geometry import Polygon
            # Convert (lat, lon) to (lon, lat) for shapely
            coords = [(v[1], v[0]) for v in self.vertices]
            self._polygon = Polygon(coords)
        except ImportError:
            self._polygon = None

    def contains(
        self,
        lons: np.ndarray,
        lats: np.ndarray
    ) -> np.ndarray:
        """Check if points are inside the polygon."""
        if self._polygon is None:
            raise ImportError(
                "shapely is required for polygon regions. "
                "Install with: pip install shapely"
            )

        from shapely.geometry import Point

        original_shape = lons.shape
        lon_flat = lons.flatten()
        lat_flat = lats.flatten()

        inside = np.zeros(len(lon_flat), dtype=bool)

        for i, (lo, la) in enumerate(zip(lon_flat, lat_flat)):
            point = Point(lo, la)
            inside[i] = self._polygon.contains(point)

        return inside.reshape(original_shape)

    def distance_to_boundary(
        self,
        lons: np.ndarray,
        lats: np.ndarray
    ) -> np.ndarray:
        """
        Calculate distance to polygon boundary.

        Returns negative values inside, positive outside.
        Distance is approximate (based on degree-to-km conversion).
        """
        if self._polygon is None:
            raise ImportError(
                "shapely is required for polygon regions. "
                "Install with: pip install shapely"
            )

        from shapely.geometry import Point

        original_shape = lons.shape
        lon_flat = lons.flatten()
        lat_flat = lats.flatten()

        distances = np.zeros(len(lon_flat))
        inside = self.contains(lons, lats).flatten()

        # Approximate conversion: 1 degree ~ 111 km
        deg_to_km = 111.0

        for i, (lo, la) in enumerate(zip(lon_flat, lat_flat)):
            point = Point(lo, la)
            dist_deg = point.distance(self._polygon.boundary)
            dist_km = dist_deg * deg_to_km

            # Negative inside, positive outside
            if inside[i]:
                distances[i] = -dist_km
            else:
                distances[i] = dist_km

        return distances.reshape(original_shape)


def compute_cell_width(
    lons: np.ndarray,
    lats: np.ndarray,
    regions: List[Region],
    background_resolution: float = 150.0
) -> np.ndarray:
    """
    Compute cell width array based on refinement regions.

    The cell width at each point is determined by the finest resolution
    among all regions that contain or influence that point. Transition
    zones create smooth gradients between resolutions.

    Parameters
    ----------
    lons : ndarray
        2D array of longitudes.
    lats : ndarray
        2D array of latitudes.
    regions : list of Region
        List of refinement regions, processed from coarsest to finest.
    background_resolution : float, optional
        Resolution for areas outside all regions (km).

    Returns
    -------
    cell_width : ndarray
        2D array of cell widths in km.

    Notes
    -----
    Regions are processed from coarsest to finest resolution to allow
    proper nesting of refinement areas.
    """
    # Initialize with background resolution
    cell_width = np.full_like(lons, background_resolution, dtype=float)

    # Sort regions by resolution (coarsest first for proper nesting)
    sorted_regions = sorted(regions, key=lambda r: r.resolution, reverse=True)

    for region in sorted_regions:
        # Get region properties
        res = region.resolution
        trans_width = region.transition_width

        # Check which points are inside
        inside = region.contains(lons, lats)

        # Apply target resolution inside region
        cell_width[inside] = np.minimum(cell_width[inside], res)

        # Apply transition zone
        if trans_width > 0:
            dist_to_boundary = region.distance_to_boundary(lons, lats)

            # Transition zone: points outside region but within transition_width
            in_transition = (dist_to_boundary > 0) & (dist_to_boundary <= trans_width)

            # Linear interpolation from region resolution to current resolution
            if np.any(in_transition):
                fraction = dist_to_boundary[in_transition] / trans_width
                outer_res = cell_width[in_transition]
                new_res = res + fraction * (outer_res - res)
                cell_width[in_transition] = np.minimum(
                    cell_width[in_transition], new_res
                )

    return cell_width


def region_from_dict(config: dict) -> Region:
    """
    Create a Region object from a dictionary configuration.

    Parameters
    ----------
    config : dict
        Region configuration with keys:
        - 'name': str
        - 'type': 'circle' or 'polygon'
        - 'resolution': float (km)
        - 'transition_start': float (km) - resolution at transition start
        For circles:
        - 'center': [lat, lon]
        - 'radius': float (km)
        For polygons:
        - 'polygon': list of [lat, lon] pairs

    Returns
    -------
    region : Region
        CircularRegion or PolygonRegion instance.

    Examples
    --------
    >>> config = {
    ...     'name': 'MyRegion',
    ...     'type': 'circle',
    ...     'center': [-23.55, -46.63],
    ...     'radius': 100,
    ...     'resolution': 5,
    ...     'transition_start': 30
    ... }
    >>> region = region_from_dict(config)
    """
    name = config.get('name', 'Unnamed')
    resolution = config['resolution']

    # Transition width is the difference between transition_start and resolution
    transition_start = config.get('transition_start', resolution)
    transition_width = transition_start - resolution

    region_type = config['type'].lower()

    if region_type == 'circle':
        center = tuple(config['center'])
        radius = config['radius']
        return CircularRegion(
            name=name,
            resolution=resolution,
            transition_width=transition_width,
            center=center,
            radius=radius
        )

    elif region_type == 'polygon':
        vertices = [tuple(v) for v in config['polygon']]
        return PolygonRegion(
            name=name,
            resolution=resolution,
            transition_width=transition_width,
            vertices=vertices
        )

    else:
        raise ValueError(f"Unknown region type: {region_type}")


def regions_from_config(config: dict) -> Tuple[List[Region], float]:
    """
    Create Region objects from a full configuration dictionary.

    Parameters
    ----------
    config : dict
        Full configuration with 'regions' list and optional
        'background_resolution'.

    Returns
    -------
    regions : list of Region
        List of Region objects.
    background_resolution : float
        Background resolution in km.
    """
    regions = [region_from_dict(r) for r in config['regions']]
    background_res = config.get('background_resolution', 150.0)

    return regions, background_res
