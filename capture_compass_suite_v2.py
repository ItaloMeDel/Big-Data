import subprocess
import time
from playwright.sync_api import sync_playwright

proc = subprocess.Popen([
    r'.\compass_dist\MongoDBCompass.exe',
    '--ignoreAdditionalCommandLineFlags',
    '--remote-debugging-port=9222',
    'mongodb://localhost:27017'
])
time.sleep(8)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp('http://localhost:9222')
        page = browser.contexts[0].pages[0]
        page.set_viewport_size({'width': 1400, 'height': 850})
        time.sleep(1)
        
        # 1. Connection / Welcome view
        try:
            print("Capturing Welcome / Connection screen...")
            page.locator('text=Welcome').first.click()
            time.sleep(1)
            page.screenshot(path='compass_01_welcome_conexion.png')
            print("Saved compass_01_welcome_conexion.png!")
        except Exception as e:
            print("Welcome error:", e)

        # 2. Database Overview: guia5_bigdata
        try:
            print("Capturing guia5_bigdata database overview...")
            page.locator('text=guia5_bigdata').first.click()
            time.sleep(2)
            page.screenshot(path='compass_02_database_overview.png')
            print("Saved compass_02_database_overview.png!")
        except Exception as e:
            print("Database overview error:", e)

        # 3. Collection: ventas_demo
        try:
            print("Capturing ventas_demo...")
            page.locator('text=ventas_demo').first.click()
            time.sleep(2)
            page.screenshot(path='compass_03_ventas_demo.png')
            print("Saved compass_03_ventas_demo.png!")
        except Exception as e:
            print("ventas_demo error:", e)

        # 4. Collection: ventas_masivas
        try:
            print("Capturing ventas_masivas...")
            page.locator('text=ventas_masivas').first.click()
            time.sleep(2)
            page.screenshot(path='compass_04_ventas_masivas.png')
            print("Saved compass_04_ventas_masivas.png!")
        except Exception as e:
            print("ventas_masivas error:", e)

        # 5. Indexes on ventas_masivas
        try:
            print("Capturing indexes tab...")
            page.locator('button[role="tab"]:has-text("Indexes")').first.click()
            time.sleep(2)
            page.screenshot(path='compass_05_indexes.png')
            print("Saved compass_05_indexes.png!")
        except Exception as e:
            print("Indexes error:", e)

        # 6. Aggregations tab on ventas_masivas
        try:
            print("Capturing Aggregations tab...")
            page.locator('button[role="tab"]:has-text("Aggregations")').first.click()
            time.sleep(3)
            page.screenshot(path='compass_06_aggregations.png')
            print("Saved compass_06_aggregations.png!")
        except Exception as e:
            print("Aggregations error:", e)

        # 7. Collection: pruebas_calidad
        try:
            print("Capturing pruebas_calidad...")
            # Click in sidebar
            page.locator('.sidebar-databases-and-collections, [aria-label="Navigation"]').locator('text=pruebas_calidad').first.click()
            time.sleep(2)
            page.screenshot(path='compass_07_pruebas_calidad.png')
            print("Saved compass_07_pruebas_calidad.png!")
        except Exception as e:
            print("pruebas_calidad error:", e)

        # 8. Collection: sensores_campus
        try:
            print("Capturing sensores_campus...")
            page.locator('.sidebar-databases-and-collections, [aria-label="Navigation"]').locator('text=sensores_campus').first.click()
            time.sleep(2)
            page.screenshot(path='compass_08_sensores_campus.png')
            print("Saved compass_08_sensores_campus.png!")
        except Exception as e:
            print("sensores_campus error:", e)

finally:
    proc.terminate()
