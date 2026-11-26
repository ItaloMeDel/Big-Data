"""
Fase 3 - Anomalías térmicas diarias por celda.
Línea base: media y desviación estándar de la temperatura media diaria de cada celda durante el propio mes
(enero 2020). z = (T_dia - media_celda) / desv_celda ; anomalía si |z| > 2.
LIMITACIÓN: la base es el mismo mes, no una climatología de 30 años.
"""
import json

import pandas as pd

from common import OUT_DIR, get_db

Z_UMBRAL = 2.0


def main():
    db = get_db()
    df = pd.DataFrame(list(db["daily_climatology_etl"].find(
        {}, {"_id": 0, "day": 1, "latitude": 1, "longitude": 1, "domain": 1, "temp_mean": 1, "precip_total_mm": 1})))
    g = df.groupby(["latitude", "longitude"])["temp_mean"]
    df["temp_base"] = g.transform("mean")
    df["temp_std"] = g.transform(lambda s: s.std(ddof=0))
    df["z"] = ((df["temp_mean"] - df["temp_base"]) / df["temp_std"]).where(df["temp_std"] > 1e-4, 0.0)
    df["z"] = df["z"].round(3)
    df["is_anomaly"] = df["z"].abs() > Z_UMBRAL
    df["tipo"] = df["z"].apply(lambda z: "calida" if z > Z_UMBRAL else ("fria" if z < -Z_UMBRAL else "normal"))
    out = df.round({"temp_base": 2, "temp_std": 3}).to_dict("records")
    db["anomalies_daily"].drop()
    db["anomalies_daily"].insert_many(out)
    db["anomalies_daily"].create_index([("is_anomaly", 1), ("day", 1)])
    res = {"filas": len(df), "anomalias": int(df["is_anomaly"].sum()),
           "pct_anomalias": round(100 * df["is_anomaly"].mean(), 2),
           "calidas": int((df["tipo"] == "calida").sum()), "frias": int((df["tipo"] == "fria").sum()),
           "por_dominio": df.groupby("domain")["is_anomaly"].sum().astype(int).to_dict(),
           "dia_con_mas_anomalias": int(df[df.is_anomaly].groupby("day").size().idxmax())
           if df.is_anomaly.any() else None}
    (OUT_DIR / "resumen_anomalias.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
