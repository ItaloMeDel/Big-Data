# Plan (qué mostrar y por qué) — 7 min
1. 0:00-1:00  Problema + arquitectura (1 diapositiva).
2. 1:00-3:30  DEMO EN VIVO: "Ejecutar todo" con 168 h (~30 s). Cada integrante explica un paso mientras corre
              (ingesta/ETL, anomalías, MapReduce, validación).
3. 3:30-5:30  Pestaña Resultados: mapa de calor con slider (se ve costa–Andes–Amazonía), anomalías, click en celda,
              consulta geoespacial IXSCAN.
4. 5:30-6:30  Validación 3 vías (NumPy = Mongo = Hadoop) y números del mes completo (3,265,416 docs; 3,635 anomalías).
5. 6:30-7:00  Limitaciones (línea base de 31 días, Hadoop local, 1 nodo) y conclusión.
Respaldo: ten abiertas capturas de la BD principal por si falla el demo.
Antes de la expo: ensayar 1 vez completa, `podman start mongo`, venv + Java 11 activos, `git commit` del estado que funciona.
