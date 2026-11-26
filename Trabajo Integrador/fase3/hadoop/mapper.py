#!/usr/bin/env python3
"""MAP: por cada observación emite  clave=dominio|dia  valor=temp<TAB>precip<TAB>1"""
import sys

for linea in sys.stdin:
    p = linea.rstrip("\n").split(",")
    if len(p) < 6 or p[0] == "domain":
        continue
    try:
        dominio, dia, temp, precip = p[0], int(p[1]), float(p[3]), float(p[4])
    except ValueError:
        continue          # regla de calidad: se descartan filas inválidas
    print(f"{dominio}|{dia:02d}\t{temp}\t{precip}\t1")
