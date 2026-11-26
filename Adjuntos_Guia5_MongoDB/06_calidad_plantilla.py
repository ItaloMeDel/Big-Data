"""Ejercicio 4: completar la función antes de ejecutar. No carga datos aún."""
import json
from pathlib import Path

def validar(venta):
    # Retornar (True, "") o (False, causa).
    # type(valor) is int excluye booleanos; isinstance(True, int) no los excluye.
    raise NotImplementedError("Completar reglas de cantidad, precio y ciudad")

if __name__ == "__main__":
    registros = json.loads(Path(__file__).with_name("pruebas_calidad.json").read_text(encoding="utf-8"))
    validos, rechazados = [], []
    for venta in registros:
        aceptado, causa = validar(venta)
        if aceptado:
            validos.append(venta)
        else:
            rechazados.append({"registro": venta, "causa": causa})
    print("Válidos:", len(validos), "Rechazados:", len(rechazados))
    # Completar: guardar SOLO los válidos en pruebas_calidad, con _id estable y upsert.
    # Completar: guardar rechazados y causas en un archivo separado.
