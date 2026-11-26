"""Configuración común de la Fase 3 (ERA5 -> MongoDB). Todas las rutas se pueden cambiar con variables de entorno."""
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # carpeta "Trabajo Integrador"
DATA_DIR = pathlib.Path(os.environ.get("ERA5_DIR", ROOT / "era5_data"))
DB_NAME = os.environ.get("ERA5_DB", "era5_climate_db")      # la demo usa otra BD (era5_demo) para no pisar la principal
OUT_DIR = HERE / ("resultados" if DB_NAME == "era5_climate_db" else f"resultados_{DB_NAME}")
OUT_DIR.mkdir(exist_ok=True)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
F_INST = DATA_DIR / "data_stream-oper_stepType-instant.nc"
F_ACC = DATA_DIR / "data_stream-oper_stepType-accum.nc"


def get_db():
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[DB_NAME]


def check_files():
    for f in (F_INST, F_ACC):
        if not f.exists():
            raise SystemExit(f"No se encuentra {f}\nDescomprime el zip de ERA5 en {DATA_DIR} (ver README).")
