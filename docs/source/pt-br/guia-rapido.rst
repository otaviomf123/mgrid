Guia Rápido
===========

Este guia mostra como gerar malhas de resolução variável com o mgrid.

Uso Básico
----------

Gerar uma malha de resolução uniforme:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   # Gerar malha global de 30 km
   grid = generate_mesh(resolution=30)

   # Salvar no formato MPAS
   save_grid(grid, 'global_30km.nc')

Resolução Variável com Região Circular
--------------------------------------

Criar uma região de alta resolução dentro de uma malha global:

.. code-block:: python

   from mgrid import generate_mesh, save_grid, CircularRegion

   # Definir região de refinamento
   regiao = CircularRegion(
       name='Amazonia',
       resolution=5.0,          # 5 km dentro da região
       transition_width=50.0,   # 50 km de transição suave
       center=(-3.0, -60.0),    # (lat, lon) ponto central
       radius=500.0             # 500 km de raio
   )

   # Gerar com 100 km de resolução de fundo
   grid = generate_mesh(
       regions=[regiao],
       background_resolution=100.0
   )

   save_grid(grid, 'amazonia_5km.nc')

Resolução Variável com Região Poligonal
---------------------------------------

Usar uma fronteira poligonal para a região de refinamento. Os shapefiles podem
ser obtidos do `DIVA-GIS <https://diva-gis.org/gdata>`_, que fornece dados de
fronteiras administrativas gratuitos para todos os países:

- **Nível 0** (BRA_adm0.shp): Fronteiras nacionais
- **Nível 1** (BRA_adm1.shp): Fronteiras estaduais/regionais
- **Nível 2** (BRA_adm2.shp): Fronteiras municipais

.. code-block:: python

   from mgrid import generate_mesh, save_grid, PolygonRegion

   # Definir fronteira estadual (exemplo: Goiás)
   # Shapefile: https://diva-gis.org/gdata
   regiao = PolygonRegion(
       name='Goias',
       resolution=10.0,         # 10 km dentro
       transition_width=30.0,   # 30 km de transição
       vertices=[
           (-12.4, -50.2),      # (lat, lon)
           (-19.5, -50.8),
           (-18.7, -52.4),
           (-16.5, -53.2),
           (-14.0, -50.8),
       ]
   )

   grid = generate_mesh(regions=[regiao], background_resolution=100.0)
   save_grid(grid, 'goias_10km.nc')

Múltiplas Regiões Aninhadas
---------------------------

Criar uma hierarquia de resoluções:

.. code-block:: python

   from mgrid import generate_mesh, save_grid, CircularRegion, PolygonRegion

   # Região externa: nível estadual (15 km)
   estado = PolygonRegion(
       name='Estado',
       resolution=15.0,
       transition_width=30.0,
       vertices=[
           (-19.0, -53.0),
           (-19.0, -44.0),
           (-25.5, -44.0),
           (-25.5, -53.0),
       ]
   )

   # Região interna: área metropolitana (3 km)
   metro = CircularRegion(
       name='Metropolitana',
       resolution=3.0,
       transition_width=10.0,
       center=(-23.55, -46.63),  # São Paulo
       radius=80.0
   )

   # Gerar com 60 km de fundo
   grid = generate_mesh(
       regions=[estado, metro],
       background_resolution=60.0
   )

   save_grid(grid, 'saopaulo_aninhado.nc')

Usando Arquivos de Configuração
-------------------------------

Criar um arquivo JSON de configuração:

.. code-block:: json

   {
       "background_resolution": 60.0,
       "grid_density": 0.05,
       "regions": [
           {
               "name": "Estado",
               "type": "polygon",
               "polygon": [
                   [-19.0, -53.0],
                   [-19.0, -44.0],
                   [-25.5, -44.0],
                   [-25.5, -53.0]
               ],
               "resolution": 15.0,
               "transition_start": 30.0
           },
           {
               "name": "Metro",
               "type": "circle",
               "center": [-23.55, -46.63],
               "radius": 80,
               "resolution": 3.0,
               "transition_start": 15.0
           }
       ]
   }

Carregar e usar:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   grid = generate_mesh(config='minha_config.json')
   save_grid(grid, 'minha_malha.nc')

Visualização
------------

Plotar a distribuição de largura de célula:

.. code-block:: python

   from mgrid import generate_mesh, plot_cell_width

   grid = generate_mesh(config='minha_config.json')
   plot_cell_width(grid, output='largura_celula.png')

Próximos Passos
---------------

- Veja :doc:`pipeline` para o fluxo completo de geração de malha
- Veja os exemplos no diretório ``examples/``
