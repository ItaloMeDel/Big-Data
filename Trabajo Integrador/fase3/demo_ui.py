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
    {"id": "ingesta", "titulo": "1. Ingesta: de NetCDF a MongoDB",
     "inicio": "Abrimos los NetCDF de ERA5 y nos conectamos a MongoDB.",
     "que": ["Leemos los NetCDF y armamos un documento por celda y hora (°C, mm, m/s, GeoJSON).",
             "Guardamos en lotes de 15,000 documentos con w:1 para ir rápido.",
             "Creamos 5 índices y calculamos la climatología diaria con el Aggregation Pipeline."],
     "decir": "",
     "cmds": [[PY, "-u", "01_ingesta_completa.py"]],
     "explain": [(r"^Grilla", "Leímos la grilla: 77 × 57 celdas por cada hora."),
                 (r"hora \d+/\d+", "Leemos los NetCDF y armamos un documento por celda y hora. Insertamos de 15,000 en 15,000."),
                 (r"^Ingesta:", "Creamos los índices para no escanear todo."),
                 (r"^Índices creados", "Calculamos la climatología diaria con $group y la guardamos con $out."),
                 (r"^Agregaciones en", "Guardamos las métricas de la ingesta.")]},
    {"id": "anomalias", "titulo": "2. Anomalías de temperatura",
     "inicio": "Leemos la temperatura diaria de cada celda desde MongoDB.",
     "que": ["Calculamos z = (T del día − media de la celda) / desviación de la celda.",
             "Marcamos anomalía cuando |z| > 2 y la guardamos en anomalies_daily.",
             "La línea base es el mismo mes, no una climatología de 30 años."],
     "decir": "",
     "cmds": [[PY, "-u", "02_anomalias.py"]],
     "explain": [(r'"anomalias"', "Contamos las celdas-día con |z| > 2, cálidas y frías.")]},
    {"id": "figuras", "titulo": "3. Figuras",
     "inicio": "Consultamos MongoDB para dibujar las figuras.",
     "que": ["Leemos las colecciones de climatología, estadísticas y anomalías.",
             "Sacamos la lluvia extrema (> 5 mm) con $match + $group.",
             "Dibujamos 4 figuras: serie por dominio, temperatura, anomalías y lluvia extrema."],
     "decir": "",
     "cmds": [[PY, "-u", "03_visualizaciones.py"]],
     "explain": [(r"guardados en", "Guardamos las figuras; aparecen abajo.")]},
    {"id": "mapreduce", "titulo": "4. MapReduce con Hadoop",
     "inicio": "Exportamos las observaciones de MongoDB a CSV para Hadoop.",
     "que": ["Exportamos las observaciones de MongoDB a un CSV.",
             "mapper.py emite dominio|día; reducer.py suma y promedia cada clave.",
             "Corremos Hadoop 3.3.6 en modo local, sin HDFS ni YARN."],
     "decir": "",
     "cmds": [[PY, "-u", "05_exportar_para_hadoop.py"], ["bash", "hadoop/run_hadoop.sh", "local"]],
     "keep": r"(filas exportadas|^Hadoop:|number of splits|Running job|map \d+% reduce|completed successfully|Map input records|Map output records|Reduce input groups|Reduce output records|Resultado en|Falta|Error|Exception)",
     "explain": [(r"filas exportadas", "Lanzamos el trabajo MapReduce sobre el CSV."),
                 (r"number of splits", "Hadoop parte el CSV en splits, uno por mapper."),
                 (r"map \d+% reduce 0%", "Map: cada fila emite el par dominio|día → temperatura, lluvia, 1."),
                 (r"map 100% reduce [1-9]", "Reduce: sumamos y promediamos cada clave ya ordenada."),
                 (r"completed successfully", "Terminó el trabajo: una línea por dominio y día.")]},
    {"id": "validacion", "titulo": "5. Validación cruzada",
     "inicio": "Recalculamos todo con NumPy, directo desde los NetCDF.",
     "que": ["Recalculamos temperatura y lluvia por dominio y día con NumPy.",
             "Comparamos contra MongoDB y contra Hadoop.",
             "Esperamos VALIDACION_OK = true con diferencias ≈ 0."],
     "decir": "",
     "cmds": [[PY, "-u", "04_validacion.py"]],
     "explain": [(r"VALIDACION_OK", "Comparamos los tres resultados: NumPy, MongoDB y Hadoop.")]},
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


def mongo_live(db):
    d = _mdb(db)
    ss = d.client.admin.command("serverStatus")
    oc, st = ss.get("opcounters", {}), d.command("dbStats")
    cols = []
    for n in sorted(d.list_collection_names()):
        try:
            cs = next(d[n].aggregate([{"$collStats": {"storageStats": {}}}]), {}).get("storageStats", {})
        except Exception:
            cs = {}
        cols.append({"name": n, "count": cs.get("count", 0), "size": cs.get("size", 0),
                     "storageSize": cs.get("storageSize", 0), "totalIndexSize": cs.get("totalIndexSize", 0),
                     "indexes": [{"name": k, "size": v} for k, v in (cs.get("indexSizes") or {}).items()]})
    return {"t": time.time(), "db": db, "opcounters": {k: oc.get(k, 0) for k in ("insert", "query", "command")},
            "connections": ss.get("connections", {}).get("current"),
            "dbStats": {k: st.get(k) for k in ("collections", "objects", "dataSize", "storageSize", "indexSize")},
            "colls": cols}


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


def _plan(ex):
    es = ex.get("executionStats", {})
    st, p = [], ex.get("queryPlanner", {}).get("winningPlan", {})
    while p:
        p = p.get("queryPlan", p); st.append(p.get("stage"))
        p = p.get("inputStage") or (p.get("inputStages") or [None])[0]
    return {"ms": es.get("executionTimeMillis"), "docs": es.get("totalDocsExamined"),
            "keys": es.get("totalKeysExamined"), "n": es.get("nReturned"),
            "stage": "IXSCAN" if "IXSCAN" in st else ("COLLSCAN" if "COLLSCAN" in st else (st[-1] if st else None))}


