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
        
        page.locator('text=guia5_bigdata').first.click()
        time.sleep(2)
        page.locator('text=ventas_masivas').first.click()
        time.sleep(2)
        
        # Click CodeMirror content
        print("Clicking .cm-content...")
        page.locator('.cm-content').first.click()
        time.sleep(0.5)
        # Select all and type filter
        page.keyboard.press('Control+A')
        page.keyboard.type('{ ciudad: "Arequipa" }')
        time.sleep(0.5)
        
        # Click Find
        print("Clicking Find...")
        page.locator('button:has-text("Find")').first.click()
        time.sleep(3)
        page.screenshot(path='compass_filter_arequipa_success.png')
        print("Saved compass_filter_arequipa_success.png!")
        
        # Now click table view button
        print("Clicking Table View...")
        # In Compass, the view buttons are in a group with icons
        page.locator('[data-testid="view-switch-table"], button[title="Table"], button[aria-label="Table View"]').first.click()
        time.sleep(2)
        page.screenshot(path='compass_table_view.png')
        print("Saved compass_table_view.png!")
        
finally:
    proc.terminate()
