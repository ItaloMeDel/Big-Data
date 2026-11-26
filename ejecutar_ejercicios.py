from pymongo import MongoClient
import json
from pathlib import Path

cliente = MongoClient("mongodb://localhost:27017/")
db = cliente["guia5_bigdata"]

print("="*65)
print(" EJERCICIO 1: CONSULTAS SOBRE LAS CUATRO VENTAS ORIGINALES")
print("="*65)

# a) Laptops
print("\n>>> 1.a) Ventas de Laptop:")
for doc in db.ventas_demo.find({"producto": "Laptop"}):
    print(" ", doc)

# b) Cantidad >= 3
print("\n>>> 1.b) Ventas con cantidad >= 3:")
for doc in db.ventas_demo.find({"cantidad": {"$gte": 3}}):
    print(" ", doc)

# c) Mostrar producto y cantidad sin _id
print("\n>>> 1.c) Proyeccion de producto y cantidad (sin _id):")
for doc in db.ventas_demo.find({}, {"_id": 0, "producto": 1, "cantidad": 1}):
    print(" ", doc)

# d) Calcular unidades por ciudad
print("\n>>> 1.d) Unidades totales por ciudad:")
pipe_1d = [
    {"$group": {"_id": "$ciudad", "unidades": {"$sum": "$cantidad"}}},
    {"$sort": {"_id": 1}}
]
res_1d = list(db.ventas_demo.aggregate(pipe_1d))
for r in res_1d:
    print(f"  Ciudad: {r['_id']:<10} | Unidades: {r['unidades']}")
total_u_1d = sum(r['unidades'] for r in res_1d)
print(f"  TOTAL UNIDADES: {total_u_1d} (Verificacion: {'CORRECTO' if total_u_1d == 11 else 'ERROR'})")

print("\n" + "="*65)
print(" EJERCICIO 2: AGREGACION POR PRODUCTO EN VENTAS MASIVAS")
print("="*65)

pipe_2 = [
    {"$group": {
        "_id": "$producto",
        "ventas": {"$sum": 1},
        "unidades": {"$sum": "$cantidad"},
        "ingresos": {"$sum": {"$multiply": ["$cantidad", "$precio"]}}
    }},
    {"$sort": {"ingresos": -1}}
]
res_2 = list(db.ventas_masivas.aggregate(pipe_2))
print(f"{'Producto':<12} | {'Ventas':<8} | {'Unidades':<10} | {'Ingresos (S/)':<14}")
print("-" * 52)
for r in res_2:
    print(f"{r['_id']:<12} | {r['ventas']:<8} | {r['unidades']:<10} | S/ {r['ingresos']:<12}")
print("-" * 52)
total_ing_prod = sum(r['ingresos'] for r in res_2)
total_v_prod = sum(r['ventas'] for r in res_2)
total_u_prod = sum(r['unidades'] for r in res_2)
print(f"{'TOTAL':<12} | {total_v_prod:<8} | {total_u_prod:<10} | S/ {total_ing_prod:<12}")
print(f"Verificacion de ingresos frente a ciudades: {'COINCIDENCIA EXACTA (251,220,720)' if total_ing_prod == 251220720 else 'ERROR'}")

print("\n" + "="*65)
print(" EJERCICIO 3: FILTRO MATCH ANTES DE GROUP (AREQUIPA)")
print("="*65)

pipe_3 = [
    {"$match": {"ciudad": "Arequipa"}},
    {"$group": {
        "_id": "$producto",
        "ventas": {"$sum": 1},
        "unidades": {"$sum": "$cantidad"},
        "ingresos": {"$sum": {"$multiply": ["$cantidad", "$precio"]}}
    }},
    {"$sort": {"ingresos": -1}}
]
res_3 = list(db.ventas_masivas.aggregate(pipe_3))
print(f"{'Producto':<12} | {'Ventas':<8} | {'Unidades':<10} | {'Ingresos Arequipa (S/)':<22}")
print("-" * 60)
for r in res_3:
    print(f"{r['_id']:<12} | {r['ventas']:<8} | {r['unidades']:<10} | S/ {r['ingresos']:<18}")
print("-" * 60)
total_ing_aqp = sum(r['ingresos'] for r in res_3)
print(f"Total ingresos Arequipa (filtrado previo) : S/ {total_ing_aqp}")
print(f"Ingresos Arequipa en Actividad 8          : S/ 63777500")
print(f"Verificacion cruzada                      : {'COINCIDENCIA EXACTA (100%)' if total_ing_aqp == 63777500 else 'DISCREPANCIA'}")

cliente.close()
