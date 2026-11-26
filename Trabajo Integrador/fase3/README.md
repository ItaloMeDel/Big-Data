# Fase 3 — Pipeline ERA5 → MongoDB → MapReduce (Big Data UCSM 2026)

Carpeta `fase3/` dentro de `Trabajo Integrador/`. Datos: ERA5 enero 2020 (Perú y Pacífico Oriental), 744 h × 77×57 celdas = 3,265,416 observaciones.

## 1. Requisitos
- Python 3.12+ con `pip install -r requirements.txt` (usar un venv)
- MongoDB 8.0 en `localhost:27017` (p. ej. `podman run -d --name mongo -p 27017:27017 -v mongo_data:/data/db docker.io/library/mongo:8.0 --wiredTigerCacheSizeGB 2`)
- Hadoop 3.3.6 + Java 11 (solo para el paso 5)
- Datos: descomprimir `era5_peru_202001_nc.zip` en `Trabajo Integrador/era5_data/` (deben quedar `data_stream-oper_stepType-instant.nc` y `data_stream-oper_stepType-accum.nc`). No están en el repo por tamaño (116 MB); origen: Copernicus CDS, ERA5 single levels.

## 2. Ejecución (desde `Trabajo Integrador/fase3/`)
```bash
source ~/venv-bd/bin/activate
ERA5_HORAS=24 python 01_ingesta_completa.py   # prueba rápida (24 h); sin la variable carga las 744 h
python 01_ingesta_completa.py                 # ingesta completa + índices + agregaciones
python 02_anomalias.py                        # anomalías |z|>2 por celda y día
python 03_visualizaciones.py                  # figuras en resultados/
python 05_exportar_para_hadoop.py             # CSV de observaciones para MapReduce
hadoop/run_hadoop.sh local                    # job Hadoop Streaming (mapper.py / reducer.py)
python 04_validacion.py                       # NumPy vs MongoDB vs Hadoop -> resultado_validacion.json
```
Todo se guarda en `resultados/` (métricas JSON, PNG, CSV).

## 2b. Interfaz de ejecución en vivo (para la demostración)
```bash
source ~/venv-bd/bin/activate && cd fase3 && python demo_ui.py     # abre http://localhost:8765
```
Botón por paso (ingesta, anomalías, figuras, MapReduce/Hadoop, validación) y «Ejecutar todo». Muestra el log en vivo, qué está pasando y los resultados. Por defecto usa la base `era5_demo` y la carpeta `resultados_era5_demo/`, sin tocar la base principal del informe. Solo biblioteca estándar de Python. Requiere el contenedor de MongoDB encendido.

## 3. Qué hace cada script
| Script | Función |
|---|---|
| `01_ingesta_completa.py` | ETL NetCDF→BSON (K→°C, m→mm, viento, hPa), carga masiva `w=1,j=false`, índices 2dsphere/compuesto/B-tree, agregaciones `daily_climatology_etl` y `regional_stats_etl` |
| `02_anomalias.py` | z-score de la temperatura media diaria de cada celda respecto a su media de enero 2020 |
| `03_visualizaciones.py` | serie por dominio, mapa de temperatura, mapa de anomalías, precipitación extrema |
| `04_validacion.py` | recálculo independiente con NumPy y comparación con MongoDB y Hadoop |
| `05_exportar_para_hadoop.py`, `hadoop/` | export CSV y job MapReduce (clave = dominio\|día; valor = temp, precip, 1) |

## 4. HDFS (opcional, para la demo)
Con `~/hadoop-3.3.6/etc/hadoop/core-site.xml` → `fs.defaultFS = hdfs://localhost:9000` y `hdfs-site.xml` → `dfs.replication = 1` y rutas `dfs.namenode.name.dir` / `dfs.datanode.data.dir` en un directorio propio:
```bash
export HADOOP_HOME=~/hadoop-3.3.6; export PATH=$HADOOP_HOME/bin:$PATH
hdfs namenode -format          # SOLO la primera vez
hdfs --daemon start namenode && hdfs --daemon start datanode
jps                            # deben verse NameNode y DataNode
hadoop/run_hadoop.sh hdfs
hdfs --daemon stop datanode && hdfs --daemon stop namenode
```

## 5. Limitaciones declaradas
- Un solo mes (enero 2020) y un nodo MongoDB local (sin replica set ni sharding real; el sharding es diseño).
- La línea base de anomalías es el mismo mes, no una climatología de 30 años.
- El job de Hadoop corre en modo local/pseudodistribuido, no en un clúster.
