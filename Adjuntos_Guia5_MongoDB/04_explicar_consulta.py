from datetime import datetime, timezone
from pymongo import MongoClient
with MongoClient("mongodb://localhost:27017/",
            serverSelectionTimeoutMS=5000) as cliente:
   base = cliente["guia5_bigdata"]
   filtro = {"fecha": {
      "$gte": datetime(2026, 1, 10, tzinfo=timezone.utc),
      "$lt": datetime(2026, 1, 11, tzinfo=timezone.utc)
   }}
   resultado = base.command({
      "explain": {"find": "ventas_masivas", "filter": filtro},
      "verbosity": "executionStats"
   })
   datos = resultado["executionStats"]
   for nombre in ["nReturned", "totalDocsExamined",
            "totalKeysExamined", "executionTimeMillis"]:
      print(nombre, datos[nombre])
