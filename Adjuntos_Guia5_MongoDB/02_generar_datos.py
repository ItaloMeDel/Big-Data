from datetime import datetime, timedelta, timezone
import random
from pymongo import MongoClient
TOTAL = 100_000
TAMANO_LOTE = 1_000
COLECCION = "ventas_masivas"
rng = random.Random(42)
ciudades = ["Arequipa", "Lima", "Cusco", "Tacna"]
productos = [
   ("Laptop", 2500), ("Mouse", 40),
   ("Teclado", 100), ("Monitor", 700)
]
inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
cliente = MongoClient(
   "mongodb://localhost:27017/",
   serverSelectionTimeoutMS=5000
)
try:
   cliente.admin.command("ping")
   ventas = cliente["guia5_bigdata"][COLECCION]
   existentes = ventas.count_documents({})
   if existentes:
      print("La colección ya contiene", existentes, "documentos.")
      print("No se agregaron datos. Verifique su carga anterior.")
   else:
      lote = []
      total_unidades = 0
      total_ingresos = 0
      for numero in range(1, TOTAL + 1):
          producto, precio = rng.choice(productos)
          ciudad = rng.choice(ciudades)
          cantidad = rng.randint(1, 5)
          fecha = inicio + timedelta(
              minutes=rng.randrange(100_000)
          )
          documento = {
              "_id": numero, "producto": producto,
              "ciudad": ciudad, "cantidad": cantidad,
              "precio": precio, "fecha": fecha
          }
          lote.append(documento)
          total_unidades += cantidad
          total_ingresos += cantidad * precio
          if len(lote) == TAMANO_LOTE:
              ventas.insert_many(lote)
              lote.clear()
              print("Insertados:", numero)
      if lote:
          ventas.insert_many(lote)
      print("Total en MongoDB:", ventas.count_documents({}))
      print("Unidades generadas:", total_unidades)
      print("Ingresos generados:", total_ingresos)
finally:
   cliente.close()
