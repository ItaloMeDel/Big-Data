# ==============================================================================
# EJERCICIO 3: CASO ORIGINAL - SOPORTE TECNICO EN LABORATORIOS (EPIS - UCSM)
# Big Data - Universidad Catolica de Santa Maria
# ==============================================================================
from collections import defaultdict

registros_brutos = [
    ("TK-101", "Lab-Redes", "Hardware", 45),
    ("TK-102", "Lab-Software", "Software", 20),
    ("TK-103", "Lab-Redes", "Conectividad", 60),
    ("TK-104", "Lab-IA", "Software", 35),
    ("TK-105", "Lab-Software", "Hardware", 50),
    ("TK-101", "Lab-Redes", "Hardware", 45),     # Duplicado
    ("TK-106", "Lab-Redes", "Software", 25),
    ("TK-107", "Lab-IA", "Conectividad", 40),
    ("TK-108", "Lab-Software", "Software", 15),
    ("TK-109", "   ", "Hardware", 30),           # Campo laboratorio vacio
    ("TK-110", "Lab-IA", "DESCONOCIDO", -15),     # Categoria y tiempo invalidos
    ("TK-111", "Lab-Redes", "Conectividad", 55)
]

print("="*70)
print(" PRACTICA N 03 - EJERCICIO 3: GESTION DE INCIDENCIAS EN LABORATORIOS")
print("="*70)

print("\n>>> FASE 1: SANEAMIENTO Y MAP (Tratamiento de casos limite)")
pares_intermedios = []
vistos = set()
excluidos = []

for tk_id, lab, cat, tiempo in registros_brutos:
    lab_limpio = lab.strip()
    if tk_id in vistos:
        excluidos.append((tk_id, lab, "Duplicado de ticket"))
        continue
    if not lab_limpio:
        excluidos.append((tk_id, lab, "Campo laboratorio vacio"))
        continue
    if tiempo <= 0 or cat == "DESCONOCIDO":
        excluidos.append((tk_id, lab, f"Parametros invalidos (Cat: {cat}, T: {tiempo}m)"))
        continue
    
    vistos.add(tk_id)
    pares_intermedios.append((lab_limpio, (1, tiempo)))
    print(f"  [VALIDO]   {tk_id} -> Clave: '{lab_limpio}', Valor: (1 ticket, {tiempo} min)")

print(f"\nResumen de saneamiento:")
print(f"  Registros brutos recibidos : {len(registros_brutos)}")
print(f"  Registros excluidos        : {len(excluidos)}")
for tid, lab, motivo in excluidos:
    print(f"    * {tid} [{lab}]: {motivo}")
print(f"  Registros admitidos        : {len(pares_intermedios)}")

print("\n>>> FASE 2: SHUFFLE & SORT (Agrupacion aditiva por laboratorio)")
grupos = defaultdict(list)
for lab, val in pares_intermedios:
    grupos[lab].append(val)

for lab in sorted(grupos):
    print(f"  {lab:<15} -> {grupos[lab]}")

print("\n>>> FASE 3: REDUCE (Agregacion y calculo ponderado de promedios)")
resultados = {}
print(f"  {'Laboratorio':<15} | {'Tickets':<8} | {'Tiempo Total':<14} | {'Tiempo Promedio':<15}")
print("  " + "-"*60)
for lab in sorted(grupos):
    conteo = sum(item[0] for item in grupos[lab])
    tiempo_total = sum(item[1] for item in grupos[lab])
    promedio = tiempo_total / conteo
    resultados[lab] = (conteo, tiempo_total, promedio)
    print(f"  {lab:<15} | {conteo:<8} | {tiempo_total:<9} min | {promedio:<6.2f} min/ticket")

print("  " + "-"*60)
total_tickets = sum(r[0] for r in resultados.values())
total_tiempo = sum(r[1] for r in resultados.values())
prom_global = total_tiempo / total_tickets
print(f"  {'TOTAL CONSOLIDADO':<15} | {total_tickets:<8} | {total_tiempo:<9} min | {prom_global:<6.2f} min/ticket")

print("\n>>> VALIDACION INDEPENDIENTE:")
print(f"  Suma manual de tiempos de registros validos = 45+20+60+35+50+25+40+15+55 = 345 min")
print(f"  Tiempo total acumulado en Reduce            = {total_tiempo} min")
print(f"  Estado de verificacion                      = {'CONCORDANCIA EXACTA (100%)' if total_tiempo == 345 else 'ERROR'}")
print("="*70)
