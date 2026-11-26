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
        
        # Click on guia5_bigdata
        page.locator('text=guia5_bigdata').first.click()
        time.sleep(2)
        
        # Click on pruebas_calidad card
        print("Clicking pruebas_calidad card...")
        # In the cards view, let's click the card or heading
        page.locator('h3:has-text("pruebas_calidad"), span:has-text("pruebas_calidad")').first.click()
        time.sleep(2)
        page.screenshot(path='compass_07_pruebas_calidad.png')
        print("Saved compass_07_pruebas_calidad.png!")
        
        # Go back to guia5_bigdata
        page.locator('text=guia5_bigdata').first.click()
        time.sleep(2)
        
        # Click on sensores_campus card
        print("Clicking sensores_campus card...")
        page.locator('h3:has-text("sensores_campus"), span:has-text("sensores_campus")').first.click()
        time.sleep(2)
        page.screenshot(path='compass_08_sensores_campus.png')
        print("Saved compass_08_sensores_campus.png!")
        
        # Let's also check indexes of sensores_campus
        page.locator('button[role="tab"]:has-text("Indexes")').first.click()
        time.sleep(2)
        page.screenshot(path='compass_09_sensores_indexes.png')
        print("Saved compass_09_sensores_indexes.png!")
        
finally:
    proc.terminate()
