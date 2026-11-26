"""
EJERCICIO 4: CALIDAD DE DATOS (REGLAS DE VALIDACION Y SANEAMIENTO)
Coleccion: pruebas_calidad en guia5_bigdata
"""
import json
from pathlib import Path
from pymongo import MongoClient

def validar(venta):
    # Regla 1: cantidad debe ser int positivo (excluyendo booleanos)
    if type(venta.get("cantidad")) is not int or venta["cantidad"] <= 0:
        return False, f"Cantidad invalida: {repr(venta.get('cantidad'))} (debe ser entero > 0)"
    
    # Regla 2: precio debe ser int positivo (excluyendo texto y booleanos)
    if type(venta.get("precio")) is not int or venta["precio"] <= 0:
        return False, f"Precio invalido: {repr(venta.get('precio'))} (debe ser entero > 0)"
    
    # Regla 3: ciudad debe ser cadena no vacia
    ciudad = venta.get("ciudad")
    if not isinstance(ciudad, str) or not ciudad.strip():
        return False, f"Ciudad vacia o no valida: {repr(ciudad)}"
        
    return True, "Valido"

if __name__ == "__main__":
    ruta_json = Path("Adjuntos_Guia5_MongoDB") / "pruebas_calidad.json"
    registros = json.loads(ruta_json.read_text(encoding="utf-8"))
    
    validos, rechazados = [], []
    for venta in registros:
        aceptado, causa = validar(venta)
        if aceptado:
            validos.append(venta)
        else:
            rechazados.append({"registro": venta, "causa": causa})
            
    print("="*65)
    print(" EJERCICIO 4: EVALUACION DE CALIDAD DE DATOS")
    print("="*65)
    print(f"Total registros analizados: {len(registros)}")
    print(f"Registros validos         : {len(validos)}")
    print(f"Registros rechazados      : {len(rechazados)}")
    
    print("\nDetalle de registros rechazados:")
    for r in rechazados:
        reg = r["registro"]
        print(f"  - _id: {reg['_id']} -> Causa: {r['causa']}")
        
    # Guardar en MongoDB coleccion pruebas_calidad con upsert
    cliente = MongoClient("mongodb://localhost:27017/")
    db = cliente["guia5_bigdata"]
    col = db["pruebas_calidad"]
    
    for v in validos:
        col.replace_one({"_id": v["_id"]}, v, upsert=True)
        
    print(f"\nDocumentos insertados en MongoDB (pruebas_calidad): {col.count_documents({})}")
    print("Muestra de documentos validos en MongoDB:")
    for doc in col.find():
        print(" ", doc)
        
    cliente.close()
