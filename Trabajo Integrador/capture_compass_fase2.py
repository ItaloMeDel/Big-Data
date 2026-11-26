"""
Captura automatizada de MongoDB Compass para la Fase 2 del Trabajo Integrador
Utiliza Playwright sobre el protocolo Chrome DevTools (CDP) de MongoDB Compass.
"""
import os
import subprocess
import time
from playwright.sync_api import sync_playwright

COMPASS_EXE = r"C:\UCSM\Semestre 10\Big Data\compass_dist\MongoDBCompass.exe"
OUTPUT_DIR = r"c:\UCSM\Semestre 10\Big Data\Trabajo Integrador\latex\img"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Iniciando MongoDB Compass con puerto de depuración CDP 9222...")
# Matar cualquier proceso previo de Compass si estuviera colgado
subprocess.run(["taskkill", "/F", "/IM", "MongoDBCompass.exe"], capture_output=True)
time.sleep(1)

proc = subprocess.Popen([
    COMPASS_EXE,
    "--ignoreAdditionalCommandLineFlags",
    "--remote-debugging-port=9222",
    "mongodb://localhost:27017"
])
print("Esperando 10 segundos a que inicialice MongoDB Compass...")
time.sleep(10)

try:
    with sync_playwright() as p:
        print("Conectando Playwright vía CDP...")
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0]
        page.set_viewport_size({"width": 1400, "height": 900})
        time.sleep(3)
        
        # 1. Captura de vista de Base de Datos y Colecciones
        try:
            print("Capturando Base de Datos era5_climate_db...")
            # Click en era5_climate_db en la barra lateral o en la lista
            db_elem = page.locator('text=era5_climate_db').first
            if db_elem.is_visible():
                db_elem.click()
                time.sleep(3)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_01_db_overview.png"))
            print("Guardado: compass_01_db_overview.png")
        except Exception as e:
            print("Error en captura 1:", e)
            
        # 2. Captura de Documentos de climate_observations
        try:
            print("Capturando vista de Documentos (climate_observations)...")
            coll_elem = page.locator('text=climate_observations').first
            if coll_elem.is_visible():
                coll_elem.click()
                time.sleep(3)
            # Expandir el primer documento si es posible
            page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_02_documents_model.png"))
            print("Guardado: compass_02_documents_model.png")
        except Exception as e:
            print("Error en captura 2:", e)
            
        # 3. Captura de la pestaña Schema (Distribución de datos)
        try:
            print("Capturando pestaña Schema (Distribución de datos)...")
            schema_tab = page.locator('button[role="tab"]:has-text("Schema")').first
            if schema_tab.is_visible():
                schema_tab.click()
                time.sleep(2)
                # Hacer clic en "Analyze Schema" si aparece
                analyze_btn = page.locator('button:has-text("Analyze"), button:has-text("Analyze Schema")').first
                if analyze_btn.is_visible():
                    analyze_btn.click()
                    print("Analizando esquema (esperando 6s)...")
                    time.sleep(6)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_03_schema_distribution.png"))
            print("Guardado: compass_03_schema_distribution.png")
        except Exception as e:
            print("Error en captura 3:", e)
            
        # 4. Captura de la pestaña Indexes (Estrategias de indexación)
        try:
            print("Capturando pestaña Indexes...")
            indexes_tab = page.locator('button[role="tab"]:has-text("Indexes")').first
            if indexes_tab.is_visible():
                indexes_tab.click()
                time.sleep(2)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_04_indexes.png"))
            print("Guardado: compass_04_indexes.png")
        except Exception as e:
            print("Error en captura 4:", e)
            
        # 5. Captura de la pestaña Aggregations (Pipeline MapReduce / ETL)
        try:
            print("Capturando pestaña Aggregations...")
            aggr_tab = page.locator('button[role="tab"]:has-text("Aggregations")').first
            if aggr_tab.is_visible():
                aggr_tab.click()
                time.sleep(2)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_05_aggregations.png"))
            print("Guardado: compass_05_aggregations.png")
        except Exception as e:
            print("Error en captura 5:", e)

        # 6. Captura de la pestaña Explain Plan (Rendimiento de consultas)
        try:
            print("Capturando pestaña Explain Plan...")
            explain_tab = page.locator('button[role="tab"]:has-text("Explain Plan")').first
            if explain_tab.is_visible():
                explain_tab.click()
                time.sleep(2)
                # Ejecutar explain si hay botón
                exp_btn = page.locator('button:has-text("Execute Explain")').first
                if exp_btn.is_visible():
                    exp_btn.click()
                    time.sleep(2)
            page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_06_explain_plan.png"))
            print("Guardado: compass_06_explain_plan.png")
        except Exception as e:
            print("Error en captura 6:", e)

        print("=== TODAS LAS CAPTURAS COMPLETADAS CON ÉXITO ===")

except Exception as err:
    print("Error global con Playwright:", err)

