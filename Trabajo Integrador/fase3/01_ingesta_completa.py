"""
Fase 3 - Ingesta completa ERA5 (744 h de enero 2020 = 3,265,416 documentos) a MongoDB.
Mismo esquema BSON que la Fase 2 (Sec. VI-B del artículo). Escribe resultados/metricas_ingesta.json
"""
import datetime as dt
import json
import os
import time

import netCDF4
import numpy as np
from pymongo import ASCENDING, GEOSPHERE
from pymongo.write_concern import WriteConcern

from common import F_ACC, F_INST, OUT_DIR, check_files, get_db

BATCH_SIZE = 15000


def f64(x):
    return np.ma.filled(x, np.nan).astype("float64")


def main():
    check_files()
    t_start = time.time()
    db = get_db()
    (OUT_DIR / "hadoop_resultado.tsv").unlink(missing_ok=True)   # evita comparar contra una corrida anterior
    for c in ("climate_observations", "daily_climatology_etl", "regional_stats_etl",
              "spatial_grid_catalog", "anomalies_daily"):
        db[c].drop()

    inst, acc = netCDF4.Dataset(F_INST), netCDF4.Dataset(F_ACC)
    lats, lons = f64(inst["latitude"][:]), f64(inst["longitude"][:])
    times = inst["valid_time"][:]
    nt, nlat, nlon = len(times), len(lats), len(lons)
    nt = min(nt, int(os.environ.get("ERA5_HORAS", nt)))   # ERA5_HORAS=24 para una prueba rápida
    n = nlat * nlon
    lsm = f64(inst["lsm"][0])
    print(f"Grilla {nlat}x{nlon} = {n} celdas, {nt} horas -> {nt * n:,} documentos esperados")

    # --- catálogo espacial -------------------------------------------------
    lat_f = np.round(np.repeat(lats, nlon), 2).tolist()
    lon_f = np.round(np.tile(lons, nlat), 2).tolist()
    land = (lsm.ravel() > 0.5).tolist()
    dom = ["Continental_Peru" if x else "Pacific_Ocean" for x in land]
    ratio = np.round(lsm.ravel(), 4).tolist()
    db["spatial_grid_catalog"].insert_many([
        {"_id": f"gp_{la:.2f}_{lo:.2f}", "location": {"type": "Point", "coordinates": [lo, la]},
         "lat": la, "lon": lo, "is_land": isl, "land_sea_ratio": r, "domain": d}
        for la, lo, isl, r, d in zip(lat_f, lon_f, land, ratio, dom)])
    db["spatial_grid_catalog"].create_index([("location", GEOSPHERE)])

    # --- variables (todas las horas en memoria: ~13 MB por variable) -------
    t2m, skt = f64(inst["t2m"][:]), f64(inst["skt"][:])
    u10, v10 = f64(inst["u10"][:]), f64(inst["v10"][:])
    msl, sp, cape = f64(inst["msl"][:]), f64(inst["sp"][:]), f64(inst["cape"][:])
    tp = f64(acc["tp"][:])

    # Escritura masiva con semántica BASE (w=1, j=false), como en la Sec. V-B del artículo
    col = db.get_collection("climate_observations", write_concern=WriteConcern(w=1, j=False))
    batch, total = [], 0
    t_ing = time.time()
    for t in range(nt):
        ts = dt.datetime.fromtimestamp(int(times[t]), tz=dt.timezone.utc)
        tc = np.round(t2m[t].ravel() - 273.15, 2)
        sc = np.round(skt[t].ravel() - 273.15, 2)
        uu, vv = np.round(u10[t].ravel(), 2), np.round(v10[t].ravel(), 2)
        ws = np.round(np.sqrt(uu ** 2 + vv ** 2), 2)
        ml = np.round(msl[t].ravel() / 100.0, 2)
        sf = np.round(sp[t].ravel() / 100.0, 2)
        pr = np.round(np.maximum(0.0, tp[t].ravel() * 1000.0), 3)
        cp = np.round(cape[t].ravel(), 1)
        hi = np.round(tc + 0.1 * cp / 100.0, 2)
        ext = (pr > 5.0).tolist()
        for row in zip(lat_f, lon_f, land, dom, tc.tolist(), sc.tolist(), uu.tolist(), vv.tolist(),
                       ws.tolist(), ml.tolist(), sf.tolist(), pr.tolist(), cp.tolist(), hi.tolist(), ext):
            la, lo, isl, d, a, b, u, v, w, m, s, p, c, h, e = row
            batch.append({
                "timestamp": ts, "hour": ts.hour, "day": ts.day, "month": ts.month, "year": ts.year,
                "location": {"type": "Point", "coordinates": [lo, la]},
                "geo": {"latitude": la, "longitude": lo, "is_land": isl, "domain": d},
                "measurements": {"temperature_c": a, "skin_temp_c": b, "wind_u10": u, "wind_v10": v,
                                 "wind_speed_ms": w, "pressure_msl_hpa": m, "surface_pressure_hpa": s,
                                 "precipitation_mm": p, "cape": c},
                "derived": {"is_extreme_precip": e, "heat_index_proxy": h}})
        if len(batch) >= BATCH_SIZE:
            col.insert_many(batch, ordered=False)
            total += len(batch)
            batch = []
            if (t + 1) % 24 == 0:
                print(f"  hora {t + 1}/{nt}: {total:,} docs")
    if batch:
        col.insert_many(batch, ordered=False)
        total += len(batch)
    t_ing = time.time() - t_ing
    print(f"Ingesta: {total:,} docs en {t_ing:.2f} s ({total / t_ing:,.0f} docs/s)")

    # --- índices (Sec. VI-E) -----------------------------------------------
    t_idx = time.time()
    obs = db["climate_observations"]
    obs.create_index([("location", GEOSPHERE)], name="idx_geo_2dsphere")
    obs.create_index([("timestamp", ASCENDING), ("geo.latitude", ASCENDING), ("geo.longitude", ASCENDING)],
                     name="idx_timestamp_lat_lon")
    obs.create_index([("measurements.temperature_c", ASCENDING)], name="idx_temp_c")
    obs.create_index([("measurements.precipitation_mm", ASCENDING)], name="idx_precip_mm")
    obs.create_index([("geo.domain", ASCENDING)], name="idx_domain")
    t_idx = time.time() - t_idx
    print(f"Índices creados en {t_idx:.2f} s")

    # --- agregaciones (pipeline de agregación = etapa map/reduce en MongoDB) -
    t_agg = time.time()
    obs.aggregate([
        {"$group": {"_id": {"day": "$day", "lat": "$geo.latitude", "lon": "$geo.longitude", "domain": "$geo.domain"},
                    "temp_mean": {"$avg": "$measurements.temperature_c"},
                    "temp_max": {"$max": "$measurements.temperature_c"},
                    "temp_min": {"$min": "$measurements.temperature_c"},
                    "precip_total": {"$sum": "$measurements.precipitation_mm"},
                    "wind_max": {"$max": "$measurements.wind_speed_ms"},
                    "cape_mean": {"$avg": "$measurements.cape"},
                    "readings_count": {"$sum": 1}}},
        {"$project": {"_id": 0, "day": "$_id.day",
                      "location": {"type": "Point", "coordinates": ["$_id.lon", "$_id.lat"]},
                      "latitude": "$_id.lat", "longitude": "$_id.lon", "domain": "$_id.domain",
                      "temp_mean": {"$round": ["$temp_mean", 2]}, "temp_max": {"$round": ["$temp_max", 2]},
                      "temp_min": {"$round": ["$temp_min", 2]},
                      "precip_total_mm": {"$round": ["$precip_total", 3]},
                      "wind_max_ms": {"$round": ["$wind_max", 2]}, "cape_mean": {"$round": ["$cape_mean", 1]},
                      "readings_count": 1}},
        {"$out": "daily_climatology_etl"}], allowDiskUse=True)
    obs.aggregate([
        {"$group": {"_id": {"domain": "$geo.domain", "day": "$day"},
                    "avg_temperature": {"$avg": "$measurements.temperature_c"},
                    "max_precipitation": {"$max": "$measurements.precipitation_mm"},
                    "total_precipitation": {"$sum": "$measurements.precipitation_mm"},
                    "avg_wind_speed": {"$avg": "$measurements.wind_speed_ms"},
                    "total_samples": {"$sum": 1}}},
        {"$project": {"_id": 0, "domain": "$_id.domain", "day": "$_id.day",
                      "avg_temperature": {"$round": ["$avg_temperature", 2]},
                      "max_precipitation": {"$round": ["$max_precipitation", 3]},
                      "total_precipitation_volume": {"$round": ["$total_precipitation", 2]},
                      "avg_wind_speed": {"$round": ["$avg_wind_speed", 2]}, "total_samples": 1}},
        {"$out": "regional_stats_etl"}], allowDiskUse=True)
    t_agg = time.time() - t_agg
    print(f"Agregaciones en {t_agg:.2f} s")

    m = {"documentos_observaciones": db["climate_observations"].count_documents({}),
         "documentos_climatologia_diaria": db["daily_climatology_etl"].count_documents({}),
         "documentos_regionales": db["regional_stats_etl"].count_documents({}),
         "celdas_catalogo": db["spatial_grid_catalog"].count_documents({}),
         "horas": nt, "celdas": n,
         "segundos_ingesta": round(t_ing, 2), "docs_por_segundo": round(total / t_ing),
         "segundos_indices": round(t_idx, 2), "segundos_agregacion": round(t_agg, 2),
         "segundos_total": round(time.time() - t_start, 2),
         "tamano_coleccion_MB": round(db.command("collstats", "climate_observations")["size"] / 1e6, 1),
         "tamano_indices_MB": round(db.command("collstats", "climate_observations")["totalIndexSize"] / 1e6, 1)}
    (OUT_DIR / "metricas_ingesta.json").write_text(json.dumps(m, indent=2, ensure_ascii=False))
    print(json.dumps(m, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
