"""Tests for the regions module."""

import numpy as np
import pytest

from m_grid.regions import (
    CircularRegion,
    PolygonRegion,
    compute_cell_width,
    region_from_dict,
    regions_from_config,
)


class TestCircularRegion:
    """Tests for CircularRegion class."""

    def test_creation(self):
        """Test basic region creation."""
        region = CircularRegion(
            name='TestRegion',
            resolution=5.0,
            transition_width=20.0,
            center=(-23.0, -46.0),
            radius=100.0
        )

        assert region.name == 'TestRegion'
        assert region.resolution == 5.0
        assert region.transition_width == 20.0
        assert region.center == (-23.0, -46.0)
        assert region.radius == 100.0

    def test_contains_center(self):
        """Center point should be inside region."""
        region = CircularRegion(
            name='Test',
            resolution=5.0,
            transition_width=20.0,
            center=(0.0, 0.0),
            radius=100.0
        )

        lons = np.array([[0.0]])
        lats = np.array([[0.0]])

        inside = region.contains(lons, lats)
        assert inside[0, 0] == True

    def test_contains_far_point(self):
        """Point far from center should be outside."""
        region = CircularRegion(
            name='Test',
            resolution=5.0,
            transition_width=20.0,
            center=(0.0, 0.0),
            radius=100.0
        )

        # Point ~1000 km away
        lons = np.array([[10.0]])
        lats = np.array([[0.0]])

        inside = region.contains(lons, lats)
        assert inside[0, 0] == False

    def test_distance_to_boundary(self):
        """Test distance calculation."""
        region = CircularRegion(
            name='Test',
            resolution=5.0,
            transition_width=20.0,
            center=(0.0, 0.0),
            radius=111.0  # ~1 degree at equator
        )

        # Center should have negative distance (inside)
        lons = np.array([[0.0]])
        lats = np.array([[0.0]])
        dist = region.distance_to_boundary(lons, lats)
        assert dist[0, 0] < 0

        # Point outside should have positive distance
        lons = np.array([[5.0]])
        lats = np.array([[0.0]])
        dist = region.distance_to_boundary(lons, lats)
        assert dist[0, 0] > 0


class TestPolygonRegion:
    """Tests for PolygonRegion class."""

    @pytest.fixture
    def square_region(self):
        """Create a simple square region for testing."""
        return PolygonRegion(
            name='Square',
            resolution=5.0,
            transition_width=20.0,
            vertices=[
                (-10.0, -10.0),
                (-10.0, 10.0),
                (10.0, 10.0),
                (10.0, -10.0),
            ]
        )

    def test_creation(self, square_region):
        """Test polygon region creation."""
        assert square_region.name == 'Square'
        assert len(square_region.vertices) == 4

    def test_contains_center(self, square_region):
        """Center of polygon should be inside."""
        lons = np.array([[0.0]])
        lats = np.array([[0.0]])

        inside = square_region.contains(lons, lats)
        assert inside[0, 0] == True

    def test_contains_outside(self, square_region):
        """Point outside polygon should not be contained."""
        lons = np.array([[50.0]])
        lats = np.array([[50.0]])

        inside = square_region.contains(lons, lats)
        assert inside[0, 0] == False

    def test_contains_edge(self, square_region):
        """Point on edge behavior."""
        # Point just inside
        lons = np.array([[5.0]])
        lats = np.array([[5.0]])

        inside = square_region.contains(lons, lats)
        assert inside[0, 0] == True


class TestComputeCellWidth:
    """Tests for compute_cell_width function."""

    def test_uniform_without_regions(self):
        """Without regions, should return background resolution."""
        lons, lats = np.meshgrid(
            np.linspace(-10, 10, 21),
            np.linspace(-10, 10, 21)
        )

        cell_width = compute_cell_width(lons, lats, [], background_resolution=100.0)

        assert np.all(cell_width == 100.0)

    def test_single_circular_region(self):
        """Test with a single circular region."""
        region = CircularRegion(
            name='Test',
            resolution=5.0,
            transition_width=20.0,
            center=(0.0, 0.0),
            radius=100.0
        )

        lons, lats = np.meshgrid(
            np.linspace(-5, 5, 11),
            np.linspace(-5, 5, 11)
        )

        cell_width = compute_cell_width(
            lons, lats, [region], background_resolution=100.0
        )

        # Center should have fine resolution
        center_idx = 5
        assert cell_width[center_idx, center_idx] == 5.0

        # Min should be region resolution
        assert np.min(cell_width) == 5.0

        # Max should be background or transition
        assert np.max(cell_width) <= 100.0

    def test_nested_regions(self):
        """Test with nested regions."""
        outer = CircularRegion(
            name='Outer',
            resolution=20.0,
            transition_width=30.0,
            center=(0.0, 0.0),
            radius=500.0
        )

        inner = CircularRegion(
            name='Inner',
            resolution=5.0,
            transition_width=10.0,
            center=(0.0, 0.0),
            radius=100.0
        )

        lons, lats = np.meshgrid(
            np.linspace(-3, 3, 7),
            np.linspace(-3, 3, 7)
        )

        cell_width = compute_cell_width(
            lons, lats, [outer, inner], background_resolution=150.0
        )

        # Center should have finest resolution
        center_idx = 3
        assert cell_width[center_idx, center_idx] == 5.0


class TestRegionFromDict:
    """Tests for region_from_dict function."""

    def test_circular_region(self):
        """Test creating circular region from dict."""
        config = {
            'name': 'TestCircle',
            'type': 'circle',
            'center': [-23.0, -46.0],
            'radius': 100.0,
            'resolution': 5.0,
            'transition_start': 25.0
        }

        region = region_from_dict(config)

        assert isinstance(region, CircularRegion)
        assert region.name == 'TestCircle'
        assert region.resolution == 5.0
        assert region.transition_width == 20.0  # 25 - 5
        assert region.radius == 100.0

    def test_polygon_region(self):
        """Test creating polygon region from dict."""
        config = {
            'name': 'TestPolygon',
            'type': 'polygon',
            'polygon': [
                [-10.0, -10.0],
                [-10.0, 10.0],
                [10.0, 10.0],
            ],
            'resolution': 10.0,
            'transition_start': 50.0
        }

        region = region_from_dict(config)

        assert isinstance(region, PolygonRegion)
        assert region.name == 'TestPolygon'
        assert len(region.vertices) == 3

    def test_invalid_type(self):
        """Invalid type should raise ValueError."""
        config = {
            'name': 'Test',
            'type': 'invalid',
            'resolution': 10.0,
            'transition_start': 50.0
        }

        with pytest.raises(ValueError):
            region_from_dict(config)


class TestRegionsFromConfig:
    """Tests for regions_from_config function."""

    def test_multiple_regions(self):
        """Test creating multiple regions from config."""
        config = {
            'background_resolution': 150.0,
            'regions': [
                {
                    'name': 'Region1',
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 100.0,
                    'resolution': 10.0,
                    'transition_start': 30.0
                },
                {
                    'name': 'Region2',
                    'type': 'circle',
                    'center': [10.0, 10.0],
                    'radius': 50.0,
                    'resolution': 5.0,
                    'transition_start': 10.0
                }
            ]
        }

        regions, bg_res = regions_from_config(config)

        assert len(regions) == 2
        assert bg_res == 150.0
        assert regions[0].name == 'Region1'
        assert regions[1].name == 'Region2'

    def test_default_background(self):
        """Default background resolution should be 150."""
        config = {
            'regions': [
                {
                    'name': 'Test',
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 100.0,
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        regions, bg_res = regions_from_config(config)

        assert bg_res == 150.0
