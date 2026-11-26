# ==============================================================================
# EJERCICIO 2: PLATAFORMA ACADEMICA VIRTUAL (MAPREDUCE)
# Big Data - Universidad Catolica de Santa Maria
# ==============================================================================
from collections import defaultdict

eventos_raw = [
    ("D1", "A", "acceso"),
    ("D2", "B", "acceso"),
    ("D3", "A", "descarga"),
    ("D4", "A", "acceso"),
    ("D5", "B", "descarga"),
    ("D6", "A", "descarga"),
    ("D7", "B", "acceso"),
    ("D8", "C", "acceso")
]

print("="*65)
print(" PRACTICA N 03 - EJERCICIO 2: EVENTOS EN PLATAFORMA ACADEMICA")
print("="*65)

print("\n>>> FASE 1: MAP (Clave compuesta: (curso, evento))")
pares_intermedios = []
for d_id, curso, evento in eventos_raw:
    clave = (curso, evento)
    pares_intermedios.append((clave, 1))
    print(f"  {d_id}: ({curso}, {evento}) -> clave: {clave}, valor: 1")

print(f"\nTotal eventos intermedios procesados: {len(pares_intermedios)}")

print("\n>>> FASE 2: SHUFFLE & SORT (Agrupacion por par ordenado)")
grupos = defaultdict(list)
for clave, valor in pares_intermedios:
    grupos[clave].append(valor)

for clave in sorted(grupos):
    print(f"  {str(clave):<18} -> {grupos[clave]}")

print("\n>>> FASE 3: REDUCE (Conteo por clave compuesta)")
resultados = {}
for clave in sorted(grupos):
    resultados[clave] = sum(grupos[clave])
    print(f"  {str(clave):<18} -> {resultados[clave]}")

print("\n>>> CONSOLIDACION DE METRICAS POR CURSO:")
cursos = defaultdict(lambda: {"acceso": 0, "descarga": 0, "total": 0})
for (curso, evento), conteo in resultados.items():
    cursos[curso][evento] += conteo
    cursos[curso]["total"] += conteo

for curso in sorted(cursos):
    c_data = cursos[curso]
    print(f"  Curso {curso}: {c_data['acceso']} accesos, {c_data['descarga']} descargas | Total = {c_data['total']} eventos")

total_eventos = sum(c["total"] for c in cursos.values())
print(f"\nTotal general de eventos contabilizados: {total_eventos}")
print(f"Verificacion frente a registros brutos : {'CORRECTO (8 = 8)' if total_eventos == len(eventos_raw) else 'ERROR'}")
print("="*65)
