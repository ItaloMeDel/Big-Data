"""
EJERCICIO 5: CASO DE ESTUDIO ORIGINAL DEL EQUIPO
Monitoreo de Sensores Ambientales y Calidad del Aire (Smart Campus EPIS - UCSM)
Coleccion: sensores_campus en guia5_bigdata
"""
import random
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pymongo import MongoClient

TOTAL = 10_000
TAMANO_LOTE = 500
COLECCION = "sensores_campus"
SEMILLA = 100

rng = random.Random(SEMILLA)
aulas = ["Pabellon-A", "Pabellon-B", "Lab-Sistemas", "Auditorio"]
sensores_por_aula = {
    "Pabellon-A": "SNS-A101",
    "Pabellon-B": "SNS-B202",
    "Lab-Sistemas": "SNS-SIS3",
    "Auditorio": "SNS-AUD4"
}
inicio = datetime(2026, 3, 1, tzinfo=timezone.utc)

cliente = MongoClient("mongodb://localhost:27017/")
db = cliente["guia5_bigdata"]
col = db[COLECCION]

print("="*68)
print(" EJERCICIO 5: MONITOREO DE SENSORES EN CAMPUS UCSM")
print("="*68)

# 1. Carga por lotes con verificacion de idempotencia
existentes = col.count_documents({})
if existentes > 0:
    print(f"La coleccion ya contiene {existentes} registros. Carga omitida para idempotencia.")
else:
    print(f"Generando {TOTAL} lecturas sinteticas con semilla {SEMILLA}...")
    lote = []
    for i in range(1, TOTAL + 1):
        aula = rng.choice(aulas)
        sensor = sensores_por_aula[aula]
        co2 = rng.randint(400, 1800) # ppm
        temp = round(rng.uniform(18.0, 28.5), 1) # Celsius
        fecha = inicio + timedelta(minutes=rng.randrange(43_200)) # 30 dias
        
        doc = {
            "_id": i,
            "sensor_id": sensor,
            "aula": aula,
            "co2_ppm": co2,
            "temperatura_c": temp,
            "timestamp": fecha
        }
        lote.append(doc)
        if len(lote) == TAMANO_LOTE:
            col.insert_many(lote)
            lote.clear()
    if lote:
        col.insert_many(lote)
    print(f"Carga completada exitosamente. Total en MongoDB: {col.count_documents({})}")

# 2. Dos Filtros Analiticos
print("\n>>> FILTRO 1: Alertas de Co2 Critico (> 1200 ppm)")
conteo_alertas = col.count_documents({"co2_ppm": {"$gt": 1200}})
print(f"Total de lecturas en estado critico de ventilacion: {conteo_alertas}")

print("\n>>> FILTRO 2: Lecturas en Lab-Sistemas en las primeras 24 horas")
f_ini = datetime(2026, 3, 1, tzinfo=timezone.utc)
f_fin = datetime(2026, 3, 2, tzinfo=timezone.utc)
filtro_lab = {"aula": "Lab-Sistemas", "timestamp": {"$gte": f_ini, "$lt": f_fin}}
conteo_lab_dia1 = col.count_documents(filtro_lab)
print(f"Total de lecturas registradas en Lab-Sistemas (Dia 1): {conteo_lab_dia1}")

# 3. Pipeline de Agregacion
print("\n>>> AGREGACION: Metricas Ambientales y Alertas por Aula")
pipeline = [
    {"$group": {
        "_id": "$aula",
        "lecturas": {"$sum": 1},
        "co2_promedio": {"$avg": "$co2_ppm"},
        "temp_promedio": {"$avg": "$temperatura_c"},
        "alertas_co2": {"$sum": {"$cond": [{"$gt": ["$co2_ppm", 1200]}, 1, 0]}}
    }},
    {"$sort": {"_id": 1}}
]
res_agg = list(col.aggregate(pipeline))
print(f"{'Aula / Ambiente':<16} | {'Lecturas':<9} | {'CO2 Prom (ppm)':<16} | {'Temp Prom (C)':<15} | {'Alertas CO2':<12}")
print("-" * 75)
for r in res_agg:
    print(f"{r['_id']:<16} | {r['lecturas']:<9} | {r['co2_promedio']:<16.2f} | {r['temp_promedio']:<15.2f} | {r['alertas_co2']:<12}")
print("-" * 75)

# 4. Validacion Independiente Secuencial en Python
print("\n>>> VALIDACION INDEPENDIENTE SECUENCIAL:")
acum_py = defaultdict(lambda: {"lecturas": 0, "sum_co2": 0, "sum_temp": 0.0, "alertas": 0})
for d in col.find({}, {"_id": 0, "aula": 1, "co2_ppm": 1, "temperatura_c": 1}):
    a = d["aula"]
    acum_py[a]["lecturas"] += 1
    acum_py[a]["sum_co2"] += d["co2_ppm"]
    acum_py[a]["sum_temp"] += d["temperatura_c"]
    if d["co2_ppm"] > 1200:
        acum_py[a]["alertas"] += 1

valido = True
for r in res_agg:
    a = r["_id"]
    p = acum_py[a]
    if r["lecturas"] != p["lecturas"] or abs(r["co2_promedio"] - (p["sum_co2"]/p["lecturas"])) > 0.01:
        valido = False

print(f"Estado de comprobacion independiente: {'VALIDACION EXITOSA (100% concordancia)' if valido else 'ERROR'}")

# 5. Justificacion y Evaluacion de Indice Compuesto (aula, timestamp)
print("\n>>> EVALUACION DE INDICE COMPUESTO (aula: 1, timestamp: 1):")
# Explain antes de crear indice especifico (si existe, evaluamos)
exp_antes = db.command({
    "explain": {"find": COLECCION, "filter": filtro_lab},
    "verbosity": "executionStats"
})["executionStats"]
print(f"  Antes de indice -> Docs examinados: {exp_antes['totalDocsExamined']} | Keys: {exp_antes['totalKeysExamined']} | ms: {exp_antes['executionTimeMillis']}")

# Crear indice compuesto
col.create_index([("aula", 1), ("timestamp", 1)])

exp_despues = db.command({
    "explain": {"find": COLECCION, "filter": filtro_lab},
    "verbosity": "executionStats"
})["executionStats"]
print(f"  Despues de indice -> Docs examinados: {exp_despues['totalDocsExamined']} | Keys: {exp_despues['totalKeysExamined']} | ms: {exp_despues['executionTimeMillis']}")
print(f"  Reduccion de documentos examinados: {exp_antes['totalDocsExamined']} -> {exp_despues['totalDocsExamined']} (Optimizacion de {((1 - exp_despues['totalDocsExamined']/exp_antes['totalDocsExamined'])*100):.1f}%)")

cliente.close()
