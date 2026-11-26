# ==============================================================================
# EJERCICIO 1: CONTEO DE PALABRAS GUIADO (MAPREDUCE)
# Big Data - Universidad Catolica de Santa Maria
# ==============================================================================
from collections import defaultdict

registros = [
    ("R1", "datos para todos"),
    ("R2", "datos y decisiones"),
    ("R3", "para decidir con datos"),
    ("R4", "datos para decidir")
]

print("="*65)
print(" PRACTICA N 03 - EJERCICIO 1: CONTEO DE PALABRAS GUIADO")
print("="*65)

print("\n>>> FASE 1: MAP (Emision de pares clave-valor por registro)")
pares_intermedios = []
for r_id, texto in registros:
    palabras = texto.lower().split()
    pares_reg = [(palabra, 1) for palabra in palabras]
    pares_intermedios.extend(pares_reg)
    print(f"  {r_id} ('{texto}'):")
    print(f"     -> {pares_reg}")

print(f"\nTotal de pares clave-valor intermedios emitidos: {len(pares_intermedios)}")

print("\n>>> FASE 2: SHUFFLE & SORT (Particionamiento y orden alfabetico)")
grupos = defaultdict(list)
for palabra, valor in pares_intermedios:
    grupos[palabra].append(valor)

for palabra in sorted(grupos):
    print(f"  {palabra:<12} -> {grupos[palabra]}")

print("\n>>> FASE 3: REDUCE (Agregacion y sumatoria final)")
resultados = {}
for palabra in sorted(grupos):
    resultados[palabra] = sum(grupos[palabra])
    print(f"  {palabra:<12} -> {resultados[palabra]}")

print("\n>>> COMPROBACION DE INTEGRIDAD CUANTITATIVA:")
total_entrada = sum(len(texto.split()) for _, texto in registros)
total_salida = sum(resultados.values())
print(f"  Palabras en entrada bruta : {total_entrada}")
print(f"  Palabras en salida Reduce : {total_salida}")
print(f"  Estado de verificacion    : {'VALIDACION EXITOSA (13 = 13)' if total_entrada == total_salida else 'DISCREPANCIA'}")
print("="*65)
