"""Tests for the geometry module."""

import numpy as np
import pytest

from m_grid.geometry import (
    haversine_distance,
    degrees_to_km,
    km_to_degrees,
    spherical_to_cartesian,
    cartesian_to_spherical,
    create_latlon_grid,
    icosahedral_resolution,
    level_for_resolution,
    EARTH_RADIUS_KM,
)


class TestHaversineDistance:
    """Tests for haversine_distance function."""

    def test_zero_distance(self):
        """Same point should have zero distance."""
        dist = haversine_distance(0.0, 0.0, 0.0, 0.0)
        assert dist == pytest.approx(0.0, abs=1e-10)

    def test_known_distance(self):
        """Test against known distance (SP to RJ ~360 km)."""
        # Sao Paulo to Rio de Janeiro
        sp_lon, sp_lat = -46.63, -23.55
        rj_lon, rj_lat = -43.17, -22.91

        dist = haversine_distance(sp_lon, sp_lat, rj_lon, rj_lat)

        # Actual distance is approximately 358 km
        assert 350 < dist < 370

    def test_antipodal_points(self):
        """Antipodal points should be ~20,000 km apart."""
        dist = haversine_distance(0.0, 0.0, 180.0, 0.0)
        expected = np.pi * EARTH_RADIUS_KM  # Half circumference

        assert dist == pytest.approx(expected, rel=1e-6)

    def test_array_input(self):
        """Function should handle array inputs."""
        lons = np.array([0.0, 90.0, -90.0])
        lats = np.array([0.0, 0.0, 0.0])

        dists = haversine_distance(lons, lats, 0.0, 0.0)

        assert len(dists) == 3
        assert dists[0] == pytest.approx(0.0, abs=1e-10)

    def test_equator_quarter(self):
        """Quarter around equator should be ~10,000 km."""
        dist = haversine_distance(90.0, 0.0, 0.0, 0.0)
        quarter_circumference = np.pi * EARTH_RADIUS_KM / 2

        assert dist == pytest.approx(quarter_circumference, rel=1e-6)


class TestDegreesKmConversion:
    """Tests for degree/km conversion functions."""

    def test_degrees_to_km_equator(self):
        """1 degree at equator should be ~111 km."""
        km = degrees_to_km(1.0, latitude=0.0)
        assert 110 < km < 112

    def test_km_to_degrees_equator(self):
        """111 km at equator should be ~1 degree."""
        deg = km_to_degrees(111.0, latitude=0.0)
        assert 0.99 < deg < 1.01

    def test_roundtrip(self):
        """Converting back and forth should be identity."""
        original = 5.0
        km = degrees_to_km(original)
        back = km_to_degrees(km)

        assert back == pytest.approx(original, rel=1e-10)

    def test_latitude_effect(self):
        """Degrees to km should be less at higher latitudes."""
        km_equator = degrees_to_km(1.0, latitude=0.0)
        km_60deg = degrees_to_km(1.0, latitude=60.0)

        # At 60 degrees, should be half
        assert km_60deg == pytest.approx(km_equator / 2, rel=0.01)


class TestCoordinateConversion:
    """Tests for spherical/Cartesian coordinate conversion."""

    def test_origin(self):
        """Point at (0, 0) should be on positive x-axis."""
        x, y, z = spherical_to_cartesian(0.0, 0.0)

        assert x == pytest.approx(1.0, rel=1e-10)
        assert y == pytest.approx(0.0, abs=1e-10)
        assert z == pytest.approx(0.0, abs=1e-10)

    def test_north_pole(self):
        """North pole should be on positive z-axis."""
        x, y, z = spherical_to_cartesian(0.0, 90.0)

        assert x == pytest.approx(0.0, abs=1e-10)
        assert y == pytest.approx(0.0, abs=1e-10)
        assert z == pytest.approx(1.0, rel=1e-10)

    def test_roundtrip(self):
        """Converting back and forth should preserve coordinates."""
        lon_orig, lat_orig = -46.63, -23.55

        x, y, z = spherical_to_cartesian(lon_orig, lat_orig)
        lon_back, lat_back, r = cartesian_to_spherical(x, y, z)

        assert lon_back == pytest.approx(lon_orig, rel=1e-10)
        assert lat_back == pytest.approx(lat_orig, rel=1e-10)
        assert r == pytest.approx(1.0, rel=1e-10)

    def test_array_input(self):
        """Should handle array inputs."""
        lons = np.array([0.0, 90.0, 180.0])
        lats = np.array([0.0, 0.0, 0.0])

        x, y, z = spherical_to_cartesian(lons, lats)

        assert len(x) == 3
        assert x[0] == pytest.approx(1.0, rel=1e-10)
        assert y[1] == pytest.approx(1.0, rel=1e-10)
        assert x[2] == pytest.approx(-1.0, rel=1e-10)


class TestLatLonGrid:
    """Tests for create_latlon_grid function."""

    def test_grid_size(self):
        """Grid should have expected dimensions."""
        lon, lat, lons, lats = create_latlon_grid(100.0, density_factor=0.01)

        # With 100 km resolution and 0.01 density, dlat = 1 degree
        # 180/1 + 1 = 181 lat points, 360/1 + 1 = 361 lon points
        assert lat.shape[0] == 181
        assert lon.shape[0] == 361
        assert lons.shape == (181, 361)
        assert lats.shape == (181, 361)

    def test_bounds(self):
        """Grid should cover specified bounds."""
        lon, lat, _, _ = create_latlon_grid(
            50.0,
            lat_bounds=(-45, 45),
            lon_bounds=(-90, 90)
        )

        assert lat[0] == -45.0
        assert lat[-1] == 45.0
        assert lon[0] == -90.0
        assert lon[-1] == 90.0


class TestIcosahedralResolution:
    """Tests for icosahedral resolution calculations."""

    def test_level_0(self):
        """Level 0 should have ~7000 km resolution."""
        res = icosahedral_resolution(0)
        assert 6500 < res < 7500

    def test_level_decreases(self):
        """Higher levels should have finer resolution."""
        res_4 = icosahedral_resolution(4)
        res_6 = icosahedral_resolution(6)
        res_8 = icosahedral_resolution(8)

        assert res_4 > res_6 > res_8

    def test_level_halving(self):
        """Each level should roughly halve the resolution."""
        res_4 = icosahedral_resolution(4)
        res_5 = icosahedral_resolution(5)

        ratio = res_4 / res_5
        assert ratio == pytest.approx(2.0, rel=0.1)

    def test_level_for_resolution(self):
        """Should find appropriate level for target resolution."""
        level = level_for_resolution(30.0)

        # Level should give resolution <= 30 km
        res = icosahedral_resolution(level)
        assert res <= 30.0

    def test_roundtrip_level(self):
        """level_for_resolution should invert icosahedral_resolution."""
        for level in [4, 6, 8]:
            res = icosahedral_resolution(level)
            found_level = level_for_resolution(res)

            # Should find same or next level
            assert abs(found_level - level) <= 1
