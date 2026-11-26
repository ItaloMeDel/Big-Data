import csv
from pathlib import Path
from pymongo import MongoClient
with MongoClient("mongodb://localhost:27017/",
             serverSelectionTimeoutMS=5000) as cliente:
   ventas = cliente["guia5_bigdata"]["ventas_masivas"]
   etapas = [
      {"$group": {
         "_id": "$ciudad",
         "ventas": {"$sum": 1},
         "unidades": {"$sum": "$cantidad"},
         "ingresos": {"$sum": {
            "$multiply": ["$cantidad", "$precio"]
         }}
      }},
      {"$sort": {"_id": 1}}
   ]
   ruta = Path("resumen_ciudades.csv")
   with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
      escritor = csv.writer(archivo)
      escritor.writerow(["ciudad", "ventas", "unidades", "ingresos"])
      for fila in ventas.aggregate(etapas):
         escritor.writerow([
            fila["_id"], fila["ventas"],
            fila["unidades"], fila["ingresos"]
       ])
   print("Archivo creado:", ruta.resolve())