def hallazgos(db):
    import datetime
    d = _mdb(db)
    cl, an, rg = d.daily_climatology_etl, d.anomalies_daily, d.regional_stats_etl
    P = {"_id": 0, "day": 1, "latitude": 1, "longitude": 1, "domain": 1}
    hot = cl.find_one({}, dict(P, temp_max=1), sort=[("temp_max", -1)])
    cold = cl.find_one({}, dict(P, temp_min=1), sort=[("temp_min", 1)])
    days = sorted(cl.distinct("day"))
    lats, lons = sorted(cl.distinct("latitude")), sorted(cl.distinct("longitude"))
    dia = list(an.aggregate([{"$match": {"is_anomaly": True}}, {"$group": {"_id": "$day", "n": {"$sum": 1}}},
                             {"$sort": {"n": -1}}, {"$limit": 1}]))
    dom = {x["_id"]: {"anom": x["a"], "total": x["t"]} for x in an.aggregate(
        [{"$group": {"_id": "$domain", "t": {"$sum": 1}, "a": {"$sum": {"$cond": ["$is_anomaly", 1, 0]}}}}])}
    top = list(an.aggregate([{"$match": {"is_anomaly": True}}, {"$addFields": {"az": {"$abs": "$z"}}},
                             {"$sort": {"az": -1}}, {"$limit": 5},
                             {"$project": {"_id": 0, "az": 0, "is_anomaly": 0}}]))
    pr = rg.find_one({}, {"_id": 0, "day": 1, "domain": 1, "max_precipitation": 1}, sort=[("max_precipitation", -1)])
    obs = d.climate_observations
    r = res_dir(db)
    return {"db": db, "docs": obs.estimated_document_count(), "celdas": d.spatial_grid_catalog.count_documents({}),
            "dias": days, "lat_rango": [lats[0], lats[-1]] if lats else None,
            "lon_rango": [lons[0], lons[-1]] if lons else None,
            "periodo": [str(x["timestamp"]) for x in (obs.find_one({}, {"timestamp": 1}, sort=[("timestamp", s)]) for s in (1, -1)) if x],
            "horas": len(obs.distinct("timestamp")),
            "hot": hot, "cold": cold, "dia_max": {"day": dia[0]["_id"], "n": dia[0]["n"]} if dia else None,
            "por_dominio": dom, "calidas": an.count_documents({"is_anomaly": True, "z": {"$gt": 0}}),
            "frias": an.count_documents({"is_anomaly": True, "z": {"$lt": 0}}),
            "top": top, "precip": pr, "geo": _GEO.get(db),
            "metricas": read_json(r / "metricas_ingesta.json"), "validacion": read_json(r / "resultado_validacion.json"),
            "res_dir": r.name}


_GEO = {}


