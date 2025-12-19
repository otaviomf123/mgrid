"""
Spherical geometry utilities for MPAS/MONAN grid generation.

This module provides functions for calculating distances and geometric
operations on the sphere, essential for variable-resolution mesh generation.
"""

import numpy as np
from typing import Tuple, Union

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0

# Earth radius in meters
EARTH_RADIUS_M = 6371.0e3


def haversine_distance(
    lon1: Union[float, np.ndarray],
    lat1: Union[float, np.ndarray],
    lon2: float,
    lat2: float,
    radius: float = EARTH_RADIUS_KM
) -> Union[float, np.ndarray]:
    """
    Calculate great circle distance between points using the Haversine formula.

    The Haversine formula determines the shortest distance over the Earth's
    surface between two points specified by latitude and longitude.

    Parameters
    ----------
    lon1 : float or ndarray
        Longitude of point(s) in degrees.
    lat1 : float or ndarray
        Latitude of point(s) in degrees.
    lon2 : float
        Longitude of center point in degrees.
    lat2 : float
        Latitude of center point in degrees.
    radius : float, optional
        Sphere radius. Default is Earth radius in km.

    Returns
    -------
    distance : float or ndarray
        Great circle distance(s) in same units as radius.

    Examples
    --------
    >>> haversine_distance(-46.63, -23.55, -43.17, -22.91)  # SP to RJ
    357.89...
    """
    # Convert degrees to radians
    lon1_rad = np.radians(lon1)
    lat1_rad = np.radians(lat1)
    lon2_rad = np.radians(lon2)
    lat2_rad = np.radians(lat2)

    # Haversine formula
    dlat = lat1_rad - lat2_rad
    dlon = lon1_rad - lon2_rad

    a = np.sin(dlat / 2.0) ** 2 + \
        np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2.0) ** 2

    distance = 2.0 * radius * np.arcsin(np.sqrt(a))

    return distance


def degrees_to_km(degrees: float, latitude: float = 0.0) -> float:
    """
    Convert angular distance in degrees to kilometers.

    At the equator, 1 degree is approximately 111 km. This decreases
    with latitude due to meridian convergence.

    Parameters
    ----------
    degrees : float
        Angular distance in degrees.
    latitude : float, optional
        Reference latitude for longitude conversion (default: 0).

    Returns
    -------
    km : float
        Distance in kilometers.

    Notes
    -----
    For latitude distances, the conversion is constant (~111 km/degree).
    For longitude distances, it varies with latitude.
    """
    km_per_degree = 2.0 * np.pi * EARTH_RADIUS_KM / 360.0  # ~111 km

    if latitude != 0.0:
        # Adjust for latitude (longitude circles are smaller)
        km_per_degree *= np.cos(np.radians(latitude))

    return degrees * km_per_degree


def km_to_degrees(km: float, latitude: float = 0.0) -> float:
    """
    Convert distance in kilometers to angular degrees.

    Parameters
    ----------
    km : float
        Distance in kilometers.
    latitude : float, optional
        Reference latitude for accurate conversion (default: 0).

    Returns
    -------
    degrees : float
        Angular distance in degrees.
    """
    km_per_degree = 2.0 * np.pi * EARTH_RADIUS_KM / 360.0

    if latitude != 0.0:
        km_per_degree *= np.cos(np.radians(latitude))

    return km / km_per_degree


