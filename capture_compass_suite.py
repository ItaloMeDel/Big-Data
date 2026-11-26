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
        
        # 1. Connection screen / new tab
        print("Opening new connection tab...")
        page.locator('button[aria-label="New tab"], [data-testid="add-tab-button"], .tab-bar-item-add').first.click()
        time.sleep(2)
        page.screenshot(path='compass_real_01_conexion.png')
        print("Saved compass_real_01_conexion.png!")
        
        # Go back to guia5_bigdata
        page.locator('text=guia5_bigdata').first.click()
        time.sleep(2)
        page.screenshot(path='compass_real_02_database_overview.png')
        print("Saved compass_real_02_database_overview.png!")
        
        # 2. pruebas_calidad collection
        print("Opening pruebas_calidad...")
        page.locator('text=pruebas_calidad').first.click()
        time.sleep(2)
        page.screenshot(path='compass_real_03_pruebas_calidad.png')
        print("Saved compass_real_03_pruebas_calidad.png!")
        
        # 3. sensores_campus collection
        print("Opening sensores_campus...")
        page.locator('text=sensores_campus').first.click()
        time.sleep(2)
        page.screenshot(path='compass_real_04_sensores_campus.png')
        print("Saved compass_real_04_sensores_campus.png!")
        
        # 4. ventas_masivas Aggregations tab
        print("Opening ventas_masivas Aggregations...")
        page.locator('text=ventas_masivas').first.click()
        time.sleep(2)
        page.locator('button[role="tab"]:has-text("Aggregations")').first.click()
        time.sleep(3)
        page.screenshot(path='compass_real_05_aggregations.png')
        print("Saved compass_real_05_aggregations.png!")
        
finally:
    proc.terminate()