def geo_bench(db):
    import datetime
    if db in _GEO:
        return _GEO[db]
    d = _mdb(db)
    obs, cl = d.climate_observations, d.daily_climatology_etl
    lats, lons = sorted(cl.distinct("latitude")), sorted(cl.distinct("longitude"))
    geo = None
    t0 = obs.find_one({}, {"timestamp": 1}, sort=[("timestamp", 1)])
    if t0 and lats and lons:
        t0 = t0["timestamp"].replace(hour=0, minute=0, second=0, microsecond=0)
        la, lo = lats[len(lats) // 2], lons[len(lons) // 2]
        f = {"location": {"$geoWithin": {"$centerSphere": [[lo, la], 50 / 6378.1]}},
             "timestamp": {"$gte": t0, "$lt": t0 + datetime.timedelta(days=1)}}
        geo = {"lat": la, "lon": lo, "km": 50, "dia": str(t0.date()),
               "con_indice": _plan(obs.find(f).max_time_ms(60000).explain()),
               "sin_indice": _plan(obs.find(f).hint([("$natural", 1)]).max_time_ms(60000).explain())}
        _GEO[db] = geo
    return geo


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
        if u.path == "/api/mongo/live":
            try:
                return self._send(200, json.dumps(mongo_live(clean_db(q.get("db")))))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
        if u.path.startswith("/api/viz/"):
            try:
                r = viz(u.path, q, clean_db(q.get("db")))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
            return self._send(200, json.dumps(r)) if r is not None else self._send(404, "no encontrado", "text/plain")
        if u.path == "/api/hallazgos":
            try:
                return self._send(200, json.dumps(hallazgos(clean_db(q.get("db"))), default=str))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
        if u.path == "/api/hallazgos/geo":
            try:
                return self._send(200, json.dumps(geo_bench(clean_db(q.get("db"))), default=str))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
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
<title>Anomalías climáticas ERA5</title>
<style>
:root{--bg:#f6f3ec;--card:#fffdf8;--ink:#1d1b18;--mut:#6b665c;--line:#d9d3c7;--ac:#7a1f2b;--acbg:#f4e9e7;--bad:#b3261e;--ok:#1d1b18;
 --serif:Georgia,"Times New Roman",serif;--mono:ui-monospace,"DejaVu Sans Mono",Menlo,Consolas,monospace}
html{font-size:16px}html.expo{font-size:20px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:1rem/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
h1,h2,h3{font-family:var(--serif);font-weight:normal}
code{font-family:var(--mono);font-size:.9em}
header{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;max-width:1100px;margin:0 auto;padding:22px 16px 12px;border-bottom:1px solid var(--ink)}
header h1{margin:0;font-size:1.45rem;flex:1;min-width:260px}header .who{font-size:.85rem;color:var(--mut);letter-spacing:.03em}
header label{font-size:.85rem;color:var(--mut);cursor:pointer}header input{accent-color:var(--ac);vertical-align:-2px}
main{max-width:1100px;margin:0 auto;padding:14px 16px 40px}
.tabs{display:flex;gap:22px;margin:0 0 16px;border-bottom:1px solid var(--line)}
.tab{font:inherit;background:none;border:0;border-bottom:2px solid transparent;border-radius:0;padding:6px 0;margin-bottom:-1px;color:var(--mut);cursor:pointer}
.tab.on{color:var(--ink);border-bottom-color:var(--ac)}
.bar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin-bottom:12px}
.stline{margin:0 0 12px;font:.8rem var(--mono);color:var(--mut)}.chip{color:var(--ink)}.chip.bad{color:var(--bad)}
label{font-size:.9rem;color:var(--mut)}
select,button{font:inherit;font-size:.9rem;padding:6px 12px;border-radius:3px;border:1px solid var(--ink);background:var(--card);color:var(--ink)}
select{border-color:var(--line)}button{cursor:pointer}button:hover{background:#efe9dd}
button.go:disabled{opacity:.4;cursor:not-allowed}
button.all{background:var(--ac);border-color:var(--ac);color:#fff}button.all:hover{background:#651823}
.flow{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:12px 12px 6px;overflow-x:auto}
.flow svg{display:block;width:100%;min-width:640px;height:auto}
.fs .bx{fill:var(--card);stroke:var(--line);stroke-width:1}.fs .t{font:17px var(--serif);fill:var(--mut)}.fs .s{font:12px var(--mono);fill:var(--mut)}.fs .dn{fill:var(--ink);display:none}
.fs.run .bx{stroke:var(--ac);stroke-width:2;fill:var(--acbg)}.fs.run .t,.fs.run .s{fill:var(--ac)}
.fs.ok .bx{stroke:var(--ink)}.fs.ok .t,.fs.ok .s{fill:var(--ink)}.fs.ok .dn{display:block}
.fs.err .bx{stroke:var(--bad);stroke-width:2}.fs.err .t{fill:var(--bad)}
.flow .ar{stroke:var(--mut);stroke-width:1;fill:none}
.now{margin:0 0 16px;padding:8px 12px;border:1px solid var(--line);border-top:0;border-left:3px solid var(--ac);background:var(--card);font-size:.95rem;min-height:2.4em}
.now b{font-weight:600;color:var(--ac)}
.cols{display:grid;grid-template-columns:1fr 310px;gap:16px;align-items:start}@media(max-width:900px){.cols{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:12px 16px;margin-bottom:12px}
.card h2{margin:0;font-size:1.15rem;display:flex;gap:12px;align-items:center;flex-wrap:wrap}.card h2 .sp{flex:1}
#steps .card{border-left:3px solid var(--line)}#steps .card[data-st=run]{border-left-color:var(--ac)}#steps .card[data-st=ok]{border-left-color:var(--ink)}#steps .card[data-st=err]{border-left-color:var(--bad)}
.badge{font:.8rem var(--mono);color:var(--mut)}.badge.run{color:var(--ac)}.badge.ok{color:var(--ink)}.badge.err{color:var(--bad)}
details{margin:6px 0 0}summary{cursor:pointer;color:var(--mut);font-size:.85rem}ul{margin:6px 0 4px 18px;padding:0}li{margin:2px 0;font-size:.92rem}
.term{display:none;background:#1d1b18;color:#cfc8b8;font:.72rem/1.4 var(--mono);padding:8px 10px;border-radius:3px;max-height:130px;overflow:auto;white-space:pre-wrap;margin:8px 0}
.term .cmd{color:#e6dcc4}
.res{margin-top:8px}.mets{display:flex;gap:8px 30px;flex-wrap:wrap;margin:6px 0}.met{min-width:90px}
.met b{display:block;font:1.6rem/1.15 var(--mono);font-weight:normal}.met span{font-size:.75rem;color:var(--mut)}
.figs{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px;margin-top:8px}.figs img{width:100%;border:1px solid var(--line);background:#fff}
table{border-collapse:collapse;width:100%;font-size:.82rem;margin-top:8px;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left}th{border-bottom-color:var(--ink);font-weight:600}
.verdict{font:1.7rem/1.2 var(--serif);margin:4px 0}.verdict.ok{color:var(--ink)}.verdict.bad{color:var(--bad)}
.side h3{margin:0 0 6px;font-size:1rem}.side table td{padding:2px 4px;font-family:var(--mono);font-size:.78rem}.note{font-size:.8rem;color:var(--mut)}
[hidden]{display:none!important}
.side{position:sticky;top:10px;max-height:calc(100vh - 20px);overflow:auto}
.ml{border-top:1px solid var(--line);margin-top:12px;padding-top:10px}.mlb{margin:8px 0 12px}.mlb>p.note{margin:3px 0 0}
#ml_ips{font-family:var(--mono);font-weight:normal}
#ml_cv{display:block;width:100%;height:60px;background:var(--bg);border:1px solid var(--line);margin-top:4px}
.mlr{display:grid;grid-template-columns:1fr auto;gap:2px 8px;font-size:.75rem;padding:2px 0}.mlr .n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mlr .v{font-family:var(--mono);font-weight:normal}
.bar0{grid-column:1/3;height:4px;background:#ece6da;overflow:hidden}.bar0 i{display:block;height:100%;width:0;background:var(--ac);transition:width .8s ease}
.bar0.ix i{background:#8a8478}@keyframes chg{from{background:#efe2c8}to{background:transparent}}.chg{animation:chg 1s ease-out}
.rgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:900px){.rgrid{grid-template-columns:1fr}}
.map{display:block;width:100%;max-width:399px;image-rendering:pixelated;cursor:crosshair;border:1px solid var(--line);margin-top:8px}
.wide{display:block;max-width:100%;margin-top:8px}#cv_h{cursor:crosshair}
.lg{max-width:300px;margin-top:6px}.lg canvas{display:block;width:100%;height:12px;border:1px solid var(--line)}.lgl{display:flex;justify-content:space-between;font:.7rem var(--mono);color:var(--mut)}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:#f6f3ec;font:12px/1.35 var(--mono);padding:5px 8px;border-radius:3px;display:none;z-index:9}
input[type=range]{vertical-align:middle;accent-color:var(--ac)}
.hgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}.hk{font:1.45rem var(--serif);margin:4px 0}p.hi{font-style:italic;color:var(--mut);font-size:.82rem;margin:4px 0 0}
#hal>h2{font-size:1.25rem;border-bottom:1px solid var(--line);padding-bottom:4px}
.hb{display:grid;grid-template-columns:110px 1fr;gap:6px 10px;align-items:center;font-size:.82rem}.hb .b{height:14px;background:var(--ac);min-width:2px}.hb .b.s{background:#8a8478}
html.expo .term,html.expo aside.side,html.expo details,html.expo .stline{display:none!important}html.expo .cols{grid-template-columns:1fr}
@media print{header,nav.tabs,#v_pasos,#v_res,#tip,.noprint{display:none!important}#v_hal{display:block!important}body{background:#fff}.card{break-inside:avoid;border-color:#999}main{padding:0}}
</style></head><body>
<header><h1>Anomalías climáticas en el Perú · ERA5 + MongoDB + Hadoop</h1><span class="who">UCSM · EPIS · Big Data</span>
 <label><input type="checkbox" id="expo"> Modo exposición</label></header>
<main>
<nav class="tabs"><button id="tb_pasos" class="tab on">Pipeline</button><button id="tb_res" class="tab">Resultados</button><button id="tb_hal" class="tab">Hallazgos</button></nav>
<div id="v_pasos">
<p class="stline"><span id="c_mongo" class="chip">Mongo: …</span> · <span id="c_hadoop" class="chip">Hadoop: …</span> · <span id="c_datos" class="chip">Datos: …</span></p>
<div class="bar">
 <label>Horas <select id="hours"><option value="24">24 h · 1 día</option><option value="168" selected>168 h · 7 días</option><option value="744">744 h · mes completo</option></select></label>
 <label>Base <select id="db"><option value="era5_demo" selected>era5_demo (prueba)</option><option value="era5_climate_db">era5_climate_db (principal)</option></select></label>
 <span style="flex:1"></span>
 <button id="all" class="go all">Ejecutar todo</button>
</div>
<div class="flow"><svg viewBox="0 0 1000 92" role="img" aria-label="Flujo del pipeline">
 <defs><marker id="ah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="#6b665c"/></marker></defs>
 <g class="fs" id="f0"><rect class="bx" x="1" y="4" width="166" height="70" rx="3"/><text class="t" x="84" y="34" text-anchor="middle">Datos ERA5</text><text class="s" x="84" y="56" text-anchor="middle">744 h × 4,389 celdas</text><rect class="dn" x="1" y="80" width="166" height="3"/></g>
 <g class="fs" id="f1"><rect class="bx" x="209" y="4" width="166" height="70" rx="3"/><text class="t" x="292" y="34" text-anchor="middle">MongoDB</text><text class="s" x="292" y="56" text-anchor="middle">índices 2dsphere</text><rect class="dn" x="209" y="80" width="166" height="3"/></g>
 <g class="fs" id="f2"><rect class="bx" x="417" y="4" width="166" height="70" rx="3"/><text class="t" x="500" y="34" text-anchor="middle">Anomalías</text><text class="s" x="500" y="56" text-anchor="middle">|z| &gt; 2</text><rect class="dn" x="417" y="80" width="166" height="3"/></g>
 <g class="fs" id="f3"><rect class="bx" x="625" y="4" width="166" height="70" rx="3"/><text class="t" x="708" y="34" text-anchor="middle">MapReduce (Hadoop)</text><text class="s" x="708" y="56" text-anchor="middle">mapper → reducer</text><rect class="dn" x="625" y="80" width="166" height="3"/></g>
 <g class="fs" id="f4"><rect class="bx" x="833" y="4" width="166" height="70" rx="3"/><text class="t" x="916" y="34" text-anchor="middle">Validación</text><text class="s" x="916" y="56" text-anchor="middle">NumPy = Mongo = Hadoop</text><rect class="dn" x="833" y="80" width="166" height="3"/></g>
 <path class="ar" d="M171 39H205" marker-end="url(#ah)"/><path class="ar" d="M379 39H413" marker-end="url(#ah)"/><path class="ar" d="M587 39H621" marker-end="url(#ah)"/><path class="ar" d="M795 39H829" marker-end="url(#ah)"/>
</svg></div>
<div class="now" id="now">Sin ejecución en curso.</div>
<div class="cols"><div id="steps"></div>
 <aside class="side card"><h3>Base de datos</h3><div id="dbstate" class="note">…</div>
 <div class="ml"><h3>MongoDB en vivo <span id="ml_st" class="note"></span></h3>
  <div class="mlb"><div id="ml_ipsr"><b id="ml_ips" style="font-size:1.3rem">—</b> inserts/s <span class="note">· conexiones <b id="ml_con">—</b></span></div>
   <canvas id="ml_cv" width="300" height="60"></canvas>
   <p class="note">Inserciones por segundo en el servidor, últimos 60 s (<code>serverStatus</code>).</p></div>
  <div class="mlb"><div id="ml_cols"></div>
   <p class="note">Documentos por colección (<code>$collStats</code>).</p></div>
  <div class="mlb"><div id="ml_obj" class="note"></div><div id="ml_sz"></div>
   <p class="note">Datos, índices y disco (<code>dbStats</code>).</p></div>
  <div class="mlb"><div id="ml_idx"></div>
   <p class="note">Tamaño de cada índice (<code>indexSizes</code>).</p></div>
  <button id="ml_compass">Abrir en Compass</button> <span id="ml_cp" class="note"></span></div></aside></div>
<div id="final"></div>
</div>
<div id="v_res" hidden>
<div class="bar"><button id="play" class="go">Animar</button>
 <label>Día <input type="range" id="day" min="0" max="0" value="0" style="width:260px"></label><b id="dlab">—</b>
 <span style="flex:1"></span><span id="pf" class="note"></span><span class="note">base: <b id="rdb"></b></span><button id="reload">Recargar</button></div>
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
<div id="v_hal" hidden>
<div class="bar noprint"><span class="note">base: <b id="hdb"></b></span><span style="flex:1"></span><button id="hreload">Recalcular</button><button id="hprint" class="go">Imprimir / PDF</button></div>
<div id="hal" class="note">…</div>
</div>
</main><div id="tip"></div>
<script>
const $=s=>document.querySelector(s);let STEPS=[],busy=false;
const hours=()=>$('#hours').value, db=()=>$('#db').value;
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt=n=>typeof n==='number'?n.toLocaleString('es-PE'):n;
function chip(id,ok,txt){const e=$(id);e.textContent=txt;e.className='chip '+(ok?'ok':'bad')}
async function refresh(){try{const s=await (await fetch('/api/status?db='+db())).json();
 chip('#c_mongo',s.mongo,s.mongo?'Mongo: conectado':'Mongo: sin respuesta');chip('#c_hadoop',s.hadoop,s.hadoop?'Hadoop: listo':'Hadoop: no encontrado');chip('#c_datos',s.datos,s.datos?'Datos: listos':'Datos: faltan los .nc');
 const c=s.colecciones||{};const k=Object.keys(c);
 $('#dbstate').innerHTML=k.length?'<b>'+esc(s.db)+'</b><table>'+k.map(n=>`<tr><td>${esc(n)}</td><td style="text-align:right">${fmt(c[n])}</td></tr>`).join('')+'</table>':'<b>'+esc(s.db)+'</b><br>sin colecciones todavía';
}catch(e){chip('#c_mongo',false,'Servidor: sin respuesta')}}
function build(){$('#steps').innerHTML=STEPS.map(s=>`<div class="card" id="s_${s.id}" data-st="pend"><h2>${esc(s.titulo)}<span class="sp"></span><span class="badge" id="b_${s.id}">pendiente</span><button class="go" id="r_${s.id}">Ejecutar</button></h2>
 <details><summary>Qué hacemos</summary><ul>${s.que.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>
 <div class="term" id="t_${s.id}"></div><div class="res" id="x_${s.id}"></div></div>`).join('');
 STEPS.forEach(s=>$('#r_'+s.id).onclick=()=>runStep(s.id))}
const FLOW={ingesta:[0,1],anomalias:[2],figuras:[2],mapreduce:[3],validacion:[4]};
function flow(id,st){(FLOW[id]||[]).forEach(i=>{const g=$('#f'+i);if(!(st==='run'&&g.classList.contains('ok')&&id==='figuras'))g.setAttribute('class','fs '+st)})}
function setBadge(id,cls,txt){const b=$('#b_'+id);b.className='badge '+cls;b.textContent=txt;$('#s_'+id).dataset.st=cls;flow(id,cls)}
function setBusy(v){busy=v;document.querySelectorAll('button.go').forEach(b=>b.disabled=v);if(window.mlKick)mlKick()}
function runStep(id){return new Promise(res=>{if(busy){res(false);return}
 if(id==='ingesta'&&db()==='era5_climate_db'&&!confirm('Esto BORRARÁ y recargará la base PRINCIPAL del informe (era5_climate_db). ¿Seguro?')){res(false);return}
 setBusy(true);const t=$('#t_'+id),a=$('#now'),T=STEPS.find(s=>s.id===id).titulo;t.style.display='block';t.innerHTML='';a.innerHTML='<b>'+esc(T)+'</b> · Iniciamos…';$('#x_'+id).innerHTML='';
 setBadge(id,'run','ejecutando');
 let n=0,finished=false;const es=new EventSource(`/api/run?step=${id}&hours=${hours()}&db=${db()}`);
 es.onmessage=async e=>{const m=JSON.parse(e.data);
  if(m.t==='line'||m.t==='cmd'){const d=document.createElement('div');if(m.t==='cmd')d.className='cmd';d.textContent=m.v;t.appendChild(d);if(++n>500)t.removeChild(t.firstChild);t.scrollTop=t.scrollHeight}
  else if(m.t==='ahora'){a.innerHTML='<b>'+esc(T)+'</b> · '+esc(m.v)}
  else if(m.t==='done'){finished=true;es.close();const ok=m.code===0;setBadge(id,ok?'ok':'err',(ok?'listo · ':'error · ')+m.seg+' s');
   a.innerHTML=ok?'<b>'+esc(T)+'</b> · Terminamos en '+m.seg+' s.':'<b>'+esc(T)+'</b> · Terminó con error (código '+m.code+'). Revisa el log.';
   if(ok)await showResult(id);setBusy(false);refresh();res(ok)}};
 es.onerror=()=>{if(!finished){es.close();setBadge(id,'err','conexión perdida');a.innerHTML='<b>'+esc(T)+'</b> · Se perdió la conexión con el servidor.';setBusy(false);res(false)}}})}
async function showResult(id){const r=await (await fetch(`/api/results?step=${id}&db=${db()}`)).json();let h='';const el=$('#x_'+id);
 const met=(v,l)=>`<div class="met"><b>${fmt(v)}</b><span>${l}</span></div>`;
 if(id==='ingesta'&&r.metricas){const m=r.metricas;h='<div class="mets">'+met(m.documentos_observaciones,'documentos de observación')+met(m.docs_por_segundo,'docs / segundo')+met(m.segundos_ingesta+' s','ingesta')+met(m.segundos_indices+' s','índices')+met(m.segundos_agregacion+' s','agregaciones')+met(m.tamano_coleccion_MB+' MB','colección')+met(m.documentos_climatologia_diaria,'climatología diaria')+'</div>'}
 if(id==='anomalias'&&r.resumen){const m=r.resumen;h='<div class="mets">'+met(m.anomalias,'anomalías |z|>2')+met(m.pct_anomalias+' %','de las celdas-día')+met(m.calidas,'cálidas')+met(m.frias,'frías')+met(m.por_dominio.Continental_Peru??0,'en tierra')+met(m.por_dominio.Pacific_Ocean??0,'en océano')+'</div>'}
 if(id==='figuras'){h='<div class="figs">'+(r.figuras||[]).map(u=>`<a href="${u}" target="_blank"><img src="${u}"></a>`).join('')+'</div>';
  if((r.top||[]).length)h+='<table><tr><th>día</th><th>lat</th><th>lon</th><th>T (°C)</th><th>z</th><th>tipo</th></tr>'+r.top.map(x=>`<tr><td>${x.day}</td><td>${x.latitude}</td><td>${x.longitude}</td><td>${x.temp_mean}</td><td>${x.z}</td><td>${x.tipo}</td></tr>`).join('')+'</table>'}
 if(id==='mapreduce'){h='<div class="mets">'+met(r.total,'claves en la salida (dominio|día)')+'</div>';
  if((r.filas||[]).length)h+='<table><tr><th>clave</th><th>temp. media (°C)</th><th>precip. total (mm)</th><th>muestras</th></tr>'+r.filas.map(x=>`<tr><td>${esc(x.clave)}</td><td>${x.temp_media}</td><td>${x.precip_total}</td><td>${fmt(+x.muestras)}</td></tr>`).join('')+'</table>'}
 if(id==='validacion'&&r.validacion){const v=r.validacion,ok=v.VALIDACION_OK;h=`<div class="verdict ${ok?'ok':'bad'}">${ok?'Validación correcta: NumPy, MongoDB y Hadoop coinciden.':'La validación encontró diferencias.'}</div><div class="mets" style="margin-top:8px">`+met(v.observaciones_en_mongodb,'docs en MongoDB')+met(v.observaciones_esperadas,'docs esperados')+met(v.max_dif_temp_C+' °C','dif. máx. temp. Mongo–NumPy')+met(v.max_dif_precip_mm+' mm','dif. máx. precipitación')+(v.hadoop_filas!==undefined?met(v.hadoop_max_dif_temp_C+' °C','dif. máx. temp. Hadoop–NumPy')+met(v.hadoop_filas,'claves comparadas con Hadoop'):'')+'</div>'}
 el.innerHTML=h}
$('#all').onclick=async()=>{if(busy)return;$('#final').innerHTML='';document.querySelectorAll('.fs').forEach(g=>g.setAttribute('class','fs'));let ok=true;for(const s of STEPS){ok=await runStep(s.id);if(!ok)break}
 $('#final').innerHTML=ok?'<div class="card"><div class="verdict ok">Pipeline completo.</div><span class="note">'+hours()+' h · base '+esc(db())+'</span></div>':'<div class="card"><div class="verdict bad">El pipeline se detuvo por un error.</div></div>'};
$('#hours').onchange=()=>{};
{const e=$('#expo'),f=v=>{document.documentElement.classList.toggle('expo',v);e.checked=v};try{f(localStorage.getItem('expo')==='1')}catch(_){}e.onchange=()=>{f(e.checked);try{localStorage.setItem('expo',e.checked?'1':'0')}catch(_){}}}$('#db').onchange=refresh;
// ===== Pestañas =====
function tab(t){for(const x of ['pasos','res','hal']){$('#v_'+x).hidden=x!==t;$('#tb_'+x).classList.toggle('on',x===t)}if(t==='res')loadRes();if(t==='hal')loadHal()}
$('#tb_pasos').onclick=()=>tab('pasos');$('#tb_res').onclick=()=>tab('res');$('#tb_hal').onclick=()=>tab('hal');
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
function stop(){V.run++;$('#play').textContent='Animar'}
$('#play').onclick=async()=>{if($('#play').textContent==='Pausar'){stop();return}const id=++V.run;$('#play').textContent='Pausar';
 while(V.run===id&&V.days.length){V.di=(V.di+1)%V.days.length;try{await showDay()}catch(e){$('#rmsg').textContent='Error: '+e.message;stop();break}await new Promise(r=>setTimeout(r,600))}};
$('#day').oninput=()=>{V.di=+$('#day').value;showDay().catch(e=>$('#rmsg').textContent='Error: '+e.message)};
function hookMap(cv,which){
 cv.onmousemove=e=>{const g=which==='t'?V.T:V.A;if(!g||!g.grid.length)return;const c=cellAt(cv,e,g.grid.length,g.grid[0].length);if(!c)return hideTip();
  const v=g.grid[c[0]][c[1]];tip(e,`lat ${g.lats[c[0]].toFixed(2)}°, lon ${g.lons[c[1]].toFixed(2)}°<br>`+(v==null?'sin dato':which==='t'?v.toFixed(2)+' °C':'z = '+v.toFixed(2)))};
 cv.onmouseleave=hideTip;
 cv.onclick=e=>{const g=V.T;if(!g||!g.grid.length)return;const c=cellAt(cv,e,g.grid.length,g.grid[0].length);if(!c)return;V.sel=c;drawMaps();cellSeries();geo()}}
hookMap($('#cv_t'),'t');hookMap($('#cv_a'),'a');
function drawLine(s){const cv=$('#cv_line'),W=cv.width=640,H=cv.height=240,x=cv.getContext('2d'),p={l:46,r:12,t:12,b:30};
 const pts=s.serie.filter(d=>d.temp_mean!=null);x.clearRect(0,0,W,H);if(!pts.length){x.fillStyle='#6b665c';x.fillText('Sin datos para esta celda',W/2-60,H/2);return}
 const d0=pts[0].day,d1=pts[pts.length-1].day,vs=pts.map(d=>d.temp_mean);let lo=Math.min(...vs),hi=Math.max(...vs);if(hi-lo<.5){lo-=.5;hi+=.5}
 const X=d=>p.l+(d-d0)/Math.max(1,d1-d0)*(W-p.l-p.r),Y=v=>H-p.b-(v-lo)/(hi-lo)*(H-p.t-p.b);
 x.font='11px ui-monospace,monospace';x.lineWidth=1;x.strokeStyle='#d9d3c7';x.fillStyle='#6b665c';x.textAlign='right';
 for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,y=Y(v);x.beginPath();x.moveTo(p.l,y);x.lineTo(W-p.r,y);x.stroke();x.fillText(v.toFixed(1)+'°',p.l-5,y+4)}
 x.textAlign='center';pts.forEach(d=>{if(d.day===d0||d.day===d1||d.day%5===0)x.fillText(d.day,X(d.day),H-p.b+15)});x.fillText('día',W-p.r-8,H-4);
 const cur=V.days[V.di];if(cur>=d0&&cur<=d1){x.setLineDash([4,3]);x.strokeStyle='#999';x.beginPath();x.moveTo(X(cur),p.t);x.lineTo(X(cur),H-p.b);x.stroke();x.setLineDash([])}
 x.strokeStyle='#1d1b18';x.lineWidth=1.5;x.beginPath();pts.forEach((d,k)=>k?x.lineTo(X(d.day),Y(d.temp_mean)):x.moveTo(X(d.day),Y(d.temp_mean)));x.stroke();
 pts.forEach(d=>{x.fillStyle=d.is_anomaly?'#7a1f2b':'#1d1b18';x.beginPath();x.arc(X(d.day),Y(d.temp_mean),d.is_anomaly?5:2.5,0,7);x.fill()})}
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
 x.font='11px ui-monospace,monospace';x.fillStyle='#6b665c';x.textAlign='right';
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
// ===== MongoDB en vivo =====
const ML={prev:null,hist:[],timer:null,inflight:false,db:null};
const MB=n=>n==null?'—':(n/1048576).toFixed(n<10485760?2:1)+' MB';
function hl(el){el.classList.remove('chg');void el.offsetWidth;el.classList.add('chg')}
function setT(el,t){if(el.textContent!==t){const had=el.textContent!==''&&el.textContent!=='—';el.textContent=t;if(had)hl(el.closest('.mlr')||el)}}
function mlRows(box,items,cls){const keys=items.map(i=>i.k).join('|');
 if(box.dataset.keys!==keys){box.dataset.keys=keys;box.innerHTML=items.length?items.map(i=>`<div class="mlr"><span class="n" title="${esc(i.k)}">${esc(i.label)}</span><b class="v"></b><div class="bar0 ${cls||''}"><i></i></div></div>`).join(''):'<span class="note">sin colecciones</span>'}
 items.forEach((it,n)=>{const r=box.children[n];setT(r.querySelector('.v'),it.val);r.querySelector('i').style.width=Math.max(0,Math.min(100,it.pct))+'%'})}
function mlChart(){const cv=$('#ml_cv'),x=cv.getContext('2d'),W=cv.width,H=cv.height,now=Date.now()/1000;x.clearRect(0,0,W,H);
 const h=ML.hist.filter(p=>p.t>=now-60);if(!h.length)return;const mx=Math.max(1,...h.map(p=>p.v)),X=t=>(t-(now-60))/60*W,Y=v=>H-3-v/mx*(H-14);
 x.beginPath();x.moveTo(X(h[0].t),H);h.forEach(p=>x.lineTo(X(p.t),Y(p.v)));x.lineTo(X(h[h.length-1].t),H);x.closePath();x.fillStyle='rgba(31,111,235,.18)';x.fill();
 x.beginPath();h.forEach((p,k)=>k?x.lineTo(X(p.t),Y(p.v)):x.moveTo(X(p.t),Y(p.v)));x.strokeStyle='#7a1f2b';x.lineWidth=1.5;x.stroke();
 x.fillStyle='#6b665c';x.font='10px ui-monospace,monospace';x.fillText('máx '+fmt(Math.round(mx))+'/s',4,10);x.textAlign='right';x.fillText('−60 s … ahora',W-4,10);x.textAlign='left'}
function mlDraw(r){if(ML.db!==r.db){ML.db=r.db;['#ml_cols','#ml_sz','#ml_idx'].forEach(s=>{$(s).dataset.keys='';$(s).innerHTML=''})}
 const oc=r.opcounters;if(ML.prev){const dt=r.t-ML.prev.t,di=oc.insert-ML.prev.oc.insert;const v=dt>0&&di>=0?di/dt:0;ML.hist.push({t:r.t,v});setT($('#ml_ips'),fmt(Math.round(v)))}
 ML.prev={t:r.t,oc};ML.hist=ML.hist.filter(p=>p.t>=r.t-60);mlChart();setT($('#ml_con'),String(r.connections??'—'));
 const mc=Math.max(1,...r.colls.map(c=>c.count));mlRows($('#ml_cols'),r.colls.map(c=>({k:c.name,label:c.name,val:fmt(c.count)+' docs · '+MB(c.size),pct:c.count/mc*100})));
 const s=r.dbStats,ms=Math.max(1,s.dataSize||0,s.indexSize||0,s.storageSize||0);setT($('#ml_obj'),`${esc(r.db)}: ${fmt(s.collections)} colecciones · ${fmt(s.objects)} objetos`);
 mlRows($('#ml_sz'),[{k:'d',label:'Datos (dataSize)',val:MB(s.dataSize),pct:s.dataSize/ms*100},{k:'i',label:'Índices (indexSize)',val:MB(s.indexSize),pct:s.indexSize/ms*100},{k:'s',label:'En disco (storageSize)',val:MB(s.storageSize),pct:s.storageSize/ms*100}]);
 const ix=r.colls.flatMap(c=>c.indexes.map(i=>({k:c.name+'.'+i.name,label:i.name+' · '+c.name,size:i.size}))),mi=Math.max(1,...ix.map(i=>i.size));
 mlRows($('#ml_idx'),ix.map(i=>({k:i.k,label:i.label,val:MB(i.size),pct:i.size/mi*100})),'ix')}
async function mlTick(){clearTimeout(ML.timer);if(!ML.inflight&&!$('#v_pasos').hidden){ML.inflight=true;
 try{mlDraw(await J('/api/mongo/live?db='+encodeURIComponent(db())));$('#ml_st').textContent=busy?'· cada 1 s':'· cada 5 s'}
 catch(e){$('#ml_st').textContent='· error: '+e.message}ML.inflight=false}ML.timer=setTimeout(mlTick,busy?1000:5000)}
window.mlKick=()=>mlTick();
$('#db').addEventListener('change',()=>mlTick());$('#tb_pasos').addEventListener('click',()=>mlTick());
$('#ml_compass').onclick=async()=>{const u='mongodb://localhost:27017';let ok=false;try{await navigator.clipboard.writeText(u);ok=true}catch(e){
 const t=document.createElement('textarea');t.value=u;document.body.appendChild(t);t.select();try{ok=document.execCommand('copy')}catch(_){}t.remove()}
 $('#ml_cp').textContent=ok?'copiado: pégalo en Compass → New connection':'copia a mano: '+u};
mlTick();
// ===== Hallazgos (datos reales de /api/hallazgos) =====
const DOMN={Continental_Peru:'tierra (Perú continental)',Pacific_Ocean:'océano Pacífico'};
const dn=d=>DOMN[d]||d, n2=v=>v==null?'—':(+v).toLocaleString('es-PE',{maximumFractionDigits:2});
function zona(h,lat){if(!h.lat_rango)return'';const[a,b]=h.lat_rango,t=(lat-a)/(b-a||1);return t<1/3?'sur':t<2/3?'centro':'norte'}
// franja andina aproximada: entre ~0.7° tierra adentro de la costa y el borde oriental andino (interpolación lineal por latitud)
const ipl=(P,la)=>{for(let i=1;i<P.length;i++)if(la>=P[i][0])return P[i-1][1]+(P[i][1]-P[i-1][1])*(la-P[i-1][0])/(P[i][0]-P[i-1][0]);return null};
const COSTA=[[-4,-81.3],[-6,-81.1],[-8,-79.2],[-10,-78.2],[-12,-77.1],[-14,-76.2],[-16,-74.4],[-17,-72],[-18.5,-70.4]],
 ESTE=[[-4,-79],[-5,-78.5],[-8,-77],[-10,-75.8],[-12,-74.5],[-14,-71.5],[-16,-69.5],[-18.5,-69.5]];
function sierra(la,lo,dom){if(dom!=='Continental_Peru')return false;const c=ipl(COSTA,la),e=ipl(ESTE,la);return c!=null&&e!=null&&lo>c+0.7&&lo<e}
const card=(t,k,body,i)=>`<div class="card"><h2>${t}</h2>${k?`<div class="hk">${k}</div>`:''}${body||''}${i?`<p class="hi">${i}</p>`:''}</div>`;
async function loadHal(){const d=db();$('#hdb').textContent=d;$('#hal').innerHTML='Calculando con MongoDB…';
 try{const h=await J('/api/hallazgos?db='+encodeURIComponent(d));let o='';const m=h.metricas,v=h.validacion,nd=h.dias.length;
  o+='<h2 style="margin:4px 0 10px">1. Pregunta y datos</h2><div class="hgrid">'+
   card('Pregunta de investigación','',"<p>¿Dónde y cuándo se presentan anomalías térmicas en el Perú y el Pacífico Oriental?</p>",'Anomalía: |z| &gt; 2 respecto a la media y desviación diaria de cada celda.')+
   card('Fuente y periodo','ERA5 (reanálisis horario)',`<p>${esc(h.periodo[0]||'—')} → ${esc(h.periodo[1]||'—')}<br>${nd} días cargados</p>`,`Lat ${h.lat_rango?h.lat_rango.join(' a '):'—'}°, lon ${h.lon_rango?h.lon_rango.join(' a '):'—'}°.`)+
   card('Volumen',fmt(h.docs)+' documentos',`<p>${fmt(h.celdas)} celdas × ${fmt(h.horas)} horas</p>`,`Cada documento es una observación horaria de una celda (${fmt(h.celdas*h.horas)} esperadas).`)+'</div>';
  o+='<h2 style="margin:14px 0 10px">2. Hallazgos automáticos</h2><div class="hgrid">';
  if(h.hot)o+=card('Celda más cálida · máxima horaria del día (temp_max)',n2(h.hot.temp_max)+' °C',`<p>lat ${h.hot.latitude}, lon ${h.hot.longitude} · día ${h.hot.day}</p>`,`El valor horario más alto se registró en el ${zona(h,h.hot.latitude)} del área, en ${dn(h.hot.domain)}.`);
  if(h.cold)o+=card('Celda más fría · mínima horaria del día (temp_min)',n2(h.cold.temp_min)+' °C',`<p>lat ${h.cold.latitude}, lon ${h.cold.longitude} · día ${h.cold.day}</p>`,`El valor horario más bajo se registró en el ${zona(h,h.cold.latitude)} del área, en ${dn(h.cold.domain)}${sierra(h.cold.latitude,h.cold.longitude,h.cold.domain)?'; por su latitud/longitud se ubica en la sierra (aprox.)':''}.`);
  if(h.hot&&h.cold)o+=card('Rango de temperatura',n2(h.hot.temp_max-h.cold.temp_min)+' °C',`<p>de ${n2(h.cold.temp_min)} a ${n2(h.hot.temp_max)} °C</p>`,'Diferencia entre el extremo horario máximo y mínimo de todo el periodo cargado.');
  if(h.dia_max)o+=card('Día con más anomalías','Día '+h.dia_max.day,`<p>${fmt(h.dia_max.n)} celdas con |z| &gt; 2</p>`,`Es el día en que más celdas se apartaron de su comportamiento habitual dentro del periodo.`);
  const ds=Object.entries(h.por_dominio),ta=ds.reduce((a,[,x])=>a+x.anom,0);
  if(ta){const L=(h.por_dominio.Continental_Peru||{anom:0,total:0}),Oc=(h.por_dominio.Pacific_Ocean||{anom:0,total:0}),pc=x=>n2(100*x/ta)+' %',tr=x=>x.total?n2(100*x.anom/x.total)+' %':'—';
   o+=card('Anomalías: tierra vs océano',`${pc(L.anom)} / ${pc(Oc.anom)}`,`<p>tierra ${fmt(L.anom)} · océano ${fmt(Oc.anom)} (de ${fmt(ta)})<br>tasa interna: tierra ${tr(L)}, océano ${tr(Oc)} de sus celdas-día</p>`,`Las anomalías se concentran más en ${L.anom>=Oc.anom?'tierra':'el océano'} en número absoluto; la tasa interna corrige por el tamaño de cada dominio.`);
   const tc=h.calidas+h.frias;o+=card('Cálidas vs frías',`${fmt(h.calidas)} / ${fmt(h.frias)}`,`<p>${n2(100*h.calidas/tc)} % cálidas (z &gt; 2) · ${n2(100*h.frias/tc)} % frías (z &lt; −2)</p>`,h.calidas===h.frias?'Hay tantas anomalías cálidas como frías.':`Predominan las anomalías ${h.calidas>h.frias?'cálidas':'frías'} en el periodo cargado.`)}
  else o+=card('Anomalías','Sin anomalías','<p>Ejecuta el paso de anomalías.</p>','');
  if(h.precip)o+=card('Mayor precipitación horaria',n2(h.precip.max_precipitation)+' mm',`<p>día ${h.precip.day} · ${dn(h.precip.domain)}</p>`,'Máximo de una sola hora en una celda (regional_stats_etl.max_precipitation).');
  o+='</div>';
  if(h.top.length)o+=card('Top 5 anomalías por |z|','','<table><tr><th>día</th><th>lat</th><th>lon</th><th>dominio</th><th>T (°C)</th><th>base (°C)</th><th>z</th><th>tipo</th></tr>'+h.top.map(x=>`<tr><td>${x.day}</td><td>${x.latitude}</td><td>${x.longitude}</td><td>${esc(dn(x.domain))}</td><td>${n2(x.temp_mean)}</td><td>${n2(x.temp_base)}</td><td>${n2(x.z)}</td><td>${esc(x.tipo)}</td></tr>`).join('')+'</table>',
   `La mayor desviación (z = ${n2(h.top[0].z)}) ocurrió el día ${h.top[0].day} en ${dn(h.top[0].domain)}, en el ${zona(h,h.top[0].latitude)} del área.`);
  o+='<h2 style="margin:14px 0 10px">3. Rendimiento</h2><div class="hgrid">';
  o+=m?card('Ingesta',fmt(m.docs_por_segundo)+' docs/s',`<p>ingesta ${n2(m.segundos_ingesta)} s · índices ${n2(m.segundos_indices)} s · agregaciones ${n2(m.segundos_agregacion)} s · total ${n2(m.segundos_total)} s<br>colección ${n2(m.tamano_coleccion_MB)} MB · índices ${n2(m.tamano_indices_MB)} MB</p>`,`Fuente: ${esc(h.res_dir)}/metricas_ingesta.json.`)
   :card('Ingesta','Sin métricas',`<p>No existe ${esc(h.res_dir)}/metricas_ingesta.json.</p>`,'');
  o+=`<div class="card" id="hgeo"><h2>Consulta geoespacial: con vs sin índice</h2><button id="hgeob" class="noprint">Medir con/sin índice</button> <span id="hgeos" class="note"></span><div id="hgeor"></div></div>`;
  o+='</div><h2 style="margin:14px 0 10px">4. Validación</h2><div class="hgrid">';const GH=h.geo;
  if(v){o+=card('NumPy vs MongoDB',v.VALIDACION_OK?'Validación OK':'Con diferencias',`<p>${fmt(v.filas_comparadas)} filas dominio×día<br>máx. dif. temperatura ${v.max_dif_temp_C} °C · precipitación ${v.max_dif_precip_mm} mm<br>observaciones: ${fmt(v.observaciones_en_mongodb)} de ${fmt(v.observaciones_esperadas)} esperadas · muestras ${v.muestras_coinciden?'coinciden':'no coinciden'}</p>`,'NumPy lee el NetCDF directamente; Mongo usa el pipeline de agregación.');
   o+=v.hadoop_filas!=null?card('NumPy vs Hadoop',fmt(v.hadoop_filas)+' filas',`<p>máx. dif. temperatura ${v.hadoop_max_dif_temp_C} °C · precipitación ${v.hadoop_max_dif_precip_mm} mm</p>`,'MapReduce reproduce los agregados regionales con diferencias de redondeo.'):card('NumPy vs Hadoop','Sin datos','<p>No hay resultado de Hadoop en la validación.</p>','')}
  else o+=card('Validación','No ejecutada',`<p>No existe ${esc(h.res_dir)}/resultado_validacion.json. Ejecuta el paso de validación.</p>`,'');
  o+='</div><h2 style="margin:14px 0 10px">5. Limitaciones</h2>'+card('Alcance del análisis','',`<ul>
   <li>Línea base = los ${nd} días cargados${nd<31?' (demo; el mes completo tiene 31)':''}: z mide la desviación respecto al propio periodo, no a una climatología de varios años.</li>
   <li>Hadoop se ejecutó en modo local (un solo proceso), no en un clúster distribuido.</li>
   <li>MongoDB corre en un único nodo, sin réplicas ni sharding.</li>
   <li>Los hallazgos describen dónde y cuándo; no prueban causas físicas.</li></ul>`,'');
  $('#hal').innerHTML=o;$('#hgeob').onclick=medirGeo;if(GH)geoDraw(GH)}
 catch(e){$('#hal').innerHTML='<b style="color:var(--bad)">No se pudieron calcular los hallazgos de '+esc(d)+':</b> '+esc(e.message)}}
function geoDraw(g){if(!g){$('#hgeor').innerHTML='<p>Sin datos para medir.</p>';return}
 const a=g.con_indice,b=g.sin_indice,mx=Math.max(a.ms||0,b.ms||0,1),f=Math.max(1,(b.ms||0))/Math.max(1,(a.ms||0));
 $('#hgeos').textContent='último resultado (en memoria)';
 $('#hgeor').innerHTML=`<p>$geoWithin ${g.km} km alrededor de (${g.lat}, ${g.lon}), día ${esc(g.dia)} · ${fmt(a.n)} docs devueltos · maxTimeMS 60000</p><div class="hb">
  <span>con índice<br><small>${esc(a.stage)}</small></span><div><div class="b" style="width:${100*(a.ms||0)/mx}%"></div><small>${fmt(a.ms)} ms · ${fmt(a.docs)} docs examinados</small></div>
  <span>sin índice<br><small>${esc(b.stage)} ($natural)</small></span><div><div class="b s" style="width:${100*(b.ms||0)/mx}%"></div><small>${fmt(b.ms)} ms · ${fmt(b.docs)} docs examinados</small></div></div>
  <p class="hi">Sin índice se examinan ${fmt(b.docs)} documentos frente a ${fmt(a.docs)}; el tiempo es ${n2(f)}× ${f>=1?'mayor':'menor'}.</p>`}
async function medirGeo(){const bt=$('#hgeob');bt.disabled=true;$('#hgeos').textContent='midiendo…';
 try{geoDraw(await J('/api/hallazgos/geo?db='+encodeURIComponent(db())))}catch(e){$('#hgeos').textContent='';$('#hgeor').innerHTML='<b style="color:var(--bad)">Error:</b> '+esc(e.message)}finally{bt.disabled=false}}
$('#hreload').onclick=loadHal;$('#hprint').onclick=()=>window.print();
$('#db').addEventListener('change',()=>{if(!$('#v_hal').hidden)loadHal()});
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
