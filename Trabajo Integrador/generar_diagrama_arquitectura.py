"""
Generador del diagrama de Arquitectura Big Data y Pipeline ETL para LaTeX IEEE
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis('off')

# Paleta de colores profesionales IEEE
c_ingest = '#E3F2FD'
c_ingest_border = '#1976D2'
c_storage = '#E8F5E9'
c_storage_border = '#388E3C'
c_process = '#FFF3E0'
c_process_border = '#F57C00'
c_serve = '#F3E5F5'
c_serve_border = '#7B1FA2'

# Función auxiliar para cajas redondeadas
def draw_box(x, y, w, h, bg_col, border_col, title, subtitle="", items=None):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1.5",
                                  linewidth=1.8, edgecolor=border_col, facecolor=bg_col)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h - 5, title, fontsize=10, fontweight='bold', ha='center', va='top', color='#1A237E')
    if subtitle:
        ax.text(x + w/2, y + h - 11, subtitle, fontsize=8, fontstyle='italic', ha='center', va='top', color='#424242')
    if items:
        y_text = y + h - 17
        for it in items:
            ax.text(x + 3, y_text, f"• {it}", fontsize=7.5, ha='left', va='top', color='#212121')
            y_text -= 5.2

# 1. Capa de Fuentes e Ingesta
draw_box(2, 22, 20, 68, c_ingest, c_ingest_border, 
         "1. FUENTES E INGESTA", 
         "(Copernicus CDS / ERA5)",
         ["ERA5 Reanalysis", "era5_peru_202001.nc", "Lat: [0°, -19°]", "Lon: [-82°, -68°]", 
          "Resolución: 0.25° (31 km)", "Frecuencia: Horaria (744h)", "Formato binario NetCDF4", 
          "Variables instant./accum."])

# Flecha 1 -> 2
ax.annotate('', xy=(26, 56), xytext=(22.5, 56),
            arrowprops=dict(facecolor='#1976D2', edgecolor='#1976D2', width=2, headwidth=7))
ax.text(24.2, 59, "Lectura\nNetCDF", fontsize=7, ha='center', color='#0D47A1', fontweight='bold')

# 2. Capa de Transformación ETL
draw_box(26, 22, 21, 68, c_process, c_process_border,
         "2. PIPELINE ETL",
         "(Python & Ingestion Core)",
         ["Aplanamiento espaciotemporal", "Conversión física:", "  - Temp: K -> °C", 
          "  - Precip: m -> mm", "  - Viento: mag(u10, v10)", "  - Presión: Pa -> hPa",
          "Land-Sea Mask (lsm):", "  - Océano Pacífico", "  - Perú Continental",
          "GeoJSON Point formatting", "Batching (15,000 docs/lote)"])

# Flecha 2 -> 3
ax.annotate('', xy=(51, 56), xytext=(47.5, 56),
            arrowprops=dict(facecolor='#F57C00', edgecolor='#F57C00', width=2, headwidth=7))
ax.text(49.2, 59, "Bulk\nInsert", fontsize=7, ha='center', color='#E65100', fontweight='bold')

# 3. Capa de Almacenamiento NoSQL (MongoDB)
draw_box(51, 22, 23, 68, c_storage, c_storage_border,
         "3. ALMACENAMIENTO NoSQL",
         "(MongoDB 8.0 / Teorema CP)",
         ["BD: era5_climate_db", "Colecciones principales:", "  • climate_observations", 
          "  • daily_climatology_etl", "  • spatial_grid_catalog", "Indexación Avanzada:", 
          "  - 2dsphere geoespacial", "  - Compuesto: (time, lat, lon)", 
          "  - Secundario: temp, precip", "WiredTiger Engine (Snappy)", 
          "Escalabilidad por Sharding"])

# Flecha 3 -> 4
ax.annotate('', xy=(78, 56), xytext=(74.5, 56),
            arrowprops=dict(facecolor='#388E3C', edgecolor='#388E3C', width=2, headwidth=7))
ax.text(76.2, 59, "Aggr.\nPipeline", fontsize=7, ha='center', color='#1B5E20', fontweight='bold')

# 4. Capa de Procesamiento y Análisis
draw_box(78, 22, 20, 68, c_serve, c_serve_border,
         "4. ANÁLISIS Y SALIDA",
         "(MapReduce / Aggregation)",
         ["Aggregation Pipelines:", "  - $match: filtros espacio-temp.", 
          "  - $group: promedios diarios", "  - $project: redondeo y métricas",
          "  - $out: materialización", "Consultas analíticas:", 
          "  - Detección de anomalías", "  - Correlación océano-tierra",
          "MongoDB Compass GUI:", "  - Schema & Explain Plan"])

# Banner inferior: Teorema CAP y Modelo BASE/ACID
cap_box = patches.FancyBboxPatch((2, 3), 96, 15, boxstyle="round,pad=1",
                                linewidth=1.5, edgecolor='#455A64', facecolor='#ECEFF1')
ax.add_patch(cap_box)
ax.text(50, 14, "ENFOQUE ARQUITECTÓNICO: TEOREMA CAP (SISTEMA CP) & ESCALABILIDAD DISTRIBUIDA", 
        fontsize=9, fontweight='bold', ha='center', color='#263238')
cap_text = (
    "• Consistencia (C): Prioridad en replicación primaria (Raft consensus) para garantizar lecturas deterministas en modelado climático.\n"
    "• Tolerancia a Particiones (P): La fragmentación de red aísla nodos minoritarios evitando 'split-brain' mediante elecciones automáticas.\n"
    "• Sintonía BASE vs ACID: Ingesta masiva optimizada mediante escrituras desordenadas (w:1) y consistencia linealizable en agregaciones."
)
ax.text(5, 10.5, cap_text, fontsize=7.2, ha='left', va='top', color='#37474F')

plt.tight_layout()
output_path = r"c:\UCSM\Semestre 10\Big Data\Trabajo Integrador\latex\img\arquitectura_bigdata_cap.png"
plt.savefig(output_path, bbox_inches='tight', dpi=300)
plt.close()
print(f"Diagrama de arquitectura generado exitosamente en: {output_path}")
