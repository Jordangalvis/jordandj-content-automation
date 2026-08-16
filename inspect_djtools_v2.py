import sys
import io
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def main():
    print("Abriendo navegador para inspección profunda...")
    flag_file = Path(__file__).parent / "ready.txt"
    if flag_file.exists():
        flag_file.unlink()
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("https://djtools.vip/")
        print("\n  👉 1. Inicia sesión en el navegador.")
        print("  👉 2. Haz una búsqueda manualmente.")
        print("  👉 3. Cuando estés listo, avisa por chat.")
        
        print("\n  (Esperando a que el sistema active la señal para tomar la foto...)")
        
        while not flag_file.exists():
            time.sleep(1)
            
        print("\n  📸 Señal detectada, capturando pestañas...")
        
        for i, p_tab in enumerate(context.pages):
            try:
                html = p_tab.content()
                url = p_tab.url
                output = Path(__file__).parent / f"djtools_dom_tab{i}.html"
                output.write_text(f"<!-- URL: {url} -->\n" + html, encoding="utf-8")
                print(f"  ✅ Pestaña {i} ({url}) guardada en {output.name}")
            except Exception as e:
                print(f"  ❌ Error capturando pestaña {i}: {e}")
                
        browser.close()
        print("\n  ✅ ¡Análisis completado! Navegador cerrado.")
        if flag_file.exists():
            flag_file.unlink()

if __name__ == "__main__":
    main()
