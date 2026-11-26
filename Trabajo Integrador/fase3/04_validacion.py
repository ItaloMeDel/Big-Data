"""
Fase 3 - Validación independiente.
Recalcula con NumPy directamente desde los .nc (sin MongoDB) la temperatura media y la precipitación total
por dominio y día, y la compara con MongoDB (regional_stats_etl) y, si existe, con la salida de Hadoop.
Uso:  python 04_validacion.py            (compara)
      python 04_validacion.py --solo-ref (solo muestra la referencia NumPy)
"""
import datetime as dt
import json
import os
import sys

import netCDF4
import numpy as np
import pandas as pd

from common import F_ACC, F_INST, OUT_DIR, check_files, get_db


def referencia():
    check_files()
    inst, acc = netCDF4.Dataset(F_INST), netCDF4.Dataset(F_ACC)
    f = lambda x: np.ma.filled(x, np.nan).astype("float64")
    times = inst["valid_time"][:]
    nt = min(len(times), int(os.environ.get("ERA5_HORAS", len(times))))   # misma ventana que la ingesta
    times = times[:nt]
    land = f(inst["lsm"][0]) > 0.5
    t2m = np.round(f(inst["t2m"][:nt]) - 273.15, 2)
    tp = np.round(np.maximum(0.0, f(acc["tp"][:nt]) * 1000.0), 3)
    days = np.array([dt.datetime.fromtimestamp(int(t), dt.timezone.utc).day for t in times])
    rows = []
    for d in sorted(set(days)):
        k = days == d
        for nombre, mask in (("Continental_Peru", land), ("Pacific_Ocean", ~land)):
            rows.append({"domain": nombre, "day": int(d), "avg_temperature": round(float(t2m[k][:, mask].mean()), 2),
                         "total_precipitation": float(tp[k][:, mask].sum()),
                         "total_samples": int(k.sum() * mask.sum())})
    return pd.DataFrame(rows), int(len(times) * land.size)


def main():
    ref, n_esperado = referencia()
    print(f"Referencia NumPy: {len(ref)} filas (dominio x día), {n_esperado:,} observaciones esperadas")
    if "--solo-ref" in sys.argv:
        print(ref.head(6).to_string(index=False)); return
    db = get_db()
    res = {"observaciones_esperadas": n_esperado,
           "observaciones_en_mongodb": db["climate_observations"].count_documents({})}
    mg = pd.DataFrame(list(db["regional_stats_etl"].find({}, {"_id": 0})))
    m = ref.merge(mg, on=["domain", "day"], suffixes=("_np", "_mongo"))
    m["dif_temp"] = (m["avg_temperature_np"] - m["avg_temperature_mongo"]).abs()
    m["dif_precip"] = (m["total_precipitation"] - m["total_precipitation_volume"]).abs()
    res.update({"filas_comparadas": len(m), "max_dif_temp_C": round(float(m.dif_temp.max()), 4),
                "max_dif_precip_mm": round(float(m.dif_precip.max()), 3),
                "muestras_coinciden": bool((m.total_samples_np == m.total_samples_mongo).all())})
    ok = (len(m) == len(ref) and res["observaciones_esperadas"] == res["observaciones_en_mongodb"]
          and res["max_dif_temp_C"] <= 0.011 and res["max_dif_precip_mm"] <= 0.5 and res["muestras_coinciden"])
    hp = OUT_DIR / "hadoop_resultado.tsv"
    if hp.exists():
        h = pd.read_csv(hp, sep="\t", header=None, names=["clave", "avg_temperature", "total_precip", "count"])
        h[["domain", "day"]] = h["clave"].str.split("|", expand=True)
        h["day"] = h["day"].astype(int)
        mh = ref.merge(h, on=["domain", "day"])
        res["hadoop_filas"] = len(mh)
        res["hadoop_max_dif_temp_C"] = round(float((mh.avg_temperature_x - mh.avg_temperature_y).abs().max()), 4)
        res["hadoop_max_dif_precip_mm"] = round(float((mh.total_precipitation - mh.total_precip).abs().max()), 3)
        ok = ok and len(mh) == len(ref) and res["hadoop_max_dif_temp_C"] <= 0.011 and res["hadoop_max_dif_precip_mm"] <= 0.5
    res["VALIDACION_OK"] = bool(ok)
    (OUT_DIR / "resultado_validacion.json").write_text(json.dumps(res, indent=2))
    m.to_csv(OUT_DIR / "comparacion_numpy_mongo.csv", index=False)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
