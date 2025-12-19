Instalação
==========

Este guia descreve a instalação do mgrid e suas dependências.

Requisitos
----------

- Python 3.8 ou superior
- Sistema Operacional: Linux, macOS ou Windows

Recomendado: Ambiente Conda
---------------------------

Para funcionalidade completa, recomendamos usar um ambiente conda.
Isso garante que todas as dependências, incluindo bibliotecas compiladas,
sejam instaladas corretamente.

.. code-block:: bash

   # Criar novo ambiente
   conda create -n mgrid python=3.11 -y
   conda activate mgrid

   # Instalar dependências principais
   conda install -c conda-forge numpy scipy matplotlib -y
   conda install -c conda-forge xarray netcdf4 -y

   # Instalar bibliotecas geoespaciais
   conda install -c conda-forge shapely pyproj geopandas -y
   conda install -c conda-forge cartopy basemap -y

   # Instalar ferramentas de geração de malha
   conda install -c conda-forge jigsawpy -y

   # Instalar ferramentas MPAS
   conda install -c conda-forge mpas_tools -y

   # Instalar particionamento de grafos
   conda install -c conda-forge metis -y

   # Clonar e instalar mgrid
   git clone https://github.com/otaviomf123/mgrid.git
   cd mgrid
   pip install -e .

Instalação Rápida (apenas pip)
------------------------------

Para funcionalidade básica:

.. code-block:: bash

   pip install mgrid

Para funcionalidade completa (algumas features requerem conda):

.. code-block:: bash

   pip install mgrid[full]

Visão Geral das Dependências
----------------------------

Obrigatórias
^^^^^^^^^^^^

- **numpy**: Operações com arrays

Opcionais (Funcionalidade Completa)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 20 40 20

   * - Pacote
     - Propósito
     - Instalação
   * - shapely
     - Operações com polígonos
     - pip ou conda
   * - geopandas
     - Leitura de shapefiles
     - conda recomendado
   * - jigsawpy
     - Geração de malha (JIGSAW)
     - apenas conda
   * - mpas_tools
     - Conversão para formato MPAS
     - apenas conda
   * - metis
     - Particionamento de grafos (gpmetis)
     - apenas conda
   * - matplotlib
     - Visualização
     - pip ou conda
   * - basemap
     - Projeções de mapas
     - apenas conda

Ferramentas Externas
^^^^^^^^^^^^^^^^^^^^

O pipeline completo requer:

- **MPAS-Limited-Area**: Para extração de malha regional

  .. code-block:: bash

     git clone https://github.com/MiCurry/MPAS-Limited-Area.git

- **gpmetis**: Para particionamento de malha (instalado com pacote metis)

Verificação
-----------

Verificar a instalação:

.. code-block:: python

   import mgrid
   print(m_grid.__version__)

   # Verificar funcionalidades
   from mgrid import generate_mesh, CircularRegion

   # Testar funcionalidade básica
   region = CircularRegion(
       name='Teste',
       resolution=10.0,
       transition_width=20.0,
       center=(0.0, 0.0),
       radius=100.0
   )
   grid = generate_mesh(regions=[region], background_resolution=50.0)
   print(grid.summary())

Solução de Problemas
--------------------

jigsawpy não encontrado
^^^^^^^^^^^^^^^^^^^^^^^

O pacote jigsawpy está disponível apenas via conda:

.. code-block:: bash

   conda install -c conda-forge jigsawpy

Erro de importação mpas_tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Instalar mpas_tools do conda-forge:

.. code-block:: bash

   conda install -c conda-forge mpas_tools

gpmetis não encontrado
^^^^^^^^^^^^^^^^^^^^^^

Instalar o pacote metis:

.. code-block:: bash

   conda install -c conda-forge metis

O executável ``gpmetis`` estará disponível no diretório bin do ambiente conda.
