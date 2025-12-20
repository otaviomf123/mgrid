Guia Rápido
===========

Este guia mostra como gerar malhas de resolução variável com o mgrid
usando um único arquivo de configuração unificado.

Instalação
----------

Instale o mgrid via pip:

.. code-block:: bash

   pip install mgrid

   # Ou com todas as dependências
   pip install mgrid[full]

Após a instalação, o comando ``mgrid`` fica disponível no terminal.

Fluxo de Trabalho Unificado
---------------------------

O mgrid usa um único arquivo JSON de configuração que controla todo o pipeline:

.. code-block:: text

   1. mgrid config.json                    → Gerar malha com JIGSAW
   2. ./init_atmosphere namelist...        → Gerar arquivo static (externo)
   3. mgrid config.json --static-file ...  → Cortar malha regional + particionar

Estrutura do Arquivo de Configuração
------------------------------------

Um arquivo de configuração completo contém:

.. code-block:: json

   {
       "name": "minha_regiao",
       "description": "Descrição da malha regional",
       "background_resolution": 60.0,
       "output_dir": "saida/minha_regiao",

       "regions": [
           {
               "name": "Area_AltaResolucao",
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

Exemplo Rápido
--------------

**Passo 1: Criar arquivo de configuração** ``config.json``:

.. code-block:: json

   {
       "name": "saopaulo",
       "background_resolution": 60.0,
       "output_dir": "saida",
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

**Passo 2: Gerar malha com JIGSAW**:

.. code-block:: bash

   mgrid config.json

Isso gera o arquivo de grade (``saida/saopaulo.grid.nc``).

**Passo 3: Gerar arquivo static (externo - MPAS/MONAN)**:

Gere o arquivo static usando ``init_atmosphere`` do MPAS. Configure
``namelist.init_atmosphere`` com ``config_static_interp = true`` e o
caminho para o arquivo de grade gerado no Passo 2.

Veja a `Documentação do MPAS <https://www2.mmm.ucar.edu/projects/mpas/site/documentation/mpas_overview.html>`_
para instruções detalhadas.

**Passo 4: Cortar malha regional e particionar**:

.. code-block:: bash

   mgrid config.json --static-file static.nc

Isso gera:
- Malha regional: ``saida/saopaulo.static.nc``
- Partições: ``saida/saopaulo.graph.info.part.32``, ``...part.64``

**Passo 5: Executar MPAS/MONAN**:

.. code-block:: bash

   mpirun -np 64 ./atmosphere_model

Exemplo Goiás (Completo)
------------------------

Um exemplo mais complexo com múltiplas zonas de resolução:

.. code-block:: json

   {
       "name": "goias_regional",
       "description": "Malha multi-resolução para o estado de Goiás",
       "background_resolution": 30.0,
       "output_dir": "saida/goias",

       "regions": [
           {
               "name": "Buffer_Regional",
               "type": "polygon",
               "polygon": [
                   [-10.9, -54.8], [-10.9, -44.4],
                   [-21.0, -44.4], [-21.0, -54.8]
               ],
               "resolution": 5.0,
               "transition_start": 30.0
           },
           {
               "name": "Estado_Goias",
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

Salve como ``goias.json`` e execute:

.. code-block:: bash

   # Gerar malha
   mgrid goias.json

   # Após gerar arquivo static externamente:
   mgrid goias.json --static-file static.nc

Usando Grades MPAS Pré-geradas
------------------------------

Em vez de gerar uma nova malha com JIGSAW, você pode usar grades pré-geradas de:

`MPAS Atmosphere Meshes <https://mpas-dev.github.io/atmosphere/atmosphere_meshes.html>`_

.. code-block:: bash

   # Baixar grade pré-gerada
   wget https://mpas-dev.github.io/atmosphere/meshes/x1.40962.grid.nc

   # Gerar arquivo static (externo - configurar namelist.init_atmosphere)

   # Cortar e particionar
   mgrid config.json --static-file static.nc

Referência do CLI
-----------------

.. code-block:: bash

   # Executar pipeline completo a partir do config
   mgrid config.json

   # Usar arquivo static existente (pular JIGSAW)
   mgrid config.json --static-file static.nc

   # Forçar JIGSAW mesmo se static_file estiver no config
   mgrid config.json --jigsaw

   # Pular geração de gráficos
   mgrid config.json --no-plot

   # Mostrar informações da grade
   mgrid info grid.nc

   # Mostrar ajuda
   mgrid --help

API Python
----------

Você também pode usar o mgrid como biblioteca Python:

.. code-block:: python

   from mgrid import generate_mesh, save_grid

   # Gerar a partir de arquivo de configuração
   grid = generate_mesh(config='config.json', generate_jigsaw=True)

   # Ou definir regiões programaticamente
   from mgrid import CircularRegion

   regiao = CircularRegion(
       name='Metro',
       resolution=15.0,
       transition_width=15.0,
       center=(-23.55, -46.63),
       radius=200.0
   )

   grid = generate_mesh(
       regions=[regiao],
       background_resolution=60.0
   )

Próximos Passos
---------------

- Veja :doc:`pipeline` para explicação detalhada do fluxo de trabalho
- Veja :doc:`regioes` para opções de configuração de regiões
- Confira ``examples/configs/`` para mais exemplos de configuração
