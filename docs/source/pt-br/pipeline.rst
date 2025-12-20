Pipeline Completo
=================

Este guia descreve o fluxo de trabalho completo desde dados geográficos
até malhas MPAS/MONAN prontas para produção.

Visão Geral do Pipeline
-----------------------

.. code-block:: text

   Shapefile → Config → Cell Width → JIGSAW → Grade MPAS → Arquivo Static → Corte Regional → Partição

.. list-table::
   :header-rows: 1
   :widths: 10 35 20

   * - Etapa
     - Descrição
     - Ferramenta
   * - 1
     - Extrair polígono do shapefile
     - GeoPandas
   * - 2
     - Definir zonas de resolução
     - mgrid
   * - 3
     - Calcular função de largura de célula
     - mgrid
   * - 4
     - Gerar malha esférica
     - JIGSAW
   * - 5
     - Converter para formato MPAS
     - mpas_tools
   * - 6
     - **Gerar arquivo static (dados geográficos)**
     - **MPAS init_atmosphere**
   * - 7
     - Cortar domínio regional
     - mgrid (MPAS-Limited-Area)
   * - 8
     - Particionar para MPI
     - METIS (gpmetis)

.. important::

   A **Etapa 6 (Geração do Arquivo Static)** é realizada **fora do mgrid** usando o ``init_atmosphere`` do MPAS.
   O arquivo static combina a grade com dados geográficos (terreno, uso do solo, tipo de solo, etc.)
   necessários para simulação. Veja a `Documentação do MPAS <https://www2.mmm.ucar.edu/projects/mpas/site/documentation/mpas_overview.html>`_
   para instruções detalhadas.

Grades Pré-geradas (Alternativa)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Para testes rápidos ou quando resolução personalizada não é necessária, você pode pular as etapas 1-5
e baixar grades MPAS pré-geradas em:

`MPAS Atmosphere Meshes <https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html>`_

Resoluções disponíveis: 3km, 7.5km, 15km, 30km, 60km, 120km, 240km, 480km.

Guia Passo a Passo
------------------

Etapa 1: Extrair Polígono do Shapefile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Usar GeoPandas para carregar e extrair fronteiras geográficas. Os shapefiles
podem ser obtidos do `DIVA-GIS <https://diva-gis.org/gdata>`_, que fornece
dados de fronteiras administrativas gratuitos para todos os países:

- **Nível 0** (BRA_adm0.shp): Fronteiras nacionais (Brasil)
- **Nível 1** (BRA_adm1.shp): Fronteiras estaduais/regionais (Goiás, São Paulo, etc.)
- **Nível 2** (BRA_adm2.shp): Fronteiras municipais (Goiânia, São Paulo, etc.)

Para baixar os shapefiles:

1. Acesse https://diva-gis.org/gdata
2. Selecione o país desejado
3. Escolha "Administrative areas" como assunto
4. Baixe e extraia o arquivo ZIP

.. code-block:: python

   import geopandas as gpd

   # Carregar shapefile (baixado do DIVA-GIS)
   estados = gpd.read_file('BRA_adm1.shp')

   # Filtrar por atributo
   goias = estados[estados['NAME_1'] == 'Goiás']

   # Obter geometria
   geometria = goias.geometry.iloc[0]

   # Simplificar para eficiência
   simplificado = geometria.simplify(0.1, preserve_topology=True)

   # Extrair coordenadas como [lat, lon]
   vertices = []
   for lon, lat in simplificado.exterior.coords[:-1]:
       vertices.append([lat, lon])

Etapa 2: Criar Configuração
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Definir a hierarquia de resolução:

.. code-block:: python

   config = {
       "background_resolution": 30.0,
       "regions": [
           {
               "name": "Buffer_Regional",
               "type": "polygon",
               "polygon": [[-10.9, -54.8], [-10.9, -44.4],
                          [-21.0, -44.4], [-21.0, -54.8]],
               "resolution": 5.0,
               "transition_start": 30.0
           },
           {
               "name": "Estado",
               "type": "polygon",
               "polygon": vertices,  # Da etapa 1
               "resolution": 3.0,
               "transition_start": 5.0
           },
           {
               "name": "Metropolitana",
               "type": "circle",
               "center": [-16.71, -49.24],
               "radius": 105,
               "resolution": 1.0,
               "transition_start": 3.0
           }
       ]
   }

Etapa 3: Calcular Função de Largura de Célula
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Gerar o campo de dimensionamento da malha:

.. code-block:: python

   from mgrid import generate_mesh, save_config

   # Salvar configuração
   save_config(config, 'minha_config.json')

   # Gerar função de largura de célula
   grid = generate_mesh(
       config=config,
       output_path='saida/minha_malha',
       generate_jigsaw=True  # Executar JIGSAW
   )

   print(grid.summary())

Etapa 4-5: Gerar Malha JIGSAW e Converter para MPAS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Isso acontece automaticamente quando ``generate_jigsaw=True``:

.. code-block:: python

   from mgrid.io import convert_to_mpas

   # Se a malha foi gerada
   if grid.mesh_file:
       convert_to_mpas(
           mesh_file=grid.mesh_file,
           output_file='saida/minha_malha.grid.nc'
       )

Etapa 6: Gerar Arquivo Static (Externo - MPAS init)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. important::

   Esta etapa é realizada **fora do mgrid** usando o ``init_atmosphere`` do MPAS.

O arquivo static combina a grade com dados geográficos (terreno, uso do solo,
tipo de solo, vegetação, etc.) necessários para simulação atmosférica.

**Pré-requisitos:**