def create_latlon_grid(
    resolution_km: float,
    density_factor: float = 0.001,
    lat_bounds: Tuple[float, float] = (-90.0, 90.0),
    lon_bounds: Tuple[float, float] = (-180.0, 180.0)
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Create a regular latitude-longitude grid for cell width specification.

    Parameters
    ----------
    resolution_km : float
        Target resolution in kilometers (used to compute grid spacing).
    density_factor : float, optional
        Fraction of resolution for grid spacing (default: 0.001).
        Smaller values create denser grids.
    lat_bounds : tuple, optional
        Latitude bounds (min, max) in degrees.
    lon_bounds : tuple, optional
        Longitude bounds (min, max) in degrees.

    Returns
    -------
    lon : ndarray
        1D array of longitudes.
    lat : ndarray
        1D array of latitudes.
    lons : ndarray
        2D meshgrid of longitudes.
    lats : ndarray
        2D meshgrid of latitudes.
    """
    # Grid spacing in degrees
    dlat = resolution_km * density_factor
    dlon = dlat

    # Number of grid points
    nlat = int((lat_bounds[1] - lat_bounds[0]) / dlat) + 1
    nlon = int((lon_bounds[1] - lon_bounds[0]) / dlon) + 1

    # Create 1D coordinate arrays
    lat = np.linspace(lat_bounds[0], lat_bounds[1], nlat)
    lon = np.linspace(lon_bounds[0], lon_bounds[1], nlon)

    # Create 2D meshgrids
    lons, lats = np.meshgrid(lon, lat)

    return lon, lat, lons, lats


def spherical_to_cartesian(
    lon: Union[float, np.ndarray],
    lat: Union[float, np.ndarray],
    radius: float = 1.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert spherical coordinates to Cartesian coordinates.

    Parameters
    ----------
    lon : float or ndarray
        Longitude in degrees.
    lat : float or ndarray
        Latitude in degrees.
    radius : float, optional
        Sphere radius (default: 1.0 for unit sphere).

    Returns
    -------
    x, y, z : ndarray
        Cartesian coordinates.
    """
    lon_rad = np.radians(lon)
    lat_rad = np.radians(lat)

    x = radius * np.cos(lat_rad) * np.cos(lon_rad)
    y = radius * np.cos(lat_rad) * np.sin(lon_rad)
    z = radius * np.sin(lat_rad)

    return x, y, z


def cartesian_to_spherical(
    x: Union[float, np.ndarray],
    y: Union[float, np.ndarray],
    z: Union[float, np.ndarray]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert Cartesian coordinates to spherical coordinates.

    Parameters
    ----------
    x, y, z : float or ndarray
        Cartesian coordinates.

    Returns
    -------
    lon : ndarray
        Longitude in degrees.
    lat : ndarray
        Latitude in degrees.
    radius : ndarray
        Radial distance.
    """
    radius = np.sqrt(x**2 + y**2 + z**2)
    lat = np.degrees(np.arcsin(z / radius))
    lon = np.degrees(np.arctan2(y, x))

    return lon, lat, radius


def icosahedral_resolution(level: int) -> float:
    """
    Calculate approximate resolution of an icosahedral grid at a given level.

    The icosahedral grid is recursively subdivided. Each level roughly
    doubles the number of cells and halves the resolution.

    Parameters
    ----------
    level : int
        Refinement level (0 = base icosahedron with 20 faces).

    Returns
    -------
    resolution_km : float
        Approximate cell size in kilometers.

    Notes
    -----
    Level 0: ~7,000 km (20 cells)
    Level 4: ~240 km (~10,000 cells)
    Level 7: ~30 km (~650,000 cells)
    Level 10: ~4 km (~40,000,000 cells)
    """
    # Base icosahedron edge length in km (approximation)
    base_resolution = 7054.0  # km (edge of spherical icosahedron)

    # Each level subdivides edges, roughly halving resolution
    resolution = base_resolution / (2 ** level)

    return resolution


def level_for_resolution(target_resolution_km: float) -> int:
    """
    Calculate the icosahedral refinement level for a target resolution.

    Parameters
    ----------
    target_resolution_km : float
        Desired resolution in kilometers.

    Returns
    -------
    level : int
        Recommended refinement level.
    """
    base_resolution = 7054.0

    # Solve: target = base / 2^level
    level = np.log2(base_resolution / target_resolution_km)

    return int(np.ceil(level))
