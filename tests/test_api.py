"""Tests for the high-level API."""

import numpy as np
import pytest

from m_grid.api import Grid, generate_mesh


class TestGrid:
    """Tests for Grid class."""

    def test_empty_grid(self):
        """Empty grid should have zero properties."""
        grid = Grid()

        assert grid.min_resolution == 0.0
        assert grid.max_resolution == 0.0
        assert grid.mean_resolution == 0.0

    def test_grid_with_data(self):
        """Grid with data should compute properties correctly."""
        grid = Grid(
            cell_width=np.array([[10, 20], [30, 40]]),
            lon=np.array([0, 1]),
            lat=np.array([0, 1])
        )

        assert grid.min_resolution == 10.0
        assert grid.max_resolution == 40.0
        assert grid.mean_resolution == 25.0

    def test_summary(self):
        """Summary should include key information."""
        grid = Grid(
            cell_width=np.array([[10, 20], [30, 40]]),
            lon=np.array([0, 1]),
            lat=np.array([0, 1])
        )

        summary = grid.summary()

        assert 'Grid Summary' in summary
        assert '10.0' in summary  # min resolution
        assert '40.0' in summary  # max resolution


class TestGenerateMesh:
    """Tests for generate_mesh function."""

    def test_uniform_resolution(self):
        """Test uniform resolution grid generation."""
        grid = generate_mesh(
            resolution=100,
            generate_jigsaw=False  # Skip JIGSAW for testing
        )

        assert grid.min_resolution == 100.0
        assert grid.max_resolution == 100.0
        assert grid.config['mode'] == 'uniform'

    def test_config_dict(self):
        """Test generation from config dictionary."""
        config = {
            'background_resolution': 150.0,
            'grid_density': 0.1,
            'regions': [
                {
                    'name': 'Test',
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 500.0,
                    'resolution': 50.0,
                    'transition_start': 100.0
                }
            ]
        }

        grid = generate_mesh(
            config=config,
            generate_jigsaw=False
        )

        assert grid.min_resolution == 50.0
        assert grid.max_resolution <= 150.0
        assert grid.config['mode'] == 'multi_region'

    def test_custom_regions(self):
        """Test generation with custom regions."""
        from m_grid import CircularRegion

        region = CircularRegion(
            name='Custom',
            resolution=25.0,
            transition_width=25.0,
            center=(0.0, 0.0),
            radius=200.0
        )

        grid = generate_mesh(
            regions=[region],
            background_resolution=100.0,
            generate_jigsaw=False
        )

        assert grid.min_resolution == 25.0
        assert grid.config['mode'] == 'custom_regions'

    def test_no_parameters_raises(self):
        """Should raise error if no parameters specified."""
        with pytest.raises(ValueError, match="Must specify one of"):
            generate_mesh(generate_jigsaw=False)

    def test_grid_density_effect(self):
        """Higher density factor should create smaller dlat = more points."""
        from m_grid import CircularRegion

        region = CircularRegion(
            name='Test',
            resolution=50.0,
            transition_width=25.0,
            center=(0.0, 0.0),
            radius=200.0
        )

        # grid_density is a multiplier: dlat = resolution * grid_density
        # Smaller grid_density = smaller dlat = more points
        grid1 = generate_mesh(
            regions=[region],
            background_resolution=100.0,
            grid_density=0.01,  # smaller = denser grid
            generate_jigsaw=False
        )

        grid2 = generate_mesh(
            regions=[region],
            background_resolution=100.0,
            grid_density=0.1,  # larger = coarser grid
            generate_jigsaw=False
        )

        # Smaller density factor = more grid points
        assert grid1.lat.size > grid2.lat.size
