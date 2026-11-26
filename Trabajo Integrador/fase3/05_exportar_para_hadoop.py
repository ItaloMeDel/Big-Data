"""Exporta desde MongoDB las observaciones (dominio, día, hora, temp, precip, viento) a CSV para MapReduce/HDFS."""
import csv

from common import OUT_DIR, get_db


def main():
    db = get_db()
    ruta = OUT_DIR / "era5_obs.csv"
    cur = db["climate_observations"].find({}, {"_id": 0, "geo.domain": 1, "day": 1, "hour": 1,
                                                "measurements.temperature_c": 1,
                                                "measurements.precipitation_mm": 1,
                                                "measurements.wind_speed_ms": 1}, batch_size=50000)
    n = 0
    with open(ruta, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "day", "hour", "temperature_c", "precipitation_mm", "wind_speed_ms"])
        for d in cur:
            m = d["measurements"]
            w.writerow([d["geo"]["domain"], d["day"], d["hour"], m["temperature_c"],
                        m["precipitation_mm"], m["wind_speed_ms"]])
            n += 1
    print(f"{n:,} filas exportadas a {ruta}")


if __name__ == "__main__":
    main()
