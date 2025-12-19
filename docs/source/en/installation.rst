Installation
============

This guide covers the installation of mgrid and its dependencies.

Requirements
------------

- Python 3.8 or higher
- Operating System: Linux, macOS, or Windows

Recommended: Conda Environment
------------------------------

For full functionality, we recommend using a conda environment. This ensures
all dependencies, including compiled libraries, are properly installed.

.. code-block:: bash

   # Create a new environment
   conda create -n mgrid python=3.11 -y
   conda activate mgrid

   # Install core dependencies
   conda install -c conda-forge numpy scipy matplotlib -y
   conda install -c conda-forge xarray netcdf4 -y

   # Install geospatial libraries
   conda install -c conda-forge shapely pyproj geopandas -y
   conda install -c conda-forge cartopy basemap -y

   # Install mesh generation tools
   conda install -c conda-forge jigsawpy -y

   # Install MPAS tools
   conda install -c conda-forge mpas_tools -y

   # Install graph partitioning
   conda install -c conda-forge metis -y

   # Clone and install mgrid
   git clone https://github.com/monan/mgrid.git
   cd mgrid
   pip install -e .

Quick Install (pip only)
------------------------

For basic functionality without mesh generation:

.. code-block:: bash

   pip install mgrid

For full functionality (some features may not work without conda):

.. code-block:: bash

   pip install mgrid[full]

Dependencies Overview
---------------------

Required
^^^^^^^^

- **numpy**: Core array operations

Optional (Full Functionality)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 40 20

   * - Package
     - Purpose
     - Installation
   * - shapely
     - Polygon operations
     - pip or conda
   * - geopandas
     - Shapefile reading
     - conda recommended
   * - jigsawpy
     - Mesh generation (JIGSAW)
     - conda only
   * - mpas_tools
     - MPAS format conversion
     - conda only
   * - metis
     - Graph partitioning (gpmetis)
     - conda only
   * - matplotlib
     - Visualization
     - pip or conda
   * - basemap
     - Map projections
     - conda only

External Tools
^^^^^^^^^^^^^^

The complete pipeline requires:

- **MPAS-Limited-Area**: For regional mesh extraction

  .. code-block:: bash

     git clone https://github.com/MiCurry/MPAS-Limited-Area.git

- **gpmetis**: For mesh partitioning (installed with metis conda package)

Verification
------------

Verify the installation:

.. code-block:: python

   import mgrid
   print(m_grid.__version__)

   # Check available features
   from mgrid import generate_mesh, CircularRegion

   # Test basic functionality
   region = CircularRegion(
       name='Test',
       resolution=10.0,
       transition_width=20.0,
       center=(0.0, 0.0),
       radius=100.0
   )
   grid = generate_mesh(regions=[region], background_resolution=50.0)
   print(grid.summary())

Troubleshooting
---------------

jigsawpy not found
^^^^^^^^^^^^^^^^^^

The jigsawpy package is only available through conda:

.. code-block:: bash

   conda install -c conda-forge jigsawpy

mpas_tools import error
^^^^^^^^^^^^^^^^^^^^^^^

Install mpas_tools from conda-forge:

.. code-block:: bash

   conda install -c conda-forge mpas_tools

gpmetis not found
^^^^^^^^^^^^^^^^^

Install the metis package:

.. code-block:: bash

   conda install -c conda-forge metis

The ``gpmetis`` executable will be available in your conda environment's bin directory.
