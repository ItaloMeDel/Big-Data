"""
Ingesta y Transformación ETL de ERA5 a MongoDB
Fase 2 - Proyecto Integrador Big Data UCSM
"""
import time
import datetime
import netCDF4
import numpy as np
import pymongo
from pymongo import MongoClient, ASCENDING, GEOSPHERE

def run_ingestion():
    print("=== INICIANDO PIPELINE ETL DE INGESTA ERA5 A MONGODB ===")
    t_start = time.time()
    
    # Conexión al servidor local de MongoDB
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    db = client["era5_climate_db"]
    
    # Limpiar colecciones anteriores para garantizar reproducibilidad
    db["climate_observations"].drop()
    db["daily_climatology_etl"].drop()
    db["regional_stats_etl"].drop()
    db["spatial_grid_catalog"].drop()
    print("Colecciones previas reiniciadas.")
    
    # Cargar datasets NetCDF
    print("Cargando datasets NetCDF...")
    nc_inst = netCDF4.Dataset("era5_data/data_stream-oper_stepType-instant.nc")
    nc_accum = netCDF4.Dataset("era5_data/data_stream-oper_stepType-accum.nc")
    
    lats = nc_inst.variables["latitude"][:]
    lons = nc_inst.variables["longitude"][:]
    times = nc_inst.variables["valid_time"][:]
    lsm = nc_inst.variables["lsm"][0, :, :] # Máscara tierra/mar (77, 57)
    
    n_lats = len(lats)
    n_lons = len(lons)
    total_grid_points = n_lats * n_lons
    print(f"Grilla espacial: {n_lats} latitudes x {n_lons} longitudes = {total_grid_points} puntos celdas.")
    
    # 1. Poblar catálogo espacial
    print("Poblando catálogo espacial (spatial_grid_catalog)...")
    grid_docs = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            is_land = bool(lsm[i, j] > 0.5)
            domain = "Continental_Peru" if is_land else "Pacific_Ocean"
            grid_docs.append({
                "_id": f"gp_{float(lat):.2f}_{float(lon):.2f}",
                "location": {
                    "type": "Point",
                    "coordinates": [round(float(lon), 2), round(float(lat), 2)]
                },
                "lat": round(float(lat), 2),
                "lon": round(float(lon), 2),
                "is_land": is_land,
                "land_sea_ratio": round(float(lsm[i, j]), 4),
                "domain": domain
            })
    db["spatial_grid_catalog"].insert_many(grid_docs)
    db["spatial_grid_catalog"].create_index([("location", GEOSPHERE)])
    print(f"Catálogo espacial creado con {len(grid_docs)} celdas.")
    
    # 2. Ingesta por lotes de observaciones climáticas
    # Seleccionamos las primeras 72 horas (3 días completos: Ene 1, 2, 3 de 2020)
    # 72 x 4,389 = 316,008 documentos masivos de observación
    NUM_HOURS = 72
    print(f"Extrayendo y transformando {NUM_HOURS} horas temporales de observaciones...")
    
    # Lectura en memoria de las matrices requeridas
    t2m_arr = nc_inst.variables["t2m"][:NUM_HOURS] # (NUM_HOURS, 77, 57)
    u10_arr = nc_inst.variables["u10"][:NUM_HOURS]
    v10_arr = nc_inst.variables["v10"][:NUM_HOURS]
    skt_arr = nc_inst.variables["skt"][:NUM_HOURS]
    msl_arr = nc_inst.variables["msl"][:NUM_HOURS]
    sp_arr = nc_inst.variables["sp"][:NUM_HOURS]
    cape_arr = nc_inst.variables["cape"][:NUM_HOURS]
    tp_arr = nc_accum.variables["tp"][:NUM_HOURS]
    
    batch = []
    total_inserted = 0
    BATCH_SIZE = 15000
    
    for t_idx in range(NUM_HOURS):
        epoch_sec = int(times[t_idx])
        dt = datetime.datetime.fromtimestamp(epoch_sec, tz=datetime.timezone.utc)
        iso_str = dt.isoformat()
        day = dt.day
        hour = dt.hour
        
        for i, lat in enumerate(lats):
            lat_f = round(float(lat), 2)
            for j, lon in enumerate(lons):
                lon_f = round(float(lon), 2)
                
                # Conversión física
                t2m_k = float(t2m_arr[t_idx, i, j])
                t2m_c = round(t2m_k - 273.15, 2)
                
                skt_k = float(skt_arr[t_idx, i, j])
                skt_c = round(skt_k - 273.15, 2)
                
                u10 = round(float(u10_arr[t_idx, i, j]), 2)
                v10 = round(float(v10_arr[t_idx, i, j]), 2)
                wind_speed = round(float(np.sqrt(u10**2 + v10**2)), 2)
                
                msl_hpa = round(float(msl_arr[t_idx, i, j]) / 100.0, 2)
                sp_hpa = round(float(sp_arr[t_idx, i, j]) / 100.0, 2)
                
                tp_val = float(tp_arr[t_idx, i, j])
                tp_mm = round(max(0.0, tp_val * 1000.0), 3)
                
                cape_val = round(float(cape_arr[t_idx, i, j]), 1)
                is_land = bool(lsm[i, j] > 0.5)
                domain = "Continental_Peru" if is_land else "Pacific_Ocean"
                
                doc = {
                    "timestamp": dt,
                    "hour": hour,
                    "day": day,
                    "month": 1,
                    "year": 2020,
                    "location": {
                        "type": "Point",
                        "coordinates": [lon_f, lat_f] # GeoJSON standard [lon, lat]
                    },
                    "geo": {
                        "latitude": lat_f,
                        "longitude": lon_f,
                        "is_land": is_land,
                        "domain": domain
                    },
                    "measurements": {
                        "temperature_c": t2m_c,
                        "skin_temp_c": skt_c,
                        "wind_u10": u10,
                        "wind_v10": v10,
                        "wind_speed_ms": wind_speed,
                        "pressure_msl_hpa": msl_hpa,
                        "surface_pressure_hpa": sp_hpa,
                        "precipitation_mm": tp_mm,
                        "cape": cape_val
                    },
                    "derived": {
                        "is_extreme_precip": bool(tp_mm > 5.0),
                        "heat_index_proxy": round(t2m_c + 0.1 * cape_val / 100.0, 2)
                    }
                }
                batch.append(doc)
                
                if len(batch) >= BATCH_SIZE:
                    db["climate_observations"].insert_many(batch, ordered=False)
                    total_inserted += len(batch)
                    print(f"  Ingestados {total_inserted} registros...")
                    batch = []
                    
    if batch:
        db["climate_observations"].insert_many(batch, ordered=False)
        total_inserted += len(batch)
        print(f"  Ingestados {total_inserted} registros totales.")
        
    print(f"Creando índices optimizados en 'climate_observations'...")
    # Índice geoespacial 2dsphere
    db["climate_observations"].create_index([("location", GEOSPHERE)], name="idx_geo_2dsphere")
    # Índice compuesto espaciotemporal
    db["climate_observations"].create_index([
        ("timestamp", ASCENDING),
        ("geo.latitude", ASCENDING),
        ("geo.longitude", ASCENDING)
    ], name="idx_timestamp_lat_lon")
    # Índices analíticos para consultas térmicas y de precipitación
    db["climate_observations"].create_index([("measurements.temperature_c", ASCENDING)], name="idx_temp_c")
    db["climate_observations"].create_index([("measurements.precipitation_mm", ASCENDING)], name="idx_precip_mm")
    db["climate_observations"].create_index([("geo.domain", ASCENDING)], name="idx_domain")
    print("Índices creados exitosamente.")
    
    # 3. Ejecutar Pipeline de Agregación ETL (MapReduce Style)
    print("Ejecutando Pipeline de Agregación ETL: Calculando climatología diaria por celda...")
    pipeline_daily = [
        {
            "$group": {
                "_id": {
                    "day": "$day",
                    "lat": "$geo.latitude",
                    "lon": "$geo.longitude",
                    "domain": "$geo.domain"
                },
                "temp_mean": { "$avg": "$measurements.temperature_c" },
                "temp_max": { "$max": "$measurements.temperature_c" },
                "temp_min": { "$min": "$measurements.temperature_c" },
                "precip_total": { "$sum": "$measurements.precipitation_mm" },
                "wind_max": { "$max": "$measurements.wind_speed_ms" },
                "cape_mean": { "$avg": "$measurements.cape" },
                "readings_count": { "$sum": 1 }
            }
        },
        {
            "$project": {
                "_id": 0,
                "day": "$_id.day",
                "location": {
                    "type": "Point",
                    "coordinates": ["$_id.lon", "$_id.lat"]
                },
                "latitude": "$_id.lat",
                "longitude": "$_id.lon",
                "domain": "$_id.domain",
                "temp_mean": { "$round": ["$temp_mean", 2] },
                "temp_max": { "$round": ["$temp_max", 2] },
                "temp_min": { "$round": ["$temp_min", 2] },
                "precip_total_mm": { "$round": ["$precip_total", 3] },
                "wind_max_ms": { "$round": ["$wind_max", 2] },
                "cape_mean": { "$round": ["$cape_mean", 1] },
                "readings_count": 1
            }
        },
        {
            "$out": "daily_climatology_etl"
        }
    ]
    db["climate_observations"].aggregate(pipeline_daily)
    print("Colección 'daily_climatology_etl' generada exitosamente.")
    
    # 4. Pipeline de Agregación Regional (Comparativa Costa/Mar vs Tierra)
    print("Ejecutando Agregación Regional (regional_stats_etl)...")
    pipeline_regional = [
        {
            "$group": {
                "_id": {
                    "domain": "$geo.domain",
                    "day": "$day"
                },
                "avg_temperature": { "$avg": "$measurements.temperature_c" },
                "max_precipitation": { "$max": "$measurements.precipitation_mm" },
                "total_precipitation": { "$sum": "$measurements.precipitation_mm" },
                "avg_wind_speed": { "$avg": "$measurements.wind_speed_ms" },
                "total_samples": { "$sum": 1 }
            }
        },
        {
            "$project": {
                "_id": 0,
                "domain": "$_id.domain",
                "day": "$_id.day",
                "avg_temperature": { "$round": ["$avg_temperature", 2] },
                "max_precipitation": { "$round": ["$max_precipitation", 3] },
                "total_precipitation_volume": { "$round": ["$total_precipitation", 2] },
                "avg_wind_speed": { "$round": ["$avg_wind_speed", 2] },
                "total_samples": 1
            }
        },
        {
            "$out": "regional_stats_etl"
        }
    ]
    db["climate_observations"].aggregate(pipeline_regional)
    print("Colección 'regional_stats_etl' generada exitosamente.")
    
    # Estadísticas finales
    elapsed = time.time() - t_start
    print("=== RESUMEN DE INGESTA Y PROCESAMIENTO ===")
    print(f"Total observaciones ingresadas: {db['climate_observations'].count_documents({})}")
    print(f"Total registros diarios agregados: {db['daily_climatology_etl'].count_documents({})}")
    print(f"Total celdas espaciales catalogadas: {db['spatial_grid_catalog'].count_documents({})}")
    print(f"Tiempo total de ejecución: {elapsed:.2f} segundos.")
    print("=== PIPELINE COMPLETADO EXITOSAMENTE ===")

if __name__ == "__main__":
    run_ingestion()
