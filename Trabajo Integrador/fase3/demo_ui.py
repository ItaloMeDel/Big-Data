#!/usr/bin/env python3
"""
Interfaz web local para EJECUTAR el pipeline ERA5 en vivo (solo biblioteca estándar, sin instalar nada).
Uso:   python demo_ui.py      ->  abre http://localhost:8765
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PORT = int(os.environ.get("DEMO_PORT", "8765"))
DRY = os.environ.get("DEMO_DRYRUN") == "1"          # solo para pruebas de la interfaz
PY = sys.executable
LOCK = threading.Lock()
DEFAULT_DB = "era5_climate_db"
DEMO_DB = "era5_demo"

STEPS = [
    {"id": "ingesta", "titulo": "1 · Ingesta y ETL: NetCDF → MongoDB",
     "inicio": "Leyendo los archivos NetCDF de ERA5 y preparando la conexión con MongoDB.",
     "que": ["Lee los dos NetCDF de ERA5 (variables instantáneas y acumuladas).",
             "Transforma cada celda-hora en un documento BSON: Kelvin→°C, metros→mm, viento=√(u²+v²), Pa→hPa, con coordenadas GeoJSON.",
             "Inserta en bloques de 15,000 documentos con w:1, j:false (semántica BASE para ingesta masiva).",
             "Crea 5 índices (2dsphere, compuesto espacio-tiempo y B-tree) y calcula la climatología diaria y las estadísticas regionales con el Aggregation Pipeline."],
     "decir": "Documentos = horas × 4,389 celdas. Los docs/s miden la velocidad de ingesta. Sin índices, las consultas harían COLLSCAN.",
     "cmds": [[PY, "-u", "01_ingesta_completa.py"]],
     "explain": [(r"^Grilla", "Archivos leídos: grilla de 77×57 celdas y N horas. Esa multiplicación es el número de documentos esperado."),
                 (r"hora \d+/\d+", "Transformando hora a hora (K→°C, m→mm, viento) y armando un documento BSON por celda-hora; se inserta en bloques de 15,000 con w:1, j:false."),
                 (r"^Ingesta:", "Carga masiva terminada. Ahora crea los índices para evitar escaneos completos (COLLSCAN)."),
                 (r"^Índices creados", "Índices listos. Ahora corre el Aggregation Pipeline ($group → $project → $out) para la climatología diaria y las estadísticas por dominio."),
                 (r"^Agregaciones en", "Agregaciones listas. Guardando métricas en metricas_ingesta.json.")]},
    {"id": "anomalias", "titulo": "2 · Detección de anomalías térmicas",
     "inicio": "Leyendo la climatología diaria de cada celda desde MongoDB.",
     "que": ["Toma la temperatura media diaria de cada celda (una por día).",
             "Calcula z = (T del día − media de la celda) / desviación de la celda.",
             "Marca anomalía cuando |z| > 2 y guarda la colección anomalies_daily.",
             "Limitación: la línea base es el propio periodo cargado, no una climatología de 30 años."],
     "decir": "Con pocos días el indicador es poco informativo; con el mes completo hay 31 valores por celda. Las anomalías son exploratorias.",
     "cmds": [[PY, "-u", "02_anomalias.py"]],
     "explain": [(r'"anomalias"', "Resultado: cantidad de celdas-día con |z| > 2, separadas en cálidas/frías y por dominio (tierra/océano).")]},
    {"id": "figuras", "titulo": "3 · Figuras y visualización",
     "inicio": "Consultando las colecciones de MongoDB para graficar.",
     "que": ["Lee regional_stats_etl, daily_climatology_etl y anomalies_daily.",
             "La precipitación extrema (> 5 mm) se obtiene con un $match + $group sobre las observaciones.",
             "Genera 4 figuras: serie por dominio, mapa de temperatura, mapa de anomalías y precipitación extrema."],
     "decir": "El mapa de temperatura muestra el contraste costa–Andes–Amazonía; el de anomalías, dónde se concentran los días atípicos.",
     "cmds": [[PY, "-u", "03_visualizaciones.py"]],
     "explain": [(r"guardados en", "Figuras generadas. Se muestran abajo.")]},
    {"id": "mapreduce", "titulo": "4 · MapReduce con Hadoop",
     "inicio": "Exportando las observaciones desde MongoDB a CSV para dárselas a Hadoop.",
     "que": ["Exporta las observaciones de MongoDB a un CSV.",
             "Hadoop Streaming ejecuta mapper.py (emite dominio|día → temperatura, precipitación, 1) y reducer.py (suma y promedia cada clave tras shuffle & sort).",
             "Se ejecuta en modo local de Hadoop 3.3.6: no se usa HDFS ni YARN."],
     "decir": "Map = emitir pares clave-valor; shuffle y sort = agrupar por clave; reduce = sumar. Las claves finales son dominio × día.",
     "cmds": [[PY, "-u", "05_exportar_para_hadoop.py"], ["bash", "hadoop/run_hadoop.sh", "local"]],
     "keep": r"(filas exportadas|^Hadoop:|number of splits|Running job|map \d+% reduce|completed successfully|Map input records|Map output records|Reduce input groups|Reduce output records|Resultado en|Falta|Error|Exception)",
     "explain": [(r"filas exportadas", "CSV listo. Lanzando el trabajo MapReduce de Hadoop."),
                 (r"number of splits", "Hadoop divide el CSV en splits; cada split lo procesa un mapper en paralelo."),
                 (r"map \d+% reduce 0%", "Fase MAP: cada mapper lee filas y emite pares (dominio|día → temp, precip, 1)."),
                 (r"map 100% reduce [1-9]", "Fase REDUCE: las claves ya agrupadas (shuffle y sort) se suman y se promedian."),
                 (r"completed successfully", "Trabajo terminado correctamente. La salida tiene una línea por dominio-día.")]},
    {"id": "validacion", "titulo": "5 · Validación independiente",
     "inicio": "Recalculando con NumPy, sin MongoDB, directamente desde los NetCDF.",
     "que": ["Recalcula temperatura media y precipitación total por dominio y día con NumPy.",
             "Compara contra MongoDB (Aggregation Pipeline) y contra Hadoop (MapReduce).",
             "Resultado esperado: VALIDACION_OK = true, con diferencias de ≈0."],
     "decir": "Tres métodos independientes (NumPy, Mongo, Hadoop) llegan al mismo resultado: eso respalda que el procesamiento es correcto.",
     "cmds": [[PY, "-u", "04_validacion.py"]],
     "explain": [(r"VALIDACION_OK", "Veredicto de la validación: debe ser true.")]},
]
BY_ID = {s["id"]: s for s in STEPS}

DRY_LINES = {
    "ingesta": ["Grilla 77x57 = 4389 celdas, 24 horas -> 105,336 documentos esperados", "  hora 24/24: 105,336 docs",
                "Ingesta: 105,336 docs en 2.47 s (42,613 docs/s)", "Índices creados en 2.08 s", "Agregaciones en 0.57 s"],
    "anomalias": ['{', '  "anomalias": 12,', '}'],
    "figuras": ["Figuras y top10_anomalias.csv guardados en /tmp"],
    "mapreduce": ["105,336 filas exportadas a x.csv", "Hadoop: Hadoop 3.3.6 | modo: local", "number of splits:1",
                  "map 0% reduce 0%", "map 100% reduce 100%", "Job job_local completed successfully", "Resultado en x (2 claves)"],
    "validacion": ['  "VALIDACION_OK": true'],
}


def res_dir(db):
    return HERE / ("resultados" if db == DEFAULT_DB else f"resultados_{db}")


def clean_db(v):
    return v if re.fullmatch(r"[A-Za-z0-9_]{1,40}", v or "") else DEMO_DB


def status(db):
    out = {"db": db, "mongo": False, "docs": None, "colecciones": {}, "hadoop": False, "datos": False, "dry": DRY}
    try:
        import common
        out["datos"] = common.F_INST.exists() and common.F_ACC.exists()
    except Exception:
        pass
    hh = pathlib.Path(os.environ.get("HADOOP_HOME", pathlib.Path.home() / "hadoop-3.3.6"))
    out["hadoop"] = (hh / "bin" / "hadoop").exists()
    if DRY:
        out.update(mongo=True, hadoop=True, datos=True)
        return out
    try:
        from pymongo import MongoClient
        c = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=1500)
        c.admin.command("ping")
        out["mongo"] = True
        d = c[db]
        for n in sorted(d.list_collection_names()):
            out["colecciones"][n] = d[n].estimated_document_count()
        out["docs"] = out["colecciones"].get("climate_observations")
    except Exception:
        pass
    return out


def read_json(p):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except Exception:
        return None


def results(step, db):
    r = res_dir(db)
    if step == "ingesta":
        return {"metricas": read_json(r / "metricas_ingesta.json")}
    if step == "anomalias":
        return {"resumen": read_json(r / "resumen_anomalias.json")}
    if step == "figuras":
        figs = sorted(p.name for p in r.glob("fig_*.png")) if r.exists() else []
        top = []
        try:
            import csv
            with open(r / "top10_anomalias.csv", newline="") as fh:
                top = list(csv.DictReader(fh))[:5]
        except Exception:
            pass
        return {"figuras": [f"/files/{r.name}/{f}?v={int((r / f).stat().st_mtime)}" for f in figs], "top": top}
    if step == "mapreduce":
        rows = []
        try:
            lines = (r / "hadoop_resultado.tsv").read_text().splitlines()
            for ln in lines[:10]:
                a = ln.split("\t")
                rows.append({"clave": a[0], "temp_media": a[1], "precip_total": a[2], "muestras": a[3]})
            return {"filas": rows, "total": len(lines)}
        except Exception:
            return {"filas": [], "total": 0}
    if step == "validacion":
        return {"validacion": read_json(r / "resultado_validacion.json")}
    return {}


_MC = None


def _mdb(db):
    global _MC
    from pymongo import MongoClient
    if _MC is None:
        _MC = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=2000)
    return _MC[db]


def _r2(v):
    return None if v is None else round(float(v), 2)


def _axes(d):
    lats = sorted(d.daily_climatology_etl.distinct("latitude"), reverse=True)
    lons = sorted(d.daily_climatology_etl.distinct("longitude"))
    return lats, lons


def viz(path, q, db):
    import datetime
    d = _mdb(db)
    anom = q.get("var") == "anom"
    col, fld = (d.anomalies_daily, "z") if anom else (d.daily_climatology_etl, "temp_mean")
    if path == "/api/viz/grid":
        lats, lons = _axes(d)
        days = sorted(col.distinct("day"))
        day = int(q.get("day") or (days[0] if days else 1))
        li = {round(v, 4): i for i, v in enumerate(lats)}
        oi = {round(v, 4): i for i, v in enumerate(lons)}
        m = [[None] * len(lons) for _ in lats]
        vals = []
        for x in col.find({"day": day}, {"_id": 0, "latitude": 1, "longitude": 1, fld: 1}):
            i, j = li.get(round(x["latitude"], 4)), oi.get(round(x["longitude"], 4))
            if i is not None and j is not None and x.get(fld) is not None:
                m[i][j] = _r2(x[fld]); vals.append(m[i][j])
        return {"day": day, "var": "anom" if anom else "temp", "min": min(vals, default=None),
                "max": max(vals, default=None), "lats": lats, "lons": lons, "days": days, "grid": m}
    if path == "/api/viz/hovmoller":
        rows = list(col.aggregate([{"$group": {"_id": {"lat": "$latitude", "day": "$day"}, "v": {"$avg": "$" + fld}}}]))
        lats = sorted({r["_id"]["lat"] for r in rows}, reverse=True)
        days = sorted({r["_id"]["day"] for r in rows})
        li, di = {v: i for i, v in enumerate(lats)}, {v: i for i, v in enumerate(days)}
        m = [[None] * len(days) for _ in lats]
        for r in rows:
            m[li[r["_id"]["lat"]]][di[r["_id"]["day"]]] = _r2(r["v"])
        vals = [v for row in m for v in row if v is not None]
        return {"var": "anom" if anom else "temp", "lats": lats, "days": days,
                "min": min(vals, default=None), "max": max(vals, default=None), "matrix": m}
    if path == "/api/viz/cell":
        lat, lon = float(q["lat"]), float(q["lon"])
        f = {"latitude": lat, "longitude": lon}
        t = {x["day"]: x.get("temp_mean") for x in d.daily_climatology_etl.find(f, {"_id": 0, "day": 1, "temp_mean": 1})}
        a = {x["day"]: x for x in d.anomalies_daily.find(f, {"_id": 0, "day": 1, "z": 1, "is_anomaly": 1})}
        serie = [{"day": k, "temp_mean": _r2(t.get(k)), "z": _r2(a.get(k, {}).get("z")),
                  "is_anomaly": a.get(k, {}).get("is_anomaly")} for k in sorted(set(t) | set(a))]
        return {"lat": lat, "lon": lon, "serie": serie}
    if path == "/api/viz/geo":
        lat, lon, km = float(q["lat"]), float(q["lon"]), float(q.get("km") or 50)
        t0 = d.climate_observations.find_one({}, {"timestamp": 1}, sort=[("timestamp", 1)])["timestamp"]
        t0 = t0.replace(hour=0, minute=0, second=0, microsecond=0)
        f = {"location": {"$geoWithin": {"$centerSphere": [[lon, lat], km / 6378.1]}},
             "timestamp": {"$gte": t0, "$lt": t0 + datetime.timedelta(days=1)}}
        n = d.climate_observations.count_documents(f)
        ex = d.climate_observations.find(f).explain()
        es = ex.get("executionStats", {})
        stages, p = [], ex.get("queryPlanner", {}).get("winningPlan", {})
        while p:
            p = p.get("queryPlan", p)
            stages.append(p.get("stage"))
            p = p.get("inputStage") or (p.get("inputStages") or [None])[0]
        stage = "IXSCAN" if "IXSCAN" in stages else ("COLLSCAN" if "COLLSCAN" in stages else (stages[-1] if stages else None))
        return {"lat": lat, "lon": lon, "km": km, "dia": str(t0.date()), "n": n,
                "executionTimeMillis": es.get("executionTimeMillis"), "totalDocsExamined": es.get("totalDocsExamined"),
                "totalKeysExamined": es.get("totalKeysExamined"), "stage": stage, "plan": stages}
    if path == "/api/viz/resumen":
        a = d.anomalies_daily
        dom = {x["_id"]: x["n"] for x in a.aggregate([{"$match": {"is_anomaly": True}}, {"$group": {"_id": "$domain", "n": {"$sum": 1}}}])}
        top = list(a.aggregate([{"$match": {"is_anomaly": True}}, {"$group": {"_id": "$day", "n": {"$sum": 1}}},
                                {"$sort": {"n": -1}}, {"$limit": 1}]))
        return {"anomalias": a.count_documents({"is_anomaly": True}),
                "calidas": a.count_documents({"is_anomaly": True, "z": {"$gt": 0}}),
                "frias": a.count_documents({"is_anomaly": True, "z": {"$lt": 0}}),
                "por_dominio": dom, "dia_max": {"day": top[0]["_id"], "n": top[0]["n"]} if top else None}
    return None


def make_env(hours, db):
    env = os.environ.copy()
    env.update(ERA5_HORAS=str(hours), ERA5_DB=db, RES_DIR=str(res_dir(db)), PYTHONUNBUFFERED="1")
    return env


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/":
            return self._send(200, HTML, "text/html; charset=utf-8")
        if u.path == "/api/steps":
            return self._send(200, json.dumps([{k: s[k] for k in ("id", "titulo", "que", "decir")} for s in STEPS]))
        if u.path == "/api/status":
            return self._send(200, json.dumps(status(clean_db(q.get("db")))))
        if u.path == "/api/results":
            return self._send(200, json.dumps(results(q.get("step", ""), clean_db(q.get("db")))))
        m = re.fullmatch(r"/files/(resultados(?:_[A-Za-z0-9_]+)?)/([A-Za-z0-9_.-]+\.(?:png|csv|json))", u.path)
        if m:
            p = HERE / m.group(1) / m.group(2)
            if p.exists():
                ct = {"png": "image/png", "csv": "text/csv", "json": "application/json"}[p.suffix[1:]]
                return self._send(200, p.read_bytes(), ct)
            return self._send(404, "no existe", "text/plain")
        if u.path.startswith("/api/viz/"):
            try:
                r = viz(u.path, q, clean_db(q.get("db")))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
            return self._send(200, json.dumps(r)) if r is not None else self._send(404, "no encontrado", "text/plain")
        if u.path == "/api/run":
            return self.run_step(q)
        self._send(404, "no encontrado", "text/plain")

    def run_step(self, q):
        step = BY_ID.get(q.get("step", ""))
        db = clean_db(q.get("db"))
        hours = q.get("hours", "168")
        hours = hours if hours in ("24", "168", "744") else "168"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        def emit(**kw):
            self.wfile.write(("data: " + json.dumps(kw, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()

        try:
            if not step:
                emit(t="line", v="Paso desconocido")
                return emit(t="done", code=2, seg=0)
            if not LOCK.acquire(blocking=False):
                emit(t="line", v="Ya hay un paso en ejecución. Espera a que termine.")
                return emit(t="done", code=3, seg=0)
            try:
                t0 = time.time()
                emit(t="ahora", v=step["inicio"])
                keep = re.compile(step["keep"]) if step.get("keep") else None
                rx = [(re.compile(a), b) for a, b in step["explain"]]
                code = 0
                for cmd in step["cmds"]:
                    if DRY:
                        cmd = [PY, "-u", "-c", "import sys,time\nfor l in %r:\n print(l);time.sleep(.5)" % DRY_LINES[step["id"]]]
                    emit(t="cmd", v="$ " + " ".join(os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd))[:160])
                    p = subprocess.Popen(cmd, cwd=HERE, env=make_env(hours, db), stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT, text=True, bufsize=1, errors="replace")
                    for line in p.stdout:
                        line = line.rstrip("\n")
                        if keep and not keep.search(line):
                            continue
                        emit(t="line", v=line)
                        for r, txt in rx:
                            if r.search(line):
                                emit(t="ahora", v=txt)
                    code = p.wait()
                    if code != 0:
                        break
                emit(t="done", code=code, seg=round(time.time() - t0, 1))
            finally:
                LOCK.release()
        except (BrokenPipeError, ConnectionResetError):
            pass


HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ERA5 Big Data · Ejecución en vivo</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--ink:#1b2430;--mut:#667085;--ac:#1f6feb;--ok:#1a7f37;--bad:#cf222e;--run:#9a6700;--line:#e2e6ec}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
header{background:#14213d;color:#fff;padding:16px 24px}header h1{margin:0;font-size:20px}header p{margin:2px 0 0;color:#b8c4dc;font-size:13px}
main{max-width:1100px;margin:0 auto;padding:18px}
.bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
.chip{padding:3px 10px;border-radius:99px;font-size:12px;font-weight:600;background:#eef1f5;color:var(--mut)}.chip.ok{background:#dafbe1;color:var(--ok)}.chip.bad{background:#ffebe9;color:var(--bad)}
select,button{font:inherit;padding:8px 12px;border-radius:8px;border:1px solid #c9d1dc;background:#fff}
button.go{background:var(--ac);color:#fff;border-color:var(--ac);font-weight:600;cursor:pointer}button.go:disabled{opacity:.5;cursor:not-allowed}
button.all{background:var(--ok);border-color:var(--ok)}
.cols{display:grid;grid-template-columns:1fr 250px;gap:14px;align-items:start}@media(max-width:900px){.cols{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:14px}
.card h2{margin:0;font-size:17px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.card h2 .sp{flex:1}
.badge{font-size:12px;padding:2px 9px;border-radius:99px;background:#eef1f5;color:var(--mut)}.badge.run{background:#fff8c5;color:var(--run)}.badge.ok{background:#dafbe1;color:var(--ok)}.badge.err{background:#ffebe9;color:var(--bad)}
details{margin:8px 0}summary{cursor:pointer;color:var(--ac);font-size:13px}ul{margin:6px 0 6px 18px;padding:0}li{margin:2px 0}.say{background:#eef4ff;border-left:3px solid var(--ac);padding:6px 10px;border-radius:6px;font-size:13px;margin-top:6px}
.ahora{display:none;margin:8px 0;padding:9px 12px;background:#fff8c5;border-radius:8px;border:1px solid #eac54f;font-size:14px}
.term{display:none;background:#0d1117;color:#c9d1d9;font:12px/1.45 ui-monospace,Menlo,Consolas,monospace;padding:10px;border-radius:8px;max-height:210px;overflow:auto;white-space:pre-wrap;margin:8px 0}
.term .cmd{color:#7ee787}.res{margin-top:10px}.mets{display:flex;gap:10px;flex-wrap:wrap}.met{background:#f6f8fa;border:1px solid var(--line);border-radius:10px;padding:8px 12px;min-width:120px}.met b{display:block;font-size:20px}.met span{font-size:12px;color:var(--mut)}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px;margin-top:8px}.figs img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left}th{background:#f6f8fa}
.verdict{font-size:22px;font-weight:700;padding:10px 14px;border-radius:10px;display:inline-block}.verdict.ok{background:#dafbe1;color:var(--ok)}.verdict.bad{background:#ffebe9;color:var(--bad)}
.side h3{margin:0 0 8px;font-size:14px}.side table td{padding:3px 4px}.note{font-size:12px;color:var(--mut)}
[hidden]{display:none!important}
.tabs{display:flex;gap:6px;margin-bottom:12px}.tab{font-weight:600;cursor:pointer}.tab.on{background:#14213d;color:#fff;border-color:#14213d}
.rgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:900px){.rgrid{grid-template-columns:1fr}}
.map{display:block;width:100%;max-width:399px;image-rendering:pixelated;cursor:crosshair;border:1px solid var(--line);margin-top:8px}
.wide{display:block;max-width:100%;margin-top:8px}#cv_h{cursor:crosshair}
.lg{max-width:300px;margin-top:6px}.lg canvas{display:block;width:100%;height:14px;border:1px solid var(--line)}.lgl{display:flex;justify-content:space-between;font-size:11px;color:var(--mut)}
#tip{position:fixed;pointer-events:none;background:#14213d;color:#fff;font-size:12px;padding:5px 8px;border-radius:6px;display:none;z-index:9;line-height:1.35}
input[type=range]{vertical-align:middle}
</style></head><body>
<header><h1>ERA5 Big Data · Ejecución en vivo</h1><p>Pipeline NetCDF → MongoDB → anomalías → MapReduce (Hadoop) → validación · UCSM · Big Data 2026</p></header>
<main>
<nav class="tabs"><button id="tb_pasos" class="tab on">Pasos del pipeline</button><button id="tb_res" class="tab">Resultados</button></nav>
<div id="v_pasos">
<div class="bar">
 <span id="c_mongo" class="chip">MongoDB…</span><span id="c_hadoop" class="chip">Hadoop…</span><span id="c_datos" class="chip">Datos ERA5…</span>
 <span style="flex:1"></span>
 <label>Datos a procesar
  <select id="hours"><option value="24">24 horas (≈10 s, 1 día)</option><option value="168" selected>168 horas · 7 días (≈30 s)</option><option value="744">744 horas · mes completo (≈2–3 min)</option></select></label>
 <label>Base de datos
  <select id="db"><option value="era5_demo" selected>era5_demo (demo, no toca la principal)</option><option value="era5_climate_db">era5_climate_db (principal del informe)</option></select></label>
 <button id="all" class="go all">▶ Ejecutar todo el pipeline</button>
</div>
<div class="cols"><div id="steps"></div>
 <aside class="side card"><h3>Estado de la base de datos</h3><div id="dbstate" class="note">…</div>
 <p class="note" style="margin-top:12px">Con pocos días las anomalías son poco informativas: usa 744 h para ver el resultado completo.</p></aside></div>
<div id="final"></div>
</div>
<div id="v_res" hidden>
<div class="bar"><button id="play" class="go">▶ Animar</button>
 <label>Día <input type="range" id="day" min="0" max="0" value="0" style="width:260px"></label><b id="dlab">—</b>
 <span style="flex:1"></span><span id="pf" class="note"></span><span class="note">base: <b id="rdb"></b></span><button id="reload">↻ Recargar</button></div>
<div id="rmsg" class="note" style="margin-bottom:10px"></div>
<div class="rgrid">
 <div class="card"><h2>Temperatura media diaria (°C)</h2><canvas id="cv_t" class="map"></canvas><div class="lg" id="lg_t"><canvas></canvas><div class="lgl"><span class="lo"></span><span class="mid"></span><span class="hi"></span></div></div>
  <p class="note">Gris = sin dato. Pasa el mouse para ver valores; haz click en una celda.</p></div>
 <div class="card"><h2>Anomalías (z)</h2><canvas id="cv_a" class="map"></canvas><div class="lg" id="lg_a"><canvas></canvas><div class="lgl"><span class="lo"></span><span class="mid"></span><span class="hi"></span></div></div>
  <p class="note"><b id="acount"></b> Azul = más frío, rojo = más cálido (escala fija z ∈ [−4, 4]); borde negro = |z| &gt; 2.</p></div>
</div>
<div class="rgrid">
 <div class="card"><h2>Serie de la celda seleccionada</h2><div id="cinfo" class="note">Haz click en una celda de cualquiera de los mapas.</div>
  <canvas id="cv_line" class="wide" width="640" height="0"></canvas><p class="note">Línea = temperatura media diaria; puntos rojos = días anómalos (|z| &gt; 2).</p></div>
 <div class="card"><h2>Consulta geoespacial en vivo<span class="sp"></span><label class="note">Radio <select id="km"><option value="10">10 km</option><option value="50" selected>50 km</option><option value="100">100 km</option></select></label></h2>
  <div id="geo" class="note">Haz click en el mapa: se ejecuta <code>$geoWithin/$centerSphere</code> sobre climate_observations (primer día) con <code>explain()</code>.</div></div>
</div>
<div class="card"><h2>Hovmöller (latitud × día)<span class="sp"></span><select id="hvar"><option value="temp">Temperatura</option><option value="anom">Anomalía z</option></select></h2>
 <canvas id="cv_h" class="wide"></canvas><div class="lg" id="lg_h"><canvas></canvas><div class="lgl"><span class="lo"></span><span class="mid"></span><span class="hi"></span></div></div><p class="note" id="hmsg">Cada celda = promedio sobre las longitudes de esa latitud y día.</p></div>
<div class="card"><h2>Resumen de anomalías</h2><div id="resu" class="note">…</div></div>
</div>
</main><div id="tip"></div>
<script>
const $=s=>document.querySelector(s);let STEPS=[],busy=false;
const hours=()=>$('#hours').value, db=()=>$('#db').value;
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt=n=>typeof n==='number'?n.toLocaleString('es-PE'):n;
function chip(id,ok,txt){const e=$(id);e.textContent=txt;e.className='chip '+(ok?'ok':'bad')}
async function refresh(){try{const s=await (await fetch('/api/status?db='+db())).json();
 chip('#c_mongo',s.mongo,s.mongo?'MongoDB conectado':'MongoDB NO responde');chip('#c_hadoop',s.hadoop,s.hadoop?'Hadoop encontrado':'Hadoop NO encontrado');chip('#c_datos',s.datos,s.datos?'Datos ERA5 listos':'Faltan los .nc');
 const c=s.colecciones||{};const k=Object.keys(c);
 $('#dbstate').innerHTML=k.length?'<b>'+esc(s.db)+'</b><table>'+k.map(n=>`<tr><td>${esc(n)}</td><td style="text-align:right">${fmt(c[n])}</td></tr>`).join('')+'</table>':'<b>'+esc(s.db)+'</b><br>sin colecciones todavía';
}catch(e){chip('#c_mongo',false,'Servidor no responde')}}
function build(){$('#steps').innerHTML=STEPS.map(s=>`<div class="card" id="s_${s.id}"><h2>${esc(s.titulo)}<span class="sp"></span><span class="badge" id="b_${s.id}">pendiente</span><button class="go" id="r_${s.id}">▶ Ejecutar</button></h2>
 <details><summary>¿Qué hace este paso?</summary><ul>${s.que.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><div class="say"><b>Qué explicar:</b> ${esc(s.decir)}</div></details>
 <div class="ahora" id="a_${s.id}"></div><div class="term" id="t_${s.id}"></div><div class="res" id="x_${s.id}"></div></div>`).join('');
 STEPS.forEach(s=>$('#r_'+s.id).onclick=()=>runStep(s.id))}
function setBadge(id,cls,txt){const b=$('#b_'+id);b.className='badge '+cls;b.textContent=txt}
function setBusy(v){busy=v;document.querySelectorAll('button.go').forEach(b=>b.disabled=v)}
function runStep(id){return new Promise(res=>{if(busy){res(false);return}
 if(id==='ingesta'&&db()==='era5_climate_db'&&!confirm('Esto BORRARÁ y recargará la base PRINCIPAL del informe (era5_climate_db). ¿Seguro?')){res(false);return}
 setBusy(true);const t=$('#t_'+id),a=$('#a_'+id);t.style.display='block';t.innerHTML='';a.style.display='block';a.textContent='Iniciando…';$('#x_'+id).innerHTML='';
 setBadge(id,'run','ejecutando…');$('#s_'+id).scrollIntoView({behavior:'smooth',block:'start'});
 let n=0,finished=false;const es=new EventSource(`/api/run?step=${id}&hours=${hours()}&db=${db()}`);
 es.onmessage=async e=>{const m=JSON.parse(e.data);
  if(m.t==='line'||m.t==='cmd'){const d=document.createElement('div');if(m.t==='cmd')d.className='cmd';d.textContent=m.v;t.appendChild(d);if(++n>500)t.removeChild(t.firstChild);t.scrollTop=t.scrollHeight}
  else if(m.t==='ahora'){a.innerHTML='<b>Qué está pasando ahora:</b> '+esc(m.v)}
  else if(m.t==='done'){finished=true;es.close();const ok=m.code===0;setBadge(id,ok?'ok':'err',(ok?'✔ listo en ':'✖ error · ')+m.seg+' s');
   a.style.display=ok?'none':'block';if(!ok)a.innerHTML='<b>El paso terminó con error</b> (código '+m.code+'). Revisa el log.';
   if(ok)await showResult(id);setBusy(false);refresh();res(ok)}};
 es.onerror=()=>{if(!finished){es.close();setBadge(id,'err','conexión perdida');setBusy(false);res(false)}}})}
async function showResult(id){const r=await (await fetch(`/api/results?step=${id}&db=${db()}`)).json();let h='';const el=$('#x_'+id);
 const met=(v,l)=>`<div class="met"><b>${fmt(v)}</b><span>${l}</span></div>`;
 if(id==='ingesta'&&r.metricas){const m=r.metricas;h='<div class="mets">'+met(m.documentos_observaciones,'documentos de observación')+met(m.docs_por_segundo,'docs / segundo')+met(m.segundos_ingesta+' s','ingesta')+met(m.segundos_indices+' s','índices')+met(m.segundos_agregacion+' s','agregaciones')+met(m.tamano_coleccion_MB+' MB','colección')+met(m.documentos_climatologia_diaria,'climatología diaria')+'</div>'}
 if(id==='anomalias'&&r.resumen){const m=r.resumen;h='<div class="mets">'+met(m.anomalias,'anomalías |z|>2')+met(m.pct_anomalias+' %','de las celdas-día')+met(m.calidas,'cálidas')+met(m.frias,'frías')+met(m.por_dominio.Continental_Peru??0,'en tierra')+met(m.por_dominio.Pacific_Ocean??0,'en océano')+'</div>'}
 if(id==='figuras'){h='<div class="figs">'+(r.figuras||[]).map(u=>`<a href="${u}" target="_blank"><img src="${u}"></a>`).join('')+'</div>';
  if((r.top||[]).length)h+='<table><tr><th>día</th><th>lat</th><th>lon</th><th>T (°C)</th><th>z</th><th>tipo</th></tr>'+r.top.map(x=>`<tr><td>${x.day}</td><td>${x.latitude}</td><td>${x.longitude}</td><td>${x.temp_mean}</td><td>${x.z}</td><td>${x.tipo}</td></tr>`).join('')+'</table>'}
 if(id==='mapreduce'){h='<div class="mets">'+met(r.total,'claves en la salida (dominio|día)')+'</div>';
  if((r.filas||[]).length)h+='<table><tr><th>clave</th><th>temp. media (°C)</th><th>precip. total (mm)</th><th>muestras</th></tr>'+r.filas.map(x=>`<tr><td>${esc(x.clave)}</td><td>${x.temp_media}</td><td>${x.precip_total}</td><td>${fmt(+x.muestras)}</td></tr>`).join('')+'</table>'}
 if(id==='validacion'&&r.validacion){const v=r.validacion,ok=v.VALIDACION_OK;h=`<div class="verdict ${ok?'ok':'bad'}">${ok?'✔ VALIDACIÓN OK':'✖ VALIDACIÓN FALLÓ'}</div><div class="mets" style="margin-top:8px">`+met(v.observaciones_en_mongodb,'docs en MongoDB')+met(v.observaciones_esperadas,'docs esperados')+met(v.max_dif_temp_C+' °C','dif. máx. temperatura (Mongo vs NumPy)')+met(v.max_dif_precip_mm+' mm','dif. máx. precipitación')+(v.hadoop_filas!==undefined?met(v.hadoop_max_dif_temp_C+' °C','dif. máx. temperatura (Hadoop vs NumPy)')+met(v.hadoop_filas,'claves comparadas con Hadoop'):'')+'</div>'}
 el.innerHTML=h}
$('#all').onclick=async()=>{if(busy)return;$('#final').innerHTML='';let ok=true;for(const s of STEPS){ok=await runStep(s.id);if(!ok)break}
 $('#final').innerHTML=ok?'<div class="card"><div class="verdict ok">✔ Pipeline completo ejecutado</div> <span class="note">Datos: '+hours()+' h · base: '+esc(db())+'</span></div>':'<div class="card"><div class="verdict bad">✖ El pipeline se detuvo por un error</div></div>'};
$('#hours').onchange=()=>{};$('#db').onchange=refresh;
// ===== Pestañas =====
function tab(t){for(const x of ['pasos','res']){$('#v_'+x).hidden=x!==t;$('#tb_'+x).classList.toggle('on',x===t)}if(t==='res')loadRes()}
$('#tb_pasos').onclick=()=>tab('pasos');$('#tb_res').onclick=()=>tab('res');
// ===== Resultados (datos reales de /api/viz/*) =====
const J=async u=>{const r=await fetch(u);let j;try{j=await r.json()}catch(e){j={error:'HTTP '+r.status}}if(!r.ok||j.error)throw new Error(j.error||('HTTP '+r.status));return j};
const V={db:null,days:[],di:0,cache:{},T:null,A:null,sel:null,hv:null,scale:null,run:0};
const CS=7,NULLC='#b5b5b5',metH=(v,l)=>`<div class="met"><b>${esc(fmt(v))}</b><span>${l}</span></div>`;
const cl=v=>Math.max(0,Math.min(255,Math.round(v*255)));
function turbo(t){t=Math.max(0,Math.min(1,t));return [cl(0.13572138+t*(4.6153926+t*(-42.66032258+t*(132.13108234+t*(-152.94239396+t*59.28637943))))),
 cl(0.09140261+t*(2.19418839+t*(4.84296658+t*(-14.18503333+t*(4.27729857+t*2.82956604))))),
 cl(0.1066733+t*(12.64194608+t*(-60.58204836+t*(110.36276771+t*(-89.90310912+t*27.34824973)))))]}
function divz(z){let t=Math.max(-1,Math.min(1,z/4));const w=[247,247,247],c=t<0?[33,102,172]:[178,24,43];t=Math.abs(t);return w.map((v,k)=>Math.round(v+(c[k]-v)*t))}
const rgb=c=>`rgb(${c[0]},${c[1]},${c[2]})`;
function legend(el,f,lo,hi,unit){const c=el.querySelector('canvas');c.width=300;c.height=1;const x=c.getContext('2d');
 for(let i=0;i<300;i++){x.fillStyle=rgb(f(lo+(hi-lo)*i/299));x.fillRect(i,0,1,1)}
 const L=v=>v.toFixed(1)+' '+unit;el.querySelector('.lo').textContent=L(lo);el.querySelector('.mid').textContent=L((lo+hi)/2);el.querySelector('.hi').textContent=L(hi)}
const tipEl=()=>$('#tip');
function tip(e,h){const t=tipEl();t.innerHTML=h;t.style.display='block';t.style.left=(e.clientX+14)+'px';t.style.top=(e.clientY+14)+'px'}
function hideTip(){tipEl().style.display='none'}
function drawMap(cv,g,f,box){const R=g.grid.length,C=R?g.grid[0].length:0;cv.width=C*CS;cv.height=R*CS;const x=cv.getContext('2d');
 for(let i=0;i<R;i++)for(let j=0;j<C;j++){const v=g.grid[i][j];x.fillStyle=v==null?NULLC:rgb(f(v));x.fillRect(j*CS,i*CS,CS,CS)}
 if(box){x.strokeStyle='#000';x.lineWidth=1.2;for(let i=0;i<R;i++)for(let j=0;j<C;j++){const v=g.grid[i][j];if(v!=null&&Math.abs(v)>2)x.strokeRect(j*CS+.6,i*CS+.6,CS-1.2,CS-1.2)}}
 if(V.sel){const[i,j]=V.sel;x.lineWidth=2;x.strokeStyle='#fff';x.strokeRect(j*CS-2,i*CS-2,CS+4,CS+4);x.strokeStyle='#e0007a';x.strokeRect(j*CS-4,i*CS-4,CS+8,CS+8)}}
function cellAt(cv,e,R,C){const b=cv.getBoundingClientRect(),j=Math.floor((e.clientX-b.left)/b.width*C),i=Math.floor((e.clientY-b.top)/b.height*R);return i>=0&&i<R&&j>=0&&j<C?[i,j]:null}
async function grid(v,day){const k=v+':'+day;if(V.cache[k])return V.cache[k];
 const g=await J(`/api/viz/grid?var=${v}&db=${encodeURIComponent(V.db)}`+(day!=null?'&day='+day:''));V.cache[v+':'+g.day]=g;return g}
const ftemp=()=>{const[lo,hi]=V.scale||[V.T.min,V.T.max];return [v=>turbo((v-lo)/((hi-lo)||1)),lo,hi]};
function drawMaps(){if(!V.T)return;const[f,lo,hi]=ftemp();drawMap($('#cv_t'),V.T,f,false);if(lo!=null)legend($('#lg_t'),f,lo,hi,'°C');
 drawMap($('#cv_a'),V.A,divz,true);const n=V.A.grid.flat().filter(v=>v!=null&&Math.abs(v)>2).length;$('#acount').textContent=fmt(n)+' celdas con |z| > 2 este día.'}
async function showDay(){const day=V.days[V.di];$('#day').value=V.di;$('#dlab').textContent='Día '+day+' ('+(V.di+1)+'/'+V.days.length+')';
 const[T,A]=await Promise.all([grid('temp',day),grid('anom',day)]);if(V.days[V.di]!==day)return;V.T=T;V.A=A;drawMaps()}
async function prefetch(){const db0=V.db;let lo=Infinity,hi=-Infinity,k=0;
 for(const d of V.days){if(V.db!==db0)return;const g=await grid('temp',d);if(g.min!=null){lo=Math.min(lo,g.min);hi=Math.max(hi,g.max)}k++;$('#pf').textContent=`escala °C del día (cargando mes ${k}/${V.days.length})`}
 if(V.db!==db0||lo>hi)return;V.scale=[lo,hi];$('#pf').textContent=`escala °C fija del periodo: ${lo.toFixed(1)} a ${hi.toFixed(1)}`;drawMaps()}
function stop(){V.run++;$('#play').textContent='▶ Animar'}
$('#play').onclick=async()=>{if($('#play').textContent.startsWith('⏸')){stop();return}const id=++V.run;$('#play').textContent='⏸ Pausar';
 while(V.run===id&&V.days.length){V.di=(V.di+1)%V.days.length;try{await showDay()}catch(e){$('#rmsg').textContent='Error: '+e.message;stop();break}await new Promise(r=>setTimeout(r,600))}};
$('#day').oninput=()=>{V.di=+$('#day').value;showDay().catch(e=>$('#rmsg').textContent='Error: '+e.message)};
function hookMap(cv,which){
 cv.onmousemove=e=>{const g=which==='t'?V.T:V.A;if(!g||!g.grid.length)return;const c=cellAt(cv,e,g.grid.length,g.grid[0].length);if(!c)return hideTip();
  const v=g.grid[c[0]][c[1]];tip(e,`lat ${g.lats[c[0]].toFixed(2)}°, lon ${g.lons[c[1]].toFixed(2)}°<br>`+(v==null?'sin dato':which==='t'?v.toFixed(2)+' °C':'z = '+v.toFixed(2)))};
 cv.onmouseleave=hideTip;
 cv.onclick=e=>{const g=V.T;if(!g||!g.grid.length)return;const c=cellAt(cv,e,g.grid.length,g.grid[0].length);if(!c)return;V.sel=c;drawMaps();cellSeries();geo()}}
hookMap($('#cv_t'),'t');hookMap($('#cv_a'),'a');
function drawLine(s){const cv=$('#cv_line'),W=cv.width=640,H=cv.height=240,x=cv.getContext('2d'),p={l:46,r:12,t:12,b:30};
 const pts=s.serie.filter(d=>d.temp_mean!=null);x.clearRect(0,0,W,H);if(!pts.length){x.fillStyle='#667085';x.fillText('Sin datos para esta celda',W/2-60,H/2);return}
 const d0=pts[0].day,d1=pts[pts.length-1].day,vs=pts.map(d=>d.temp_mean);let lo=Math.min(...vs),hi=Math.max(...vs);if(hi-lo<.5){lo-=.5;hi+=.5}
 const X=d=>p.l+(d-d0)/Math.max(1,d1-d0)*(W-p.l-p.r),Y=v=>H-p.b-(v-lo)/(hi-lo)*(H-p.t-p.b);
 x.font='11px system-ui,sans-serif';x.lineWidth=1;x.strokeStyle='#e2e6ec';x.fillStyle='#667085';x.textAlign='right';
 for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,y=Y(v);x.beginPath();x.moveTo(p.l,y);x.lineTo(W-p.r,y);x.stroke();x.fillText(v.toFixed(1)+'°',p.l-5,y+4)}
 x.textAlign='center';pts.forEach(d=>{if(d.day===d0||d.day===d1||d.day%5===0)x.fillText(d.day,X(d.day),H-p.b+15)});x.fillText('día',W-p.r-8,H-4);
 const cur=V.days[V.di];if(cur>=d0&&cur<=d1){x.setLineDash([4,3]);x.strokeStyle='#999';x.beginPath();x.moveTo(X(cur),p.t);x.lineTo(X(cur),H-p.b);x.stroke();x.setLineDash([])}
 x.strokeStyle='#1f6feb';x.lineWidth=2;x.beginPath();pts.forEach((d,k)=>k?x.lineTo(X(d.day),Y(d.temp_mean)):x.moveTo(X(d.day),Y(d.temp_mean)));x.stroke();
 pts.forEach(d=>{x.fillStyle=d.is_anomaly?'#cf222e':'#1f6feb';x.beginPath();x.arc(X(d.day),Y(d.temp_mean),d.is_anomaly?5:2.5,0,7);x.fill()})}
async function cellSeries(){const[i,j]=V.sel,lat=V.T.lats[i],lon=V.T.lons[j];$('#cinfo').textContent='Cargando serie…';
 try{const s=await J(`/api/viz/cell?lat=${lat}&lon=${lon}&db=${encodeURIComponent(V.db)}`);drawLine(s);const an=s.serie.filter(d=>d.is_anomaly);
  $('#cinfo').innerHTML=`Celda lat ${lat.toFixed(2)}°, lon ${lon.toFixed(2)}° · ${s.serie.length} días · <b style="color:var(--bad)">${an.length} días anómalos</b>`+(an.length?': '+an.map(d=>'día '+d.day+' (z = '+d.z+')').join(', '):'')}
 catch(e){$('#cinfo').textContent='Error: '+e.message}}
async function geo(){if(!V.sel||!V.T)return;const[i,j]=V.sel,lat=V.T.lats[i],lon=V.T.lons[j],km=$('#km').value;$('#geo').textContent='Consultando MongoDB…';
 try{const r=await J(`/api/viz/geo?lat=${lat}&lon=${lon}&km=${km}&db=${encodeURIComponent(V.db)}`);
  $('#geo').innerHTML='<div class="mets">'+metH(r.stage??'—','plan')+metH(r.n,'docs devueltos')+metH(r.totalDocsExamined??'—','docs examinados')+metH((r.executionTimeMillis??'—')+' ms','tiempo de ejecución')+'</div>'+
   `<p class="note">Círculo de ${r.km} km alrededor de (${r.lat.toFixed(2)}, ${r.lon.toFixed(2)}) · día ${esc(r.dia)} · etapas: ${esc((r.plan||[]).join(' → '))} · claves de índice examinadas: ${fmt(r.totalKeysExamined)}</p>`}
 catch(e){$('#geo').textContent='Error: '+e.message}}
$('#km').onchange=geo;
const HM={l:46,t:6,cw:18,ch:5,b:24};
function drawHov(){const h=V.hv,cv=$('#cv_h'),R=h.lats.length,C=h.days.length;cv.width=HM.l+C*HM.cw+6;cv.height=HM.t+R*HM.ch+HM.b;const x=cv.getContext('2d');
 const an=h.var==='anom',lo=an?-4:h.min,hi=an?4:h.max,f=an?divz:v=>turbo((v-lo)/((hi-lo)||1));
 for(let i=0;i<R;i++)for(let j=0;j<C;j++){const v=h.matrix[i][j];x.fillStyle=v==null?NULLC:rgb(f(v));x.fillRect(HM.l+j*HM.cw,HM.t+i*HM.ch,HM.cw,HM.ch)}
 x.font='11px system-ui,sans-serif';x.fillStyle='#667085';x.textAlign='right';
 h.lats.forEach((la,i)=>{const r=Math.round(la);if(Math.abs(la-r)<1e-6&&r%2===0)x.fillText(r+'°',HM.l-5,HM.t+i*HM.ch+HM.ch/2+4)});
 x.textAlign='center';h.days.forEach((d,j)=>{if(j===0||d%5===0)x.fillText(d,HM.l+j*HM.cw+HM.cw/2,cv.height-8)});
 if(lo!=null)legend($('#lg_h'),f,lo,hi,an?'z':'°C')}
$('#cv_h').onmousemove=e=>{const h=V.hv;if(!h)return;const cv=$('#cv_h'),b=cv.getBoundingClientRect(),px=(e.clientX-b.left)*cv.width/b.width,py=(e.clientY-b.top)*cv.height/b.height;
 const j=Math.floor((px-HM.l)/HM.cw),i=Math.floor((py-HM.t)/HM.ch);if(i<0||j<0||i>=h.lats.length||j>=h.days.length)return hideTip();const v=h.matrix[i][j];
 tip(e,`lat ${h.lats[i].toFixed(2)}°, día ${h.days[j]}<br>`+(v==null?'sin dato':h.var==='anom'?'z medio = '+v.toFixed(2):v.toFixed(2)+' °C')+'<br><span style="opacity:.7">promedio sobre longitudes</span>')};
$('#cv_h').onmouseleave=hideTip;
async function hov(){$('#hmsg').textContent='Cargando…';try{V.hv=await J(`/api/viz/hovmoller?var=${$('#hvar').value}&db=${encodeURIComponent(V.db)}`);drawHov();
 $('#hmsg').textContent='Cada celda = promedio sobre las longitudes de esa latitud y día.'}catch(e){$('#hmsg').textContent='Error: '+e.message}}
$('#hvar').onchange=hov;
async function resumen(){try{const r=await J('/api/viz/resumen?db='+encodeURIComponent(V.db));
 $('#resu').innerHTML='<div class="mets">'+metH(r.anomalias,'anomalías |z| > 2')+metH(r.calidas,'cálidas (z > 2)')+metH(r.frias,'frías (z < −2)')+
  Object.entries(r.por_dominio||{}).map(([k,v])=>metH(v,esc(k))).join('')+metH(r.dia_max?'día '+r.dia_max.day:'—',r.dia_max?'más anomalías ('+fmt(r.dia_max.n)+')':'día con más anomalías')+'</div>'}
 catch(e){$('#resu').textContent='Error: '+e.message}}
async function loadRes(force){const d=db();if(!force&&V.db===d&&V.T)return;stop();V.db=d;V.cache={};V.sel=null;V.scale=null;V.T=V.A=V.hv=null;
 $('#rdb').textContent=d;$('#rmsg').textContent='Cargando datos de '+d+'…';$('#pf').textContent='';$('#cinfo').textContent='Haz click en una celda de cualquiera de los mapas.';$('#cv_line').height=0;
 try{const g=await grid('temp',null);V.days=g.days;if(!V.days.length)throw new Error('daily_climatology_etl está vacía');$('#day').max=V.days.length-1;V.di=Math.max(0,V.days.indexOf(g.day));
  await showDay();$('#rmsg').textContent='';resumen();hov();prefetch()}
 catch(e){$('#rmsg').innerHTML='<b style="color:var(--bad)">No se pudieron cargar los resultados de '+esc(d)+':</b> '+esc(e.message)+'. Ejecuta antes los pasos de ingesta y anomalías.'}}
$('#reload').onclick=()=>loadRes(true);
$('#db').addEventListener('change',()=>{if(!$('#v_res').hidden)loadRes()});
legend($('#lg_a'),divz,-4,4,'z');
fetch('/api/steps').then(r=>r.json()).then(s=>{STEPS=s;build();refresh()});
</script></body></html>"""


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = f"http://localhost:{PORT}"
    print(f"Interfaz lista en {url}  (Ctrl+C para salir)")
    if os.environ.get("DEMO_NOBROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
