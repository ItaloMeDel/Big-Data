import subprocess
import time
from playwright.sync_api import sync_playwright

proc = subprocess.Popen([
    r'.\compass_dist\MongoDBCompass.exe',
    '--ignoreAdditionalCommandLineFlags',
    '--remote-debugging-port=9222'
])
time.sleep(8)

try:
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp('http://localhost:9222')
        page = browser.contexts[0].pages[0]
        page.set_viewport_size({'width': 1400, 'height': 850})
        time.sleep(2)
        
        # Click "Add new connection"
        print("Clicking Add new connection...")
        add_btn = page.locator('text=Add new connection, [aria-label="Add new connection"]').first
        if add_btn.count() > 0:
            add_btn.click()
            time.sleep(2)
        
        # Take screenshot of connection setup
        page.screenshot(path='compass_01_conexion_setup.png')
        print("Saved compass_01_conexion_setup.png!")
        
finally:
    proc.terminate()