- Executável ``init_atmosphere`` do MPAS (compilado do código fonte)
- Arquivos de dados geográficos (GEOGRID, terreno, uso do solo)

**Configuração:**

Configure ``namelist.init_atmosphere`` com:

- ``config_static_interp = true``
- Caminho para o arquivo de grade gerado na Etapa 5

Para instruções detalhadas, veja a documentação oficial:

- `MPAS Overview <https://www2.mmm.ucar.edu/projects/mpas/site/documentation/mpas_overview.html>`_
- `MPAS-Atmosphere Tutorial <https://www2.mmm.ucar.edu/projects/mpas/tutorial/>`_

Etapa 7: Cortar Domínio Regional
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Gerar arquivo de especificação e cortar a malha regional do arquivo static:

.. code-block:: python

   from mgrid import generate_pts_file, create_regional_mesh_python

   # Gerar arquivo .pts
   pts_file = generate_pts_file(
       output_path='saida/minha_regiao.pts',
       name='minha_regiao',
       region_type='custom',
       inside_point=(-16.0, -49.5),  # (lat, lon) dentro da região
       polygon=vertices
   )

   # Cortar malha regional do arquivo static
   malha_regional, arquivo_grafo = create_regional_mesh_python(
       pts_file=pts_file,
       global_grid_file='static.nc'  # Usar arquivo static gerado na Etapa 6
   )

   print(f"Malha regional: {malha_regional}")
   print(f"Arquivo de grafo: {arquivo_grafo}")

Etapa 8: Particionar para MPI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Particionar a malha para execução paralela:

.. code-block:: python

   from mgrid import partition_mesh

   # Particionar para 64 processos MPI
   arquivo_particao = partition_mesh(
       graph_file=arquivo_grafo,
       num_partitions=64,
       minconn=True,   # Minimizar conectividade
       contig=True,    # Forçar partições contíguas
       niter=200       # Iterações de refinamento
   )

   print(f"Arquivo de partição: {arquivo_particao}")

Função de Pipeline Completo
---------------------------

Usar ``run_full_pipeline`` para etapas 7-8 (após gerar arquivo static):

.. code-block:: python

   from mgrid import run_full_pipeline

   resultados = run_full_pipeline(
       pts_file='saida/minha_regiao.pts',
       global_grid_file='static.nc',  # Usar arquivo static da Etapa 6
       num_partitions=[32, 64, 128]   # Múltiplas partições suportadas
   )

   print(f"Malha regional: {resultados['regional_grid']}")
   print(f"Arquivos de partição: {resultados['partition_files']}")

Exemplo via Linha de Comando
----------------------------

O exemplo ``09_goias_shapefile_grid.py`` demonstra o pipeline completo:

.. code-block:: bash

   # Execução rápida: configuração + cell width + gráficos apenas
   python examples/09_goias_shapefile_grid.py

   # Pipeline completo com geração de malha JIGSAW
   python examples/09_goias_shapefile_grid.py --jigsaw

   # Pipeline completo com arquivo static existente + múltiplas partições
   python examples/09_goias_shapefile_grid.py \
       --global-grid static.nc \
       --nprocs 32 64 128

Arquivos de Saída
-----------------

O pipeline completo gera:

.. code-block:: text

   saida/
   ├── minha_config.json                    # Configuração
   ├── minha_malha-HFUN.msh                 # Cell width JIGSAW
   ├── minha_malha-MESH.msh                 # Malha JIGSAW
   ├── minha_malha.grid.nc                  # Malha MPAS global
   │
   │   [Externo: Gerar static.nc usando MPAS init_atmosphere]
   │
   ├── minha_regiao.pts                     # Especificação da região
   ├── minha_regiao.grid.nc                 # Malha MPAS regional
   ├── minha_regiao.graph.info              # Arquivo de grafo
   ├── minha_regiao.graph.info.part.32      # Partição MPI (32 procs)
   ├── minha_regiao.graph.info.part.64      # Partição MPI (64 procs)
   └── minha_regiao.graph.info.part.128     # Partição MPI (128 procs)

Executando MPAS/MONAN
---------------------

Após completar o pipeline:

.. code-block:: bash

   # Copiar arquivos para o diretório de execução
   cp saida/minha_regiao.grid.nc ./
   cp saida/minha_regiao.graph.info.part.64 ./

   # Executar modelo com 64 processos MPI
   mpirun -np 64 ./atmosphere_model

O modelo usará automaticamente o arquivo de partição para distribuir
as células entre os processos MPI.

Considerações de Desempenho
---------------------------

- **Geração de malha JIGSAW**: Pode levar horas para malhas globais de alta resolução
- **Geração do arquivo static**: Depende da resolução dos dados geográficos
- **Corte regional**: Muito mais rápido, tipicamente segundos a minutos
- **Use malhas globais existentes**: Baixe malhas pré-geradas quando possível

Grades pré-geradas estão disponíveis em:

- `MPAS Atmosphere Meshes <https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html>`_
- Resoluções: 3km, 7.5km, 15km, 30km, 60km, 120km, 240km, 480km

Considerações para o MONAN
--------------------------

O MONAN (Model for Ocean-laNd-Atmosphere PredictioN) utiliza o mesmo
formato de malha do MPAS. Os arquivos gerados pelo mgrid são diretamente
compatíveis com o MONAN.

Para execução no MONAN:

.. code-block:: bash

   # Mesmos arquivos funcionam para MONAN
   cp saida/minha_regiao.grid.nc ./
   cp saida/minha_regiao.graph.info.part.64 ./

   # Executar MONAN
   mpirun -np 64 ./monan_model
