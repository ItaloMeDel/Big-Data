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
        
        # Check query editor
        # In Compass, Monaco editor is used for query bar
        # Let's click on the query bar text area and type
        print("Clicking query bar...")
        page.locator('text=Type a query').first.click()
        time.sleep(0.5)
        page.keyboard.type('{ ciudad: "Arequipa" }')
        time.sleep(0.5)
        # Click Find
        print("Clicking Find...")
        page.locator('button:has-text("Find")').first.click()
        time.sleep(3)
        page.screenshot(path='compass_filter_arequipa.png')
        print("Saved compass_filter_arequipa.png!")
        
        # Check table view
        print("Switching to table view...")
        # Table view icon has title or testid or button
        table_btn = page.locator('button[aria-label="Table View"], button[title="Table"], [data-testid="toolbar-table-view"]').first
        if table_btn.count() > 0:
            table_btn.click()
            time.sleep(2)
            page.screenshot(path='compass_filter_arequipa_table.png')
            print("Saved compass_filter_arequipa_table.png!")
        else:
            # Try clicking the third view toggle icon
            view_btns = page.locator('.view-toggle button, [data-testid="view-switch"] button, button:has(svg)').all()
            print(f"Found {len(view_btns)} buttons with svg")
            
finally:
    proc.terminate()
