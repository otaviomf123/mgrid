Quick Start
===========

This guide shows how to generate variable-resolution meshes with mgrid
using a single unified configuration file.

Installation
------------

Install mgrid via pip:

.. code-block:: bash

   pip install mgrid

   # Or with all dependencies
   pip install mgrid[full]

After installation, the ``mgrid`` command is available in your terminal.

Unified Workflow
----------------

mgrid uses a single JSON configuration file that controls the entire pipeline:

.. code-block:: text

   1. mgrid config.json                    → Generate mesh with JIGSAW
   2. ./init_atmosphere namelist...        → Generate static file (external)
   3. mgrid config.json --static-file ...  → Cut regional mesh + partition

Configuration File Structure
----------------------------

A complete configuration file contains:

.. code-block:: json

   {
       "name": "my_region",
       "description": "Regional mesh description",
       "background_resolution": 60.0,
       "output_dir": "output/my_region",

       "regions": [
           {
               "name": "HighRes_Area",
               "type": "circle",
               "center": [-23.55, -46.63],
               "radius": 200,
               "resolution": 15.0,
               "transition_start": 30.0
           }
       ],

       "regional_cut": {
           "type": "circle",
           "inside_point": [-23.55, -46.63],
           "radius": 300000
       },

       "partitions": [32, 64, 128]
   }

Quick Example
-------------

**Step 1: Create configuration file** ``config.json``:

.. code-block:: json

   {
       "name": "saopaulo",
       "background_resolution": 60.0,
       "output_dir": "output",
       "regions": [
           {
               "name": "Metro",
               "type": "circle",
               "center": [-23.55, -46.63],
               "radius": 200,
               "resolution": 15.0,
               "transition_start": 30.0
           }
       ],
       "regional_cut": {
           "type": "circle",
           "inside_point": [-23.55, -46.63],
           "radius": 300000
       },
       "partitions": [32, 64]
   }

**Step 2: Generate mesh with JIGSAW**:

.. code-block:: bash

   mgrid config.json

This generates the grid file (``output/saopaulo.grid.nc``).

**Step 3: Generate static file (external - MPAS/MONAN)**:

Generate the static file using MPAS ``init_atmosphere``. Configure your
``namelist.init_atmosphere`` with ``config_static_interp = true`` and
the path to the grid file generated in Step 2.

See `MPAS Documentation <https://www2.mmm.ucar.edu/projects/mpas/site/documentation/mpas_overview.html>`_
for detailed instructions on static file generation.

**Step 4: Cut regional mesh and partition**:

.. code-block:: bash

   mgrid config.json --static-file static.nc

This generates:
- Regional mesh: ``output/saopaulo.static.nc``
- Partitions: ``output/saopaulo.graph.info.part.32``, ``...part.64``

**Step 5: Run MPAS/MONAN**:

.. code-block:: bash

   mpirun -np 64 ./atmosphere_model

Goiás Example (Complete)
------------------------

A more complex example with multiple resolution zones:

.. code-block:: json

   {
       "name": "goias_regional",
       "description": "Multi-resolution mesh for Goiás state",
       "background_resolution": 30.0,
       "output_dir": "output/goias",

       "regions": [
           {
               "name": "Regional_Buffer",
               "type": "polygon",
               "polygon": [
                   [-10.9, -54.8], [-10.9, -44.4],
                   [-21.0, -44.4], [-21.0, -54.8]
               ],
               "resolution": 5.0,
               "transition_start": 30.0
           },
           {
               "name": "Goias_State",
               "type": "polygon",
               "polygon": [
                   [-12.4, -50.2], [-19.5, -50.8],
                   [-18.7, -52.4], [-17.5, -53.2],
                   [-15.1, -51.5], [-13.7, -50.9]
               ],
               "resolution": 3.0,
               "transition_start": 5.0
           },
           {
               "name": "Goiania_Metro",
               "type": "circle",
               "center": [-16.71, -49.24],
               "radius": 105,
               "resolution": 1.0,
               "transition_start": 3.0
           }
       ],

       "regional_cut": {
           "type": "polygon",
           "inside_point": [-16.0, -49.5],
           "polygon": [
               [-10.9, -54.8], [-10.9, -44.4],
               [-21.0, -44.4], [-21.0, -54.8]
           ]
       },

       "partitions": [32, 64, 128]
   }

Save as ``goias.json`` and run:

.. code-block:: bash

   # Generate mesh
   mgrid goias.json

   # After generating static file externally:
   mgrid goias.json --static-file static.nc

Using Pre-made MPAS Grids
-------------------------

Instead of generating a new mesh with JIGSAW, you can use pre-made grids from:

`MPAS Atmosphere Meshes <https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html>`_

.. code-block:: bash

   # Download pre-made grid
   wget https://mpas-dev.github.io/atmosphere/meshes/x1.40962.grid.nc

   # Generate static file (external - configure namelist.init_atmosphere)

   # Cut and partition
   mgrid config.json --static-file static.nc

CLI Reference
-------------

.. code-block:: bash

   # Run complete pipeline from config
   mgrid config.json

   # Use existing static file (skip JIGSAW)
   mgrid config.json --static-file static.nc

   # Force JIGSAW even if static_file in config
   mgrid config.json --jigsaw

   # Skip plot generation
   mgrid config.json --no-plot

   # Show grid info
   mgrid info grid.nc

   # Show help
   mgrid --help

Python API
----------

You can also use mgrid as a Python library:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   # Generate from config file
   grid = generate_mesh(config='config.json', generate_jigsaw=True)

   # Or define regions programmatically
   from mgrid import CircularRegion

   region = CircularRegion(
       name='Metro',
       resolution=15.0,
       transition_width=15.0,
       center=(-23.55, -46.63),
       radius=200.0
   )

   grid = generate_mesh(
       regions=[region],
       background_resolution=60.0
   )

Next Steps
----------

- See :doc:`pipeline` for detailed workflow explanation
- See :doc:`regions` for region configuration options
- Check ``examples/configs/`` for more configuration examples
