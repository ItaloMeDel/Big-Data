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
        
        # Click on guia5_bigdata in left sidebar
        page.locator('text=guia5_bigdata').first.click()
        time.sleep(2)
        
        # Click on ventas_demo
        print("Clicking ventas_demo...")
        page.locator('text=ventas_demo').first.click()
        time.sleep(3)
        page.screenshot(path='compass_ventas_demo.png')
        print("Saved compass_ventas_demo.png!")
        
        # Check tabs
        tabs = page.locator('[role="tab"]').all_inner_texts()
        print("Tabs available:", tabs)
        
        # Now click on ventas_masivas
        print("Clicking ventas_masivas...")
        page.locator('text=ventas_masivas').first.click()
        time.sleep(3)
        page.screenshot(path='compass_ventas_masivas.png')
        print("Saved compass_ventas_masivas.png!")
        
        # Check Indexes tab
        print("Clicking Indexes tab...")
        page.locator('text=Indexes').first.click()
        time.sleep(2)
        page.screenshot(path='compass_indexes.png')
        print("Saved compass_indexes.png!")
        
        # Check Explain Plan tab
        print("Clicking Explain Plan tab...")
        page.locator('text=Explain Plan').first.click()
        time.sleep(2)
        # Click Execute Explain if available
        explain_btn = page.locator('button:has-text("Execute Explain")')
        if explain_btn.count() > 0:
            explain_btn.click()
            time.sleep(2)
        page.screenshot(path='compass_explain_plan.png')
        print("Saved compass_explain_plan.png!")
        
        # Check Aggregations tab
        print("Clicking Aggregations tab...")
        page.locator('text=Aggregations').first.click()
        time.sleep(2)
        page.screenshot(path='compass_aggregations.png')
        print("Saved compass_aggregations.png!")
        
finally:
    proc.terminate()
