import sys
import io
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def main():
    print("Abriendo navegador para inspección...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("https://djtools.vip/")
        print("\n  👉 1. Inicia sesión en el navegador.")
        print("  👉 2. Haz una búsqueda manualmente (ej. 'Reggaeton 2026').")
        print("  👉 3. Cuando estés viendo la lista de canciones para descargar, avisa por el chat.")
        
        # Espera hasta que envíe el ENTER por la consola
        input("\n  (Esperando a que envíen ENTER para tomar la foto...)")
        
        html_content = page.content()
        output_path = Path(__file__).parent / "djtools_dom.html"
        output_path.write_text(html_content, encoding="utf-8")
        
        print(f"\n  📸 ¡Fotografía del código HTML tomada!")
        print(f"  💾 Guardado en {output_path.absolute()}")
        browser.close()

if __name__ == "__main__":
    main()
