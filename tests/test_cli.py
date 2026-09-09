"""Tests for the command-line pipeline (mgrid config.json)."""

import json
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from mgrid import api, cli
from mgrid.io import check_mesh_quality


def _write_grid(path, ratios):
    """Write a minimal MPAS-like grid file with the given dv/dc ratios."""
    ratios = np.asarray(ratios, dtype=float)
    dc = np.full(ratios.size, 1000.0)
    ds = xr.Dataset(
        {
            'dvEdge': ('nEdges', ratios * dc),
            'dcEdge': ('nEdges', dc),
            'latEdge': ('nEdges', np.radians(np.linspace(-10, 10, ratios.size))),
            'lonEdge': ('nEdges', np.radians(np.linspace(-50, -40, ratios.size))),
        }
    )
    ds.to_netcdf(path)
    return path


def _make_args(config_path, **overrides):
    defaults = dict(
        config=str(config_path),
        static_file=None,
        jigsaw=False,
        no_plot=True,
        min_dvdc=None,
        strict=False,
        skip_quality_check=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


@pytest.fixture
def config_file(tmp_path):
    config = {
        'name': 'testmesh',
        'output_dir': str(tmp_path / 'out'),
        'background_resolution': 100.0,
        'regions': [
            {
                'name': 'core',
                'type': 'circle',
                'center': [-16.0, -49.0],
                'radius': 100,
                'resolution': 30.0,
                'transition_start': 60.0,
            }
        ],
    }
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(config))
    return path


@pytest.fixture
def fake_jigsaw(monkeypatch, tmp_path):
    """Replace generate_mesh with a stub that pretends JIGSAW produced a .msh."""

    def _generate_mesh(config, output_path, generate_jigsaw, plot):
        mesh_file = Path(f"{output_path}-MESH.msh")
        mesh_file.parent.mkdir(parents=True, exist_ok=True)
        mesh_file.write_text('fake jigsaw mesh')
        return api.Grid(
            cell_width=np.array([[30.0, 100.0]]),
            lon=np.array([0.0, 1.0]),
            lat=np.array([0.0]),
            mesh_file=mesh_file,
            config=config,
        )

    monkeypatch.setattr(api, 'generate_mesh', _generate_mesh)


class TestCheckMeshQuality:
    def test_passes_when_all_edges_above_threshold(self, tmp_path):
        grid = _write_grid(tmp_path / 'good.nc', [0.15, 0.5, 0.9])
        result = check_mesh_quality(grid)
        assert result['passed'] is True
        assert result['n_bad_edges'] == 0
        assert result['min_ratio'] == pytest.approx(0.15)

    def test_fails_and_reports_worst_edge(self, tmp_path):
        grid = _write_grid(tmp_path / 'bad.nc', [0.5, 0.05, 0.11, 0.9])
        result = check_mesh_quality(grid)
        assert result['passed'] is False
        assert result['n_bad_edges'] == 2
        assert result['min_ratio'] == pytest.approx(0.05)
        lat, lon = result['worst_edge_latlon']
        assert lat == pytest.approx(-10 + 20 / 3)

    def test_custom_threshold(self, tmp_path):
        grid = _write_grid(tmp_path / 'g.nc', [0.11, 0.5])
        assert check_mesh_quality(grid, min_ratio=0.10)['passed'] is True
        assert check_mesh_quality(grid, min_ratio=0.12)['passed'] is False

    def test_rejects_non_mpas_file(self, tmp_path):
        path = tmp_path / 'other.nc'
        xr.Dataset({'x': ('n', [1.0])}).to_netcdf(path)
        with pytest.raises(ValueError):
            check_mesh_quality(path)


class TestCliRun:
    def test_produces_mpas_grid_file(self, config_file, fake_jigsaw, monkeypatch):
        """mgrid config.json must convert the JIGSAW mesh to <name>.grid.nc."""
        calls = []

        def _convert(mesh_file, output_file, output_dir=None):
            calls.append((Path(mesh_file), Path(output_file)))
            _write_grid(output_file, [0.2, 0.3])
            return Path(output_file)

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        results = cli._cmd_run(_make_args(config_file))

        expected = Path(json.loads(config_file.read_text())['output_dir'])
        expected = expected / 'testmesh.grid.nc'
        assert len(calls) == 1
        assert calls[0][0].name == 'testmesh-MESH.msh'
        assert calls[0][1] == expected
        assert expected.exists()
        assert results['grid_file'] == str(expected)
        assert results['global_quality']['passed'] is True

    def test_fails_loudly_when_no_nc_is_written(self, config_file, fake_jigsaw,
                                                monkeypatch):
        """A conversion that silently writes nothing must not report success."""

        def _convert(mesh_file, output_file, output_dir=None):
            return Path(output_file)

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        with pytest.raises(RuntimeError, match='was not generated'):
            cli._cmd_run(_make_args(config_file))

    def test_missing_mpas_tools_is_an_error(self, config_file, fake_jigsaw,
                                            monkeypatch):
        def _convert(mesh_file, output_file, output_dir=None):
            raise ImportError('mpas_tools is required')

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        with pytest.raises(ImportError):
            cli._cmd_run(_make_args(config_file))

    def test_quality_gate_warns_by_default(self, config_file, fake_jigsaw,
                                           monkeypatch, capsys):
        def _convert(mesh_file, output_file, output_dir=None):
            _write_grid(output_file, [0.05, 0.3])
            return Path(output_file)

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        results = cli._cmd_run(_make_args(config_file))
        out = capsys.readouterr().out

        assert results['global_quality']['passed'] is False
        assert 'FAILED the dvEdge/dcEdge quality gate' in out

    def test_quality_gate_strict_raises(self, config_file, fake_jigsaw,
                                        monkeypatch):
        def _convert(mesh_file, output_file, output_dir=None):
            _write_grid(output_file, [0.05, 0.3])
            return Path(output_file)

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        with pytest.raises(RuntimeError, match='quality gate failed'):
            cli._cmd_run(_make_args(config_file, strict=True))

    def test_quality_gate_threshold_from_config(self, tmp_path, config_file,
                                                fake_jigsaw, monkeypatch):
        config = json.loads(config_file.read_text())
        config['min_dvdc_ratio'] = 0.04
        config_file.write_text(json.dumps(config))

        def _convert(mesh_file, output_file, output_dir=None):
            _write_grid(output_file, [0.05, 0.3])
            return Path(output_file)

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        results = cli._cmd_run(_make_args(config_file, strict=True))
        assert results['global_quality']['passed'] is True
        assert results['global_quality']['threshold'] == pytest.approx(0.04)

    def test_skip_quality_check(self, config_file, fake_jigsaw, monkeypatch):
        def _convert(mesh_file, output_file, output_dir=None):
            _write_grid(output_file, [0.05])
            return Path(output_file)

        monkeypatch.setattr('mgrid.io.convert_to_mpas', _convert)

        results = cli._cmd_run(_make_args(config_file, skip_quality_check=True))
        assert results['global_quality'] is None
