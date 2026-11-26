# Proyecto: ERA5 + MongoDB + Hadoop (UCSM, Big Data) — expo 2026-11-26
Responde en español, breve. No expliques lo que haces; solo código y 1-2 líneas de resultado.

## Reglas para ahorrar tokens
- NO leas archivos completos ni explores el repo. Usa `grep -n` / `sed -n 'a,bp'` y solo lo necesario.
- NO leas ni listes: `era5_data/`, `resultados*/`, `latex/`, `*.nc`, `*.csv`, `*.png`.
- NO ejecutes la ingesta completa (744 h). Para probar usa `ERA5_HORAS=24 ERA5_DB=era5_demo`.
- Cambios mínimos y localizados (Edit, no reescribir archivos). Sin refactors. Sin dependencias nuevas.
- Prueba solo lo que cambiaste. Si algo falla 2 veces, detente y dime el error.

## Contexto fijo (no lo re-descubras)
- Datos: ERA5 ene-2020, 744 h, grilla 77 lat × 57 lon, paso 0.25° = 4,389 celdas, lat 0→-19, lon -82→-68. 3,265,416 observaciones.
- MongoDB 8 en podman, `mongodb://localhost:27017`, BD principal `era5_climate_db` (NO tocar), demo `era5_demo`.
- Colecciones: climate_observations (GeoJSON `location`, timestamp, temperature_c, precipitation_mm, wind_speed_ms, domain, lat, lon),
  spatial_grid_catalog, daily_climatology_etl, regional_stats_etl, anomalies_daily.
- Índices: idx_geo_2dsphere, idx_timestamp_lat_lon, idx_temp_c, idx_precip_mm, idx_domain.
- Dominios: Continental_Peru, Pacific_Ocean. Anomalía = |z|>2 sobre media/desv diaria por celda (línea base = el mismo mes).
- Hadoop 3.3.6 + Java 11, Streaming (fase3/hadoop/mapper.py, reducer.py), modo local. Resultado en resultados/hadoop_resultado.tsv.
- Scripts en `fase3/`: 01_ingesta_completa, 02_anomalias, 03_visualizaciones, 04_validacion, 05_exportar_para_hadoop, demo_ui.py (UI stdlib, puerto 8765).
- Env: `ERA5_HORAS`, `ERA5_DB`, `RES_DIR`, `MONGO_URI`. Resultados de la BD demo van a `fase3/resultados_era5_demo/`.
- Ejecutar con venv activo (`source ~/venv-bd/bin/activate`), SIN `python -I`.

## Reglas de la UI
- Solo biblioteca estándar en el servidor; el front es HTML/JS/canvas/SVG vanilla. Sin CDN (puede no haber internet en la expo).
- La UI debe leer datos reales de Mongo/resultados, nunca números inventados.
- Mongo solo en 127.0.0.1. Una ejecución a la vez.

## Rutas (IMPORTANTE)
- Este repo tiene muchos archivos de OTRAS prácticas (PracticaNo3/4, compass_*.png, ejercicio*.py, JINIS, img, Adjuntos_*). IGNÓRALOS por completo.
- Solo se trabaja en `Trabajo Integrador/fase3/`. Donde este archivo y PROMPTS.md dicen `fase3/`, es `Trabajo Integrador/fase3/` (la ruta tiene un espacio: ponla entre comillas).
- No hagas `ls` ni `find` en la raíz. Entra directo con `cd "Trabajo Integrador/fase3"`.
