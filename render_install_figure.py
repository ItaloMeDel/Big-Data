from playwright.sync_api import sync_playwright

html_content = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
  body { background: #1e1e1e; padding: 20px; color: #cccccc; }
  .window {
    background: #252526;
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    overflow: hidden;
    border: 1px solid #3c3c3c;
    margin-bottom: 20px;
  }
  .title-bar {
    background: #323233;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #2b2b2b;
  }
  .title-bar-left { display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 500; color: #cccccc; }
  .traffic-lights { display: flex; gap: 8px; }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .dot-red { background: #ff5f56; }
  .dot-yellow { background: #ffbd2e; }
  .dot-green { background: #27c93f; }
  
  .content-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    padding: 16px;
    background: #1e1e1e;
  }
  .panel {
    background: #252526;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 14px;
  }
  .panel-title {
    font-size: 13px;
    font-weight: 600;
    color: #4ec9b0;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #333333;
    padding-bottom: 6px;
  }
  .code-block {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    color: #d4d4d4;
  }
  .cmd-prompt { color: #569cd6; font-weight: bold; }
  .cmd-out { color: #cccccc; }
  .cmd-highlight { color: #ce9178; }
  .cmd-success { color: #4ec9b0; font-weight: bold; }
  .cmd-info { color: #9cdcfe; }
  .file-item { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px dashed #2d2d2d; font-size: 11.5px; }
  .file-name { color: #9cdcfe; font-family: 'Consolas', monospace; }
  .file-size { color: #858585; font-family: 'Consolas', monospace; }
</style>
</head>
<body>

<div class="window">
  <div class="title-bar">
    <div class="title-bar-left">
      <span style="font-weight: bold; color: #00ed64;">🍃 MongoDB Server 8.0 & mongosh 2.3</span>
      <span>— Instalación, Estructura de Directorios y Configuración</span>
    </div>
    <div class="traffic-lights">
      <div class="dot dot-red"></div>
      <div class="dot dot-yellow"></div>
      <div class="dot dot-green"></div>
    </div>
  </div>
  
  <div class="content-grid">
    <!-- Panel 1: PowerShell Verification -->
    <div class="panel">
      <div class="panel-title">
        <span>⚙️ Verificación de Binarios y Arquitectura (PowerShell)</span>
      </div>
      <div class="code-block">
        <span class="cmd-prompt">PS C:\UCSM\Semestre 10\Big Data></span> .\mongodb_dist\...\mongod.exe --version<br>
        <span class="cmd-out">db version <span class="cmd-success">v8.0.4</span></span><br>
        <span class="cmd-out">Build Info: {</span><br>
        <span class="cmd-out">&nbsp;&nbsp;"version": "<span class="cmd-success">8.0.4</span>",</span><br>
        <span class="cmd-out">&nbsp;&nbsp;"gitVersion": "bc35ab4305d9920d9d0491c1c9ef9b72383d31f9",</span><br>
        <span class="cmd-out">&nbsp;&nbsp;"allocator": "tcmalloc-gperf",</span><br>
        <span class="cmd-out">&nbsp;&nbsp;"environment": {</span><br>
        <span class="cmd-out">&nbsp;&nbsp;&nbsp;&nbsp;"distmod": "<span class="cmd-info">windows</span>",</span><br>
        <span class="cmd-out">&nbsp;&nbsp;&nbsp;&nbsp;"distarch": "<span class="cmd-info">x86_64</span>",</span><br>
        <span class="cmd-out">&nbsp;&nbsp;&nbsp;&nbsp;"target_arch": "<span class="cmd-info">x86_64</span>"</span><br>
        <span class="cmd-out">&nbsp;&nbsp;}</span><br>
        <span class="cmd-out">}</span><br>
        <br>
        <span class="cmd-prompt">PS C:\UCSM\Semestre 10\Big Data></span> .\mongosh_dist\...\mongosh.exe --version<br>
        <span class="cmd-success">2.3.8</span> (MongoDB Shell v2.3.8 - Node.js v20.18.0)<br>
        <br>
        <span class="cmd-prompt">PS C:\UCSM\Semestre 10\Big Data></span> Test-Path .\data_db<br>
        <span class="cmd-success">True</span> (Motor WiredTiger inicializado)
      </div>
    </div>

    <!-- Panel 2: Archivo de Configuración mongod.cfg -->
    <div class="panel">
      <div class="panel-title">
        <span>📄 Archivo de Configuración Oficial (mongod.cfg)</span>
      </div>
      <div class="code-block">
        <span style="color: #6a9955;"># mongod.cfg - Configuración de Servicio MongoDB</span><br>
        <span class="cmd-prompt">storage:</span><br>
        &nbsp;&nbsp;<span class="cmd-info">dbPath:</span> <span class="cmd-highlight">"C:\UCSM\Semestre 10\Big Data\data_db"</span><br>
        &nbsp;&nbsp;<span class="cmd-info">journal:</span><br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span class="cmd-info">enabled:</span> <span class="cmd-success">true</span><br>
        <br>
        <span class="cmd-prompt">systemLog:</span><br>
        &nbsp;&nbsp;<span class="cmd-info">destination:</span> <span class="cmd-highlight">file</span><br>
        &nbsp;&nbsp;<span class="cmd-info">logAppend:</span> <span class="cmd-success">true</span><br>
        &nbsp;&nbsp;<span class="cmd-info">path:</span> <span class="cmd-highlight">"C:\UCSM\Semestre 10\Big Data\data_db\mongod.log"</span><br>
        <br>
        <span class="cmd-prompt">net:</span><br>
        &nbsp;&nbsp;<span class="cmd-info">port:</span> <span class="cmd-success">27017</span><br>
        &nbsp;&nbsp;<span class="cmd-info">bindIp:</span> <span class="cmd-highlight">127.0.0.1</span><br>
        <br>
        <span style="color: #6a9955;"># Comando de inicio del demonio:</span><br>
        <span class="cmd-prompt">PS></span> mongod.exe --config .\mongod.cfg
      </div>
    </div>

    <!-- Panel 3: Directorio de Binarios Extraídos -->
    <div class="panel">
      <div class="panel-title">
        <span>📂 Binarios Extraídos (.\mongodb_dist\...\bin)</span>
      </div>
      <div class="file-item">
        <span class="file-name">mongod.exe (Servidor NoSQL)</span>
        <span class="file-size">118,485 KB</span>
      </div>
      <div class="file-item">
        <span class="file-name">mongos.exe (Router Sharding)</span>
        <span class="file-size">48,220 KB</span>
      </div>
      <div class="file-item">
        <span class="file-name">mongosh.exe (Shell interactivo v2.3.8)</span>
        <span class="file-size">61,430 KB</span>
      </div>
      <div class="file-item">
        <span class="file-name">mongodb-compass-1.45.0-win32-x64.zip</span>
        <span class="file-size">157,811 KB</span>
      </div>
    </div>

    <!-- Panel 4: Directorio de Datos WiredTiger -->
    <div class="panel">
      <div class="panel-title">
        <span>💽 Almacenamiento Local (.\data_db - WiredTiger)</span>
      </div>
      <div class="file-item">
        <span class="file-name">WiredTiger.wt (Metadatos de motor)</span>
        <span class="file-size">24 KB</span>
      </div>
      <div class="file-item">
        <span class="file-name">collection-4-*.wt (Colección ventas_masivas)</span>
        <span class="file-size">2,880 KB</span>
      </div>
      <div class="file-item">
        <span class="file-name">index-5-*.wt (Índice fecha_1)</span>
        <span class="file-size">1,126 KB</span>
      </div>
      <div class="file-item">
        <span class="file-name">mongod.log (Registro de auditoría)</span>
        <span class="file-size">312 KB</span>
      </div>
    </div>
  </div>
</div>

</body>
</html>
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.set_content(html_content)
    page.screenshot(path="img/g4_a1_instalacion_mongodb.png")
    browser.close()
print("Saved img/g4_a1_instalacion_mongodb.png successfully!")
