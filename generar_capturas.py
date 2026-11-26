import subprocess
import html
from playwright.sync_api import sync_playwright

def run_script(script_name):
    res = subprocess.run(["python", script_name], capture_output=True, text=True, encoding="utf-8")
    return res.stdout

def create_terminal_html(title, command, output_text):
    escaped_output = html.escape(output_text)
    # Format sections or highlights
    lines = []
    for line in escaped_output.split("\n"):
        if line.startswith("="):
            lines.append(f"<span style='color: #4ec9b0;'>{line}</span>")
        elif line.startswith(">>>"):
            lines.append(f"<span style='color: #dcdcaa; font-weight: bold;'>{line}</span>")
        elif "VALIDACION EXITOSA" in line or "CORRECTO" in line or "CONCORDANCIA EXACTA" in line:
            lines.append(f"<span style='color: #4ec9b0; font-weight: bold; background: rgba(78,201,176,0.15); padding: 1px 4px; border-radius: 3px;'>{line}</span>")
        elif "[EXCLUIDO]" in line or "Excluidos" in line or "[VALIDO]" in line:
            if "[EXCLUIDO]" in line or "Excluidos" in line:
                lines.append(f"<span style='color: #f14c4c;'>{line}</span>")
            else:
                lines.append(f"<span style='color: #85e89d;'>{line}</span>")
        elif "->" in line:
            parts = line.split("->")
            lines.append(f"<span>{parts[0]}</span><span style='color: #c586c0;'>-&gt;</span><span style='color: #9cdcfe;'>{parts[1]}</span>")
        else:
            lines.append(f"<span style='color: #cccccc;'>{line}</span>")
    formatted_body = "\n".join(lines)

    html_page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    background-color: transparent;
    margin: 0;
    padding: 16px;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    display: flex;
    justify-content: center;
  }}
  .window {{
    width: 860px;
    background-color: #0c0c0c;
    border-radius: 9px;
    box-shadow: 0 12px 36px rgba(0,0,0,0.65);
    overflow: hidden;
    border: 1px solid #333333;
  }}
  .titlebar {{
    background-color: #1a1a1a;
    padding: 7px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #2a2a2a;
    user-select: none;
  }}
  .tabs {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .tab {{
    background-color: #0c0c0c;
    color: #e0e0e0;
    padding: 4px 14px;
    border-radius: 4px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 7px;
    border-top: 2px solid #0078d4;
  }}
  .tab-icon {{
    color: #4ec9b0;
    font-weight: bold;
    font-size: 11px;
  }}
  .controls {{
    display: flex;
    gap: 12px;
  }}
  .ctrl {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
  }}
  .close {{ background-color: #e81123; }}
  .min {{ background-color: #e5a50a; }}
  .max {{ background-color: #26a269; }}
  .content {{
    padding: 18px 22px;
    font-size: 13.5px;
    line-height: 1.48;
    white-space: pre;
    color: #d4d4d4;
    overflow-x: auto;
  }}
  .prompt-line {{
    margin-bottom: 12px;
  }}
  .prompt-ps {{
    color: #569cd6;
    font-weight: bold;
  }}
  .prompt-path {{
    color: #4ec9b0;
  }}
  .prompt-cmd {{
    color: #f9f9f9;
    font-weight: bold;
  }}
</style>
</head>
<body>
  <div class="window">
    <div class="titlebar">
      <div class="tabs">
        <div class="tab">
          <span class="tab-icon">PS</span>
          <span>{title}</span>
        </div>
      </div>
      <div class="controls">
        <span class="ctrl min"></span>
        <span class="ctrl max"></span>
        <span class="ctrl close"></span>
      </div>
    </div>
    <div class="content">
<div class="prompt-line"><span class="prompt-ps">PS </span><span class="prompt-path">C:\\UCSM\\Semestre 10\\Big Data</span>&gt; <span class="prompt-cmd">{command}</span></div>{formatted_body}
    </div>
  </div>
</body>
</html>"""
    return html_page

def main():
    scripts = [
        ("ejercicio1_wordcount.py", "Windows PowerShell - MapReduce WordCount", "python ejercicio1_wordcount.py", "img/captura_ejercicio1.png"),
        ("ejercicio2_eventos.py", "Windows PowerShell - MapReduce Plataforma Academica", "python ejercicio2_eventos.py", "img/captura_ejercicio2.png"),
        ("ejercicio3_laboratorios.py", "Windows PowerShell - MapReduce Soporte Tecnico EPIS", "python ejercicio3_laboratorios.py", "img/captura_ejercicio3.png")
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 960, "height": 1000}, device_scale_factor=2)

        for script, title, cmd, out_img in scripts:
            print(f"Ejecutando {script}...")
            stdout = run_script(script)
            html_content = create_terminal_html(title, cmd, stdout)
            page.set_content(html_content)
            elem = page.query_selector(".window")
            elem.screenshot(path=out_img)
            print(f"  -> Guardada captura: {out_img}")

        browser.close()
    print("Todas las capturas se generaron correctamente.")

if __name__ == "__main__":
    main()
