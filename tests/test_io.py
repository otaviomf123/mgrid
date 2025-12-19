"""Tests for the I/O module."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from m_grid.io import (
    load_config,
    save_config,
    validate_config,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config = {
            'background_resolution': 100.0,
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

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            loaded = load_config(temp_path)
            assert loaded['background_resolution'] == 100.0
            assert len(loaded['regions']) == 1
        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_file(self):
        """Loading nonexistent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config('/nonexistent/path/config.json')

    def test_load_invalid_json(self):
        """Loading invalid JSON should raise error."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write('not valid json {{{')
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_config(temp_path)
        finally:
            Path(temp_path).unlink()


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config(self):
        """Test saving configuration to file."""
        config = {
            'background_resolution': 100.0,
            'regions': []
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'test_config.json'
            result = save_config(config, output_path)

            assert result == output_path
            assert output_path.exists()

            # Verify content
            with open(output_path) as f:
                loaded = json.load(f)

            assert loaded == config


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_circle_config(self):
        """Valid circle configuration should pass validation."""
        config = {
            'regions': [
                {
                    'name': 'Test',
                    'type': 'circle',
                    'center': [-23.0, -46.0],
                    'radius': 100.0,
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        assert validate_config(config) == True

    def test_valid_polygon_config(self):
        """Valid polygon configuration should pass validation."""
        config = {
            'regions': [
                {
                    'name': 'Test',
                    'type': 'polygon',
                    'polygon': [
                        [-10.0, -10.0],
                        [-10.0, 10.0],
                        [10.0, 10.0],
                    ],
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        assert validate_config(config) == True

    def test_missing_regions(self):
        """Config without regions should fail."""
        config = {'background_resolution': 100.0}

        with pytest.raises(ValueError, match="must contain 'regions'"):
            validate_config(config)

    def test_missing_type(self):
        """Region without type should fail."""
        config = {
            'regions': [
                {
                    'name': 'Test',
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="must specify 'type'"):
            validate_config(config)

    def test_missing_resolution(self):
        """Region without resolution should fail."""
        config = {
            'regions': [
                {
                    'name': 'Test',
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 100.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="must specify 'resolution'"):
            validate_config(config)

    def test_missing_transition_start(self):
        """Region without transition_start should fail."""
        config = {
            'regions': [
                {
                    'name': 'Test',
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 100.0,
                    'resolution': 10.0
                }
            ]
        }

        with pytest.raises(ValueError, match="must specify 'transition_start'"):
            validate_config(config)

    def test_circle_missing_center(self):
        """Circle without center should fail."""
        config = {
            'regions': [
                {
                    'type': 'circle',
                    'radius': 100.0,
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="must specify 'center'"):
            validate_config(config)

    def test_circle_missing_radius(self):
        """Circle without radius should fail."""
        config = {
            'regions': [
                {
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="must specify 'radius'"):
            validate_config(config)

    def test_polygon_missing_vertices(self):
        """Polygon without polygon key should fail."""
        config = {
            'regions': [
                {
                    'type': 'polygon',
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="must specify 'polygon'"):
            validate_config(config)

    def test_polygon_insufficient_vertices(self):
        """Polygon with less than 3 vertices should fail."""
        config = {
            'regions': [
                {
                    'type': 'polygon',
                    'polygon': [[0.0, 0.0], [1.0, 1.0]],
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="at least 3 vertices"):
            validate_config(config)

    def test_invalid_latitude(self):
        """Latitude outside [-90, 90] should fail."""
        config = {
            'regions': [
                {
                    'type': 'circle',
                    'center': [100.0, 0.0],  # Invalid latitude
                    'radius': 100.0,
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="latitude must be"):
            validate_config(config)

    def test_invalid_longitude(self):
        """Longitude outside [-180, 180] should fail."""
        config = {
            'regions': [
                {
                    'type': 'circle',
                    'center': [0.0, 200.0],  # Invalid longitude
                    'radius': 100.0,
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="longitude must be"):
            validate_config(config)

    def test_negative_resolution(self):
        """Negative resolution should fail."""
        config = {
            'regions': [
                {
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 100.0,
                    'resolution': -10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="resolution must be positive"):
            validate_config(config)

    def test_transition_less_than_resolution(self):
        """Transition start less than resolution should fail."""
        config = {
            'regions': [
                {
                    'type': 'circle',
                    'center': [0.0, 0.0],
                    'radius': 100.0,
                    'resolution': 30.0,
                    'transition_start': 10.0
                }
            ]
        }

        with pytest.raises(ValueError, match="transition_start.*must be >="):
            validate_config(config)

    def test_invalid_region_type(self):
        """Invalid region type should fail."""
        config = {
            'regions': [
                {
                    'type': 'invalid_type',
                    'resolution': 10.0,
                    'transition_start': 30.0
                }
            ]
        }

        with pytest.raises(ValueError, match="invalid type"):
            validate_config(config)
