#!/usr/bin/env python3
"""REDUCE: la entrada llega ordenada por clave (shuffle & sort). Emite clave, temp media, precip total, conteo."""
import sys
from itertools import groupby

def leer():
    for linea in sys.stdin:
        k, t, p, c = linea.rstrip("\n").split("\t")
        yield k, float(t), float(p), int(c)

for clave, grupo in groupby(leer(), key=lambda x: x[0]):
    st = sp = 0.0
    n = 0
    for _, t, p, c in grupo:
        st += t; sp += p; n += c
    print(f"{clave}\t{st / n:.2f}\t{sp:.2f}\t{n}")
