"""Fase 3 - Figuras para el artículo y la exposición (se guardan en resultados/)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from common import OUT_DIR, get_db


def grid(df, col):
    return df.pivot_table(index="latitude", columns="longitude", values=col, aggfunc="mean").sort_index()


def mapa(m, titulo, cbar, nombre, cmap):
    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(m.values, origin="lower", cmap=cmap, aspect="auto",
                   extent=[m.columns.min(), m.columns.max(), m.index.min(), m.index.max()])
    ax.set_xlabel("Longitud (°)"); ax.set_ylabel("Latitud (°)"); ax.set_title(titulo)
    fig.colorbar(im, ax=ax, label=cbar)
    fig.tight_layout(); fig.savefig(OUT_DIR / nombre, dpi=200); plt.close(fig)


def main():
    db = get_db()
    reg = pd.DataFrame(list(db["regional_stats_etl"].find({}, {"_id": 0}))).sort_values("day")
    dia = pd.DataFrame(list(db["daily_climatology_etl"].find({}, {"_id": 0, "location": 0})))
    an = pd.DataFrame(list(db["anomalies_daily"].find({}, {"_id": 0})))

    fig, ax = plt.subplots(figsize=(7, 3.6))
    for d, s in reg.groupby("domain"):
        ax.plot(s["day"], s["avg_temperature"], marker="o", ms=3, label=d.replace("_", " "))
    ax.set_xlabel("Día de enero de 2020"); ax.set_ylabel("Temperatura media a 2 m (°C)")
    ax.set_title("Temperatura media diaria por dominio"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT_DIR / "fig_serie_temperatura.png", dpi=200); plt.close(fig)

    mapa(grid(dia, "temp_mean"), "Temperatura media de enero 2020", "°C", "fig_mapa_temperatura.png", "inferno")
    mapa(grid(an.assign(a=an.is_anomaly.astype(int)), "a").mul(an["day"].nunique()),
         "Días con anomalía térmica (|z|>2) por celda", "días", "fig_mapa_anomalias.png", "viridis")

    ext = pd.DataFrame(list(db["climate_observations"].aggregate([
        {"$match": {"derived.is_extreme_precip": True}},
        {"$group": {"_id": {"day": "$day", "domain": "$geo.domain"}, "n": {"$sum": 1}}}], allowDiskUse=True)))
    if len(ext):
        ext["day"] = ext["_id"].apply(lambda x: x["day"]); ext["domain"] = ext["_id"].apply(lambda x: x["domain"])
        p = ext.pivot_table(index="day", columns="domain", values="n", aggfunc="sum").fillna(0)
        ax = p.plot(kind="bar", stacked=True, figsize=(7, 3.6), width=.85)
        ax.set_xlabel("Día de enero de 2020"); ax.set_ylabel("Observaciones con precip. > 5 mm/h")
        ax.set_title("Eventos de precipitación extrema por día"); ax.legend(title="")
        ax.figure.tight_layout(); ax.figure.savefig(OUT_DIR / "fig_precip_extrema.png", dpi=200); plt.close(ax.figure)

    tops = an[an.is_anomaly].sort_values("z", key=abs, ascending=False).head(10)
    tops.to_csv(OUT_DIR / "top10_anomalias.csv", index=False)
    print("Figuras y top10_anomalias.csv guardados en", OUT_DIR)


if __name__ == "__main__":
    main()
