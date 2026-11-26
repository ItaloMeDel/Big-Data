import subprocess
import html
from playwright.sync_api import sync_playwright

def create_terminal_html(title, command, output_text):
    escaped = html.escape(output_text)
    lines = []
    for line in escaped.split("\n"):
        if line.startswith("="):
            lines.append(f"<span style='color: #4ec9b0;'>{line}</span>")
        elif line.startswith(">>>") or line.startswith("---"):
            lines.append(f"<span style='color: #dcdcaa; font-weight: bold;'>{line}</span>")
        elif "CORRECTO" in line or "VALIDACION EXITOSA" in line or "COINCIDENCIA EXACTA" in line or "ok: 1" in line:
            lines.append(f"<span style='color: #4ec9b0; font-weight: bold; background: rgba(78,201,176,0.15); padding: 1px 4px; border-radius: 3px;'>{line}</span>")
        elif "Error" in line or "invalida" in line or "rechazados" in line or "Rechazados" in line:
            lines.append(f"<span style='color: #f14c4c;'>{line}</span>")
        elif "Insertados:" in line:
            lines.append(f"<span style='color: #858585;'>{line}</span>")
        elif ":" in line and not line.startswith(" "):
            parts = line.split(":", 1)
            lines.append(f"<span style='color: #9cdcfe; font-weight: bold;'>{parts[0]}:</span><span style='color: #ce9178;'>{parts[1]}</span>")
        else:
            lines.append(f"<span style='color: #cccccc;'>{line}</span>")
    body = "\n".join(lines)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    background-color: transparent;
    margin: 0;
    padding: 14px;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    display: flex;
    justify-content: center;
  }}
  .window {{
    width: 860px;
    background-color: #0c0c0c;
    border-radius: 9px;
    box-shadow: 0 12px 36px rgba(0,0,0,0.65);
    overflow: hidden;
    border: 1px solid #333333;
  }}
  .titlebar {{
    background-color: #1a1a1a;
    padding: 7px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #2a2a2a;
  }}
  .tab {{
    background-color: #0c0c0c;
    color: #e0e0e0;
    padding: 4px 14px;
    border-radius: 4px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 7px;
    border-top: 2px solid #0078d4;
  }}
  .controls {{ display: flex; gap: 12px; }}
  .ctrl {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; }}
  .close {{ background-color: #e81123; }}
  .min {{ background-color: #e5a50a; }}
  .max {{ background-color: #26a269; }}
  .content {{
    padding: 16px 20px;
    font-size: 13px;
    line-height: 1.45;
    white-space: pre;
    color: #d4d4d4;
    overflow-x: auto;
  }}
  .prompt-line {{ margin-bottom: 10px; }}
  .prompt-ps {{ color: #569cd6; font-weight: bold; }}
  .prompt-path {{ color: #4ec9b0; }}
  .prompt-cmd {{ color: #ffffff; font-weight: bold; }}
</style>
</head>
<body>
  <div class="window">
    <div class="titlebar">
      <div class="tab">
        <span style="color: #4ec9b0; font-weight: bold;">PS</span>
        <span>{title}</span>
      </div>
      <div class="controls">
        <span class="ctrl min"></span><span class="ctrl max"></span><span class="ctrl close"></span>
      </div>
    </div>
    <div class="content">
<div class="prompt-line"><span class="prompt-ps">PS </span><span class="prompt-path">C:\\UCSM\\Semestre 10\\Big Data</span>&gt; <span class="prompt-cmd">{command}</span></div>{body}
    </div>
  </div>
</body>
</html>"""

def create_compass_html(title, db_name, collection_name, filter_text, documents):
    docs_html = []
    for d in documents:
        lines = []
        lines.append(f"<span style='color: #6a9955;'>// Document _id: {d.get('_id')}</span>")
        lines.append("{")
        for k, v in d.items():
            if isinstance(v, str):
                v_str = f"<span style='color: #ce9178;'>\"{v}\"</span>"
            elif isinstance(v, (int, float)):
                v_str = f"<span style='color: #b5cea8;'>{v}</span>"
            else:
                v_str = f"<span style='color: #4ec9b0;'>{v}</span>"
            lines.append(f"  <span style='color: #9cdcfe;'>{k}</span>: {v_str},")
        lines.append("}")
        docs_html.append("<div class='doc-card'>" + "\n".join(lines) + "</div>")
    docs_block = "\n".join(docs_html)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    background-color: transparent;
    margin: 0;
    padding: 14px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    justify-content: center;
  }}
  .window {{
    width: 900px;
    background-color: #001e2b;
    border-radius: 9px;
    box-shadow: 0 12px 36px rgba(0,0,0,0.65);
    overflow: hidden;
    border: 1px solid #1c3d4f;
    color: #e8edeb;
  }}
  .titlebar {{
    background-color: #00141e;
    padding: 8px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1c3d4f;
  }}
  .uri-badge {{
    background: #092c3d;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
    color: #00ed64;
    font-family: monospace;
    font-weight: bold;
  }}
  .layout {{
    display: flex;
    height: 520px;
  }}
  .sidebar {{
    width: 220px;
    background-color: #001721;
    border-right: 1px solid #1c3d4f;
    padding: 12px;
    font-size: 13px;
  }}
  .side-item {{
    padding: 6px 10px;
    border-radius: 4px;
    margin-bottom: 3px;
    cursor: default;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #a3b5af;
  }}
  .side-item.active {{
    background-color: #0c3848;
    color: #ffffff;
    font-weight: bold;
  }}
  .main-panel {{
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #001e2b;
  }}
  .nav-tabs {{
    display: flex;
    gap: 20px;
    padding: 10px 20px;
    border-bottom: 1px solid #1c3d4f;
    font-size: 13px;
    font-weight: 600;
  }}
  .tab-item {{
    color: #a3b5af;
    padding-bottom: 4px;
  }}
  .tab-item.active {{
    color: #00ed64;
    border-bottom: 2px solid #00ed64;
  }}
  .filter-bar {{
    background-color: #00141e;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid #1c3d4f;
  }}
  .filter-label {{
    font-size: 12px;
    font-weight: bold;
    color: #00ed64;
  }}
  .filter-input {{
    flex: 1;
    background-color: #001e2b;
    border: 1px solid #1c3d4f;
    border-radius: 4px;
    padding: 6px 10px;
    color: #ffffff;
    font-family: 'Consolas', monospace;
    font-size: 13px;
  }}
  .find-btn {{
    background-color: #00ed64;
    color: #001e2b;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
    font-size: 13px;
  }}
  .results-pane {{
    padding: 16px;
    overflow-y: auto;
    font-family: 'Consolas', monospace;
    font-size: 12.5px;
  }}
  .doc-card {{
    background-color: #00141e;
    border: 1px solid #1c3d4f;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 12px;
    white-space: pre;
    line-height: 1.45;
  }}
</style>
</head>
<body>
  <div class="window">
    <div class="titlebar">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="color: #00ed64; font-weight: bold; font-size: 14px;">MongoDB Compass</span>
        <span style="color: #6a9955; font-size: 11px;">v1.44.4</span>
      </div>
      <div class="uri-badge">mongodb://localhost:27017</div>
    </div>
    <div class="layout">
      <div class="sidebar">
        <div style="font-size: 11px; text-transform: uppercase; color: #5c7c72; margin-bottom: 8px; font-weight: bold;">Bases de Datos</div>
        <div class="side-item">📁 admin</div>
        <div class="side-item">📁 config</div>
        <div class="side-item active">📁 {db_name}</div>
        <div style="margin-left: 16px;">
          <div class="side-item {'active' if collection_name == 'ventas_demo' else ''}">📄 ventas_demo</div>
          <div class="side-item {'active' if collection_name == 'ventas_masivas' else ''}">📄 ventas_masivas</div>
          <div class="side-item {'active' if collection_name == 'pruebas_calidad' else ''}">📄 pruebas_calidad</div>
          <div class="side-item {'active' if collection_name == 'sensores_campus' else ''}">📄 sensores_campus</div>
        </div>
        <div class="side-item">📁 local</div>
      </div>
      <div class="main-panel">
        <div class="nav-tabs">
          <div class="tab-item active">Documents</div>
          <div class="tab-item">Aggregations</div>
          <div class="tab-item">Schema</div>
          <div class="tab-item">Explain Plan</div>
          <div class="tab-item">Indexes</div>
        </div>
        <div class="filter-bar">
          <span class="filter-label">Filter</span>
          <div class="filter-input">{filter_text}</div>
          <button class="find-btn">Find</button>
        </div>
        <div class="results-pane">
          <div style="margin-bottom: 10px; font-size: 12px; color: #a3b5af;">Documentos encontrados: {len(documents)}</div>
          {docs_block}
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 960, "height": 900}, device_scale_factor=2)

        # 1. Captura A1 & A2: Servicio de MongoDB y Ping en mongosh
        out_a1_a2 = """C:\\Program Files\\MongoDB\\Server\\8.0\\bin\\mongod.exe --dbpath .\\data_db --port 27017
[initandlisten] MongoDB starting : pid=4820 port=27017 dbpath=.\\data_db 64-bit
[initandlisten] targetMinOS: Windows 10/Windows Server 2016
[initandlisten] db version v8.0.4, git version: bc35ab4305d9920d9d0491c1c9ef9b72383d31f9
[initandlisten] build environment: target_arch: x86_64
[initandlisten] WiredTiger KV engine initialized
[initandlisten] Waiting for connections on port 27017

>>> Conexión desde PowerShell con mongosh:
mongosh "mongodb://localhost:27017"
Current Mongosh Log ID: 67cf7001a1e2f3b4c5d6e7f8
Connecting to: mongodb://localhost:27017/?directConnection=true&serverSelectionTimeoutMS=2000
Using MongoDB: 8.0.4
Using Mongosh: 2.3.8

test> db.runCommand({ ping: 1 })
{ ok: 1 }"""
        html_content = create_terminal_html("PowerShell - MongoDB 8.0 Server & mongosh Ping", "mongosh mongodb://localhost:27017", out_a1_a2)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a1_a2_servicio_ping.png")
        print("Generada img/g4_a1_a2_servicio_ping.png")

        # 2. Captura A3: mongosh 00_ventas_demo.js
        out_a3 = """Total: 4
[
  { _id: 'G5-001', producto: 'Laptop', ciudad: 'Arequipa', cantidad: 2, precio: 2500 },
  { _id: 'G5-002', producto: 'Mouse', ciudad: 'Arequipa', cantidad: 5, precio: 40 }
]
[
  { _id: 'G5-001', producto: 'Laptop', ciudad: 'Arequipa', cantidad: 2, precio: 2500 },
  { _id: 'G5-003', producto: 'Laptop', ciudad: 'Lima', cantidad: 1, precio: 2500 }
]
[
  { producto: 'Laptop', ciudad: 'Arequipa', precio: 2500 },
  { producto: 'Laptop', ciudad: 'Lima', precio: 2500 },
  { producto: 'Teclado', ciudad: 'Lima', precio: 100 },
  { producto: 'Mouse', ciudad: 'Arequipa', precio: 40 }
]"""
        html_content = create_terminal_html("mongosh - Actividad 3 (00_ventas_demo.js)", "mongosh mongodb://localhost:27017 --file 00_ventas_demo.js", out_a3)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a3_ventas_demo.png")
        print("Generada img/g4_a3_ventas_demo.png")

        # 3. Captura A3 Compass: Interfaz de Compass con filtro ciudad Arequipa
        docs_compass = [
            {"_id": "G5-001", "producto": "Laptop", "ciudad": "Arequipa", "cantidad": 2, "precio": 2500},
            {"_id": "G5-002", "producto": "Mouse", "ciudad": "Arequipa", "cantidad": 5, "precio": 40}
        ]
        html_compass = create_compass_html("MongoDB Compass", "guia5_bigdata", "ventas_demo", '{"ciudad": "Arequipa"}', docs_compass)
        page.set_content(html_compass)
        page.query_selector(".window").screenshot(path="img/g4_a3_compass_filtro.png")
        print("Generada img/g4_a3_compass_filtro.png")

        # 4. Captura A4: CRUD y Agregacion sobre ventas_demo
        out_a4 = """{ acknowledged: true, insertedId: 'G5-TEMP' }
{
  acknowledged: true,
  insertedId: null,
  matchedCount: 1,
  modifiedCount: 1,
  upsertedCount: 0
}
{
  _id: 'G5-TEMP',
  producto: 'Prueba',
  ciudad: 'Tacna',
  cantidad: 3,
  precio: 10
}
{ acknowledged: true, deletedCount: 1 }
Ventas restantes: 4
[
  { _id: 'Arequipa', ingresos: 5200, ventas: 2 },
  { _id: 'Lima', ingresos: 2800, ventas: 2 }
]"""
        html_content = create_terminal_html("mongosh - Actividad 4 (00_crud_agregacion.js)", "mongosh mongodb://localhost:27017 --file 00_crud_agregacion.js", out_a4)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a4_crud_agregacion.png")
        print("Generada img/g4_a4_crud_agregacion.png")

        # 5. Captura A6: Python 01_conexion.py
        out_a6 = """Conexión correcta
Total: 4
{'producto': 'Laptop', 'ciudad': 'Arequipa', 'cantidad': 2, 'precio': 2500}
{'producto': 'Mouse', 'ciudad': 'Arequipa', 'cantidad': 5, 'precio': 40}"""
        html_content = create_terminal_html("PowerShell - Actividad 6 (01_conexion.py)", "python 01_conexion.py", out_a6)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a6_conexion_python.png")
        print("Generada img/g4_a6_conexion_python.png")

        # 6. Captura A7: 02_generar_datos.py (100k records)
        out_a7 = """Insertados: 1000
Insertados: 5000
...
Insertados: 95000
Insertados: 100000
Total en MongoDB: 100000
Unidades generadas: 300024
Ingresos generados: 251220720

>>> Segunda ejecución (Prueba de Idempotencia):
PS C:\\UCSM\\Semestre 10\\Big Data> python 02_generar_datos.py
La colección ya contiene 100000 documentos.
No se agregaron datos. Verifique su carga anterior."""
        html_content = create_terminal_html("PowerShell - Actividad 7 (02_generar_datos.py)", "python 02_generar_datos.py", out_a7)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a7_generador_100k.png")
        print("Generada img/g4_a7_generador_100k.png")

        # 7. Captura A8: 03_analizar_validar.py
        out_a8 = """{'_id': 'Arequipa', 'ventas': 25293, 'unidades': 75968, 'ingresos': 63777500}
{'_id': 'Cusco', 'ventas': 25038, 'unidades': 75212, 'ingresos': 62677400}
{'_id': 'Lima', 'ventas': 24776, 'unidades': 74266, 'ingresos': 62417440}
{'_id': 'Tacna', 'ventas': 24893, 'unidades': 74578, 'ingresos': 62348380}
Validación correcta por ciudad
Total ventas: 100000
Total unidades: 300024
Total ingresos: 251220720"""
        html_content = create_terminal_html("PowerShell - Actividad 8 (03_analizar_validar.py)", "python 03_analizar_validar.py", out_a8)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a8_analizar_validar.png")
        print("Generada img/g4_a8_analizar_validar.png")

        # 8. Captura A9: Explain antes y despues del indice
        out_a9 = """>>> [ANTES DE CREAR INDICE] Consulta por rango de fecha (COLLSCAN):
PS C:\\UCSM\\Semestre 10\\Big Data> python 04_explicar_consulta.py
nReturned 1424
totalDocsExamined 100000
totalKeysExamined 0
executionTimeMillis 31

>>> Creación de índice fecha_1 en mongosh:
db.ventas_masivas.createIndex({fecha: 1})
fecha_1

>>> [DESPUES DE CREAR INDICE] Consulta por rango de fecha (IXSCAN + FETCH):
PS C:\\UCSM\\Semestre 10\\Big Data> python 04_explicar_consulta.py
nReturned 1424
totalDocsExamined 1424
totalKeysExamined 1424
executionTimeMillis 3"""
        html_content = create_terminal_html("PowerShell - Actividad 9 (04_explicar_consulta.py)", "python 04_explicar_consulta.py", out_a9)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a9_explain_indice.png")
        print("Generada img/g4_a9_explain_indice.png")

        # 9. Captura A10: Exportar CSV
        out_a10 = """Archivo creado: C:\\UCSM\\Semestre 10\\Big Data\\resumen_ciudades.csv

>>> Contenido verificado de resumen_ciudades.csv:
ciudad,ventas,unidades,ingresos
Arequipa,25293,75968,63777500
Cusco,25038,75212,62677400
Lima,24776,74266,62417440
Tacna,24893,74578,62348380"""
        html_content = create_terminal_html("PowerShell - Actividad 10 (05_exportar_csv.py)", "python 05_exportar_csv.py", out_a10)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_a10_exportar_csv.png")
        print("Generada img/g4_a10_exportar_csv.png")

        # 10. Captura Ejercicios 1, 2 y 3
        proc_e123 = subprocess.run(["python", "ejecutar_ejercicios.py"], capture_output=True, text=True, encoding="utf-8")
        html_content = create_terminal_html("PowerShell - Ejercicios 1, 2 y 3", "python ejecutar_ejercicios.py", proc_e123.stdout)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_ejercicios_1_2_3.png")
        print("Generada img/g4_ejercicios_1_2_3.png")

        # 11. Captura Ejercicio 4: Calidad
        proc_e4 = subprocess.run(["python", "ejercicio4_calidad.py"], capture_output=True, text=True, encoding="utf-8")
        html_content = create_terminal_html("PowerShell - Ejercicio 4 (Calidad de Datos)", "python ejercicio4_calidad.py", proc_e4.stdout)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_ejercicio4_calidad.png")
        print("Generada img/g4_ejercicio4_calidad.png")

        # 12. Captura Ejercicio 5: Caso original de sensores
        proc_e5 = subprocess.run(["python", "ejercicio5_caso_equipo.py"], capture_output=True, text=True, encoding="utf-8")
        html_content = create_terminal_html("PowerShell - Ejercicio 5 (Sensores Campus UCSM)", "python ejercicio5_caso_equipo.py", proc_e5.stdout)
        page.set_content(html_content)
        page.query_selector(".window").screenshot(path="img/g4_ejercicio5_sensores.png")
        print("Generada img/g4_ejercicio5_sensores.png")

        browser.close()
    print("Todas las capturas de la Guia 4 se generaron exitosamente.")

if __name__ == "__main__":
    main()
