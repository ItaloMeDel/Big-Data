# Prompts para Claude Code (pégalos UNO por vez; haz /clear entre fases)

## Fase 0 — arranque (1 vez)
Lee solo CLAUDE.md. Ya existe fase3/demo_ui.py (UI con botones por paso). NO lo reescribas.
Dime en 5 líneas qué funciones tiene (grep de "def " y "STEPS"), nada más.

## Fase 1 — datos reales para visualizar (endpoint /api/viz/*)
En fase3/demo_ui.py agrega endpoints GET JSON que consulten Mongo (BD según ?db=) y devuelvan, ya agregados y pequeños:
1. /api/viz/grid?day=N&var=temp|anom|precip → matriz 57×77 (lat×lon) con valores (temp media del día desde daily_climatology_etl; z desde anomalies_daily; precip desde regional/obs agregada). Redondea a 2 decimales.
2. /api/viz/hovmoller?var=temp|anom → matriz lat(57)×día promediando longitud.
3. /api/viz/cell?lat=&lon= → serie diaria de esa celda (temp, z, flag anomalía).
4. /api/viz/geo?lat=&lon=&km=50 → corre $geoNear/$geoWithin sobre climate_observations (límite 1 día) y devuelve: n docs, executionTimeMillis, stage del plan (IXSCAN/COLLSCAN) usando explain("executionStats").
No toques el resto. Prueba con ERA5_DB=era5_demo y curl.

## Fase 2 — pestaña "Resultados" con mapas de calor (canvas, sin librerías)
En demo_ui.py agrega una pestaña "Resultados" (mismo HTML embebido) con:
- Mapa de calor de temperatura (canvas) con slider de día 1–31 y botón ▶ animar; escala de color viridis/turbo + leyenda en °C. Contorno aproximado de costa opcional (omitir si complica).
- Mapa de calor de anomalías (azul=frío, rojo=cálido, z∈[-4,4]) con el mismo slider.
- Hovmöller (latitud × día) de temperatura o anomalía, selector.
- Click en una celda del mapa → gráfico de línea de esa celda (/api/viz/cell) con los días anómalos marcados.
- Tarjeta "Consulta geoespacial en vivo": click en mapa + radio → /api/viz/geo y muestra "IXSCAN vs COLLSCAN, n docs, ms".
Estilo limpio, mismo CSS. Tooltip con lat/lon/valor al pasar el mouse. Prueba con un screenshot headless solo si es barato; si no, dime cómo probar a mano.

## Fase 3 — comparación índice vs sin índice (para la sustentación)
Agrega botón "Comparar con/sin índice": ejecuta la misma consulta geoespacial/rango de temperatura con y sin .hint({$natural:1}) y muestra tiempos y docs examinados en dos barras. Solo en BD demo.

## Fase 4 — ensayo y pulido
Revisa que "Ejecutar todo" con 168 h termine sin error en era5_demo y que la pestaña Resultados cargue después. Corrige solo lo que falle. Añade al README fase3 un párrafo de uso de la UI (5 líneas).
