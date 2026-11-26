from pymongo import MongoClient
from pymongo.errors import PyMongoError
cliente = MongoClient(
   "mongodb://localhost:27017/",
   serverSelectionTimeoutMS=5000
)
try:
   cliente.admin.command("ping")
   print("Conexión correcta")
   ventas = cliente["guia5_bigdata"]["ventas_demo"]
   print("Total:", ventas.count_documents({}))
   filtro = {"ciudad": "Arequipa"}
   for venta in ventas.find(filtro, {"_id": 0}):
      print(venta)
except PyMongoError as error:
   print("Error de MongoDB:", error)
   raise
finally:
   cliente.close()
