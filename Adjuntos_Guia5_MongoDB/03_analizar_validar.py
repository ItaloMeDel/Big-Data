from collections import defaultdict
from pymongo import MongoClient
COLECCION = "ventas_masivas"
cliente = MongoClient(
   "mongodb://localhost:27017/",
   serverSelectionTimeoutMS=5000
)
try:
   cliente.admin.command("ping")
   ventas = cliente["guia5_bigdata"][COLECCION]
   if ventas.count_documents({}) == 0:
      raise RuntimeError("Primero ejecute el generador")
   etapas = [
      {"$group": {
         "_id": "$ciudad",
         "ventas": {"$sum": 1},
         "unidades": {"$sum": "$cantidad"},
         "ingresos": {"$sum": {
            "$multiply": ["$cantidad", "$precio"]
         }}
      }},
      {"$sort": {"ingresos": -1, "_id": 1}}
   ]
   resultados = list(ventas.aggregate(etapas))
   for fila in resultados:
      print(fila)
   independiente = defaultdict(
      lambda: {"ventas": 0, "unidades": 0, "ingresos": 0}
   )
   proyeccion = {
      "_id": 0, "ciudad": 1, "cantidad": 1, "precio": 1
   }
   for venta in ventas.find({}, proyeccion).batch_size(1000):
      fila = independiente[venta["ciudad"]]
      fila["ventas"] += 1
      fila["unidades"] += venta["cantidad"]
      fila["ingresos"] += venta["cantidad"] * venta["precio"]
   obtenido = {
      fila["_id"]: {
         "ventas": fila["ventas"],
         "unidades": fila["unidades"],
         "ingresos": fila["ingresos"]
      }
      for fila in resultados
   }
   if obtenido != dict(independiente):
      raise RuntimeError("No coinciden los dos cálculos")
   print("Validación correcta por ciudad")
   print("Total ventas:", sum(x["ventas"] for x in resultados))
   print("Total unidades:", sum(x["unidades"] for x in resultados))
   print("Total ingresos:", sum(x["ingresos"] for x in resultados))
finally:
   cliente.close()
