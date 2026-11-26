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
        context = browser.contexts[0]
        pages = context.pages
        print(f"Pages count: {len(pages)}")
        for i, pg in enumerate(pages):
            print(f"Page {i}: title='{pg.title()}' url='{pg.url}'")
        page = pages[0]
        page.set_viewport_size({'width': 1400, 'height': 850})
        time.sleep(2)
        text = page.locator('body').inner_text()
        print("Page text summary:")
        print(text[:300].replace('\n', ' | '))
        page.screenshot(path='compass_playwright_test.png')
        print("Screenshot saved to compass_playwright_test.png!")
finally:
    proc.terminate()
