"""
Refinamiento de capturas de MongoDB Compass para mostrar vistas enriquecidas
"""
import os
import subprocess
import time
from playwright.sync_api import sync_playwright

COMPASS_EXE = r"C:\UCSM\Semestre 10\Big Data\compass_dist\MongoDBCompass.exe"
OUTPUT_DIR = r"c:\UCSM\Semestre 10\Big Data\Trabajo Integrador\latex\img"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Iniciando captura avanzada de Compass...")
subprocess.run(["taskkill", "/F", "/IM", "MongoDBCompass.exe"], capture_output=True)
time.sleep(1)

proc = subprocess.Popen([
    COMPASS_EXE,
    "--ignoreAdditionalCommandLineFlags",
    "--remote-debugging-port=9222",
    "mongodb://localhost:27017"
])
time.sleep(8)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.pages[0]
    page.set_viewport_size({"width": 1400, "height": 900})
    time.sleep(2)
    
    # 1. Base de datos era5_climate_db
    try:
        page.locator('text=era5_climate_db').first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_01_db_overview.png"))
        print("1. Guardado compass_01_db_overview.png")
    except Exception as e:
        print("Error en 1:", e)
        
    # 2. Documentos de climate_observations
    try:
        page.locator('text=climate_observations').first.click()
        time.sleep(3)
        # Expandir los primeros dos documentos si tienen boton de expandir
        expand_buttons = page.locator('button[aria-label="Expand document"]')
        count = expand_buttons.count()
        for idx in range(min(2, count)):
            expand_buttons.nth(idx).click()
            time.sleep(0.5)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_02_documents_model.png"))
        print("2. Guardado compass_02_documents_model.png")
    except Exception as e:
        print("Error en 2:", e)
        
    # 3. Schema
    try:
        page.locator('button[role="tab"]:has-text("Schema")').first.click()
        time.sleep(2)
        analyze_btn = page.locator('button:has-text("Analyze Schema"), button:has-text("Analyze")').first
        if analyze_btn.is_visible():
            analyze_btn.click()
            time.sleep(6)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_03_schema_distribution.png"))
        print("3. Guardado compass_03_schema_distribution.png")
    except Exception as e:
        print("Error en 3:", e)
        
    # 4. Indexes
    try:
        page.locator('button[role="tab"]:has-text("Indexes")').first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_04_indexes.png"))
        print("4. Guardado compass_04_indexes.png")
    except Exception as e:
        print("Error en 4:", e)
        
    # 5. Explain Plan con consulta
    try:
        page.locator('button[role="tab"]:has-text("Explain Plan")').first.click()
        time.sleep(2)
        # Escribir filtro en la barra de consulta del explain plan
        query_input = page.locator('div[role="textbox"], .query-bar input, textarea').first
        if query_input.is_visible():
            query_input.fill('{ "measurements.temperature_c": { "$gt": 24.0 } }')
            time.sleep(1)
        explain_btn = page.locator('button:has-text("Execute Explain"), button:has-text("Explain")').first
        if explain_btn.is_visible():
            explain_btn.click()
            time.sleep(3)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_06_explain_plan.png"))
        print("5. Guardado compass_06_explain_plan.png")
    except Exception as e:
        print("Error en Explain Plan:", e)

    # 6. Aggregations Tab
    try:
        page.locator('button[role="tab"]:has-text("Aggregations")').first.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUTPUT_DIR, "compass_05_aggregations.png"))
        print("6. Guardado compass_05_aggregations.png")
    except Exception as e:
        print("Error en Aggregations:", e)

print("Proceso de refinamiento finalizado.")
