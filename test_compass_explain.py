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
        
        # Click on ventas_masivas
        page.locator('text=ventas_masivas').first.click()
        time.sleep(2)
        
        # In query bar, let's type {"ciudad": "Arequipa"}
        # Find the query editor
        editor = page.locator('[aria-label="Query Filter"], [data-testid="query-bar-filter-input"], textarea, input[type="text"]').first
        print("Editor found:", editor)
        
        # Click Explain button
        print("Clicking Explain button in query bar...")
        page.locator('button:has-text("Explain")').first.click()
        time.sleep(3)
        page.screenshot(path='compass_explain_modal.png')
        print("Saved compass_explain_modal.png!")
        
finally:
    proc.terminate()
