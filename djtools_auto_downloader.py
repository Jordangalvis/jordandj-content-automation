#!/usr/bin/env python3
"""
djtools_auto_downloader.py — Robot Descargador Automático para DJTools.

Lee el gap_report.json para saber qué géneros te faltan, 
luego analiza tu biblioteca para saber qué artistas de ese género 
tocas más, y busca esos artistas específicos en DJTools.
"""

import argparse
import io
import json
import os
import sys
import time
import csv
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("❌ Error: Falta la librería 'playwright'.")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: Falta 'python-dotenv'.")
    sys.exit(1)

# Configuraciones
load_dotenv(Path(__file__).parent / ".env")
USER = os.getenv("DJTOOLS_USER", "djtools2026new@hotmail.com")
PASS = os.getenv("DJTOOLS_PASS", "+musicq2026@")
URL_LOGIN = "https://djtools.vip/login"
URL_BUSQUEDA = "https://djtools.vip/search?s="
CARPETA_DESCARGAS = Path(r"D:\DJ\Music\Nuevos_DJTools")
RUTA_CSV = r"D:\DJ\analisis\biblioteca_v3.csv"

KEYWORDS_DJ = ["intro", "outro", "open show", "dirty", "extended", "mashup", "transition"]

def extraer_artistas_top(genero_objetivo: str, top_n: int = 4) -> list:
    """Busca en tu propia biblioteca los artistas que más tienes de un género."""
    if not os.path.exists(RUTA_CSV):
        return []
    artistas = []
    try:
        # Intentar utf-8 primero, luego fallback
        try:
            f = open(RUTA_CSV, "r", encoding="utf-8")
        except UnicodeDecodeError:
            f = open(RUTA_CSV, "r", encoding="latin-1")
            
        with f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("genre_carpeta") == genero_objetivo:
                    art = row.get("artista_limpio", "").strip()
                    # Ignorar vacíos o artistas genéricos
                    if art and art.lower() not in ["", "varios", "various artists", "unknown"]:
                        # Tomar solo el primer artista si hay colaboraciones
                        art_principal = art.split(" ft ")[0].split(" feat ")[0].split(",")[0].strip()
                        artistas.append(art_principal)
    except Exception as e:
        print(f"  ⚠️ Error leyendo CSV para artistas: {e}")
        
    if not artistas:
        return []
        
    # Retornar los top N artistas más frecuentes
    mas_comunes = Counter(artistas).most_common(top_n)
    return [a[0] for a in mas_comunes]

def procesar_reporte(ruta_reporte: Path) -> list[str]:
    """Genera consultas basadas en los géneros faltantes y sus top artistas."""
    if not ruta_reporte.exists():
        return []
    with open(ruta_reporte, "r", encoding="utf-8") as f:
        datos = json.load(f)
        
    consultas = []
    if "6_lista_compras" in datos:
        compras = datos["6_lista_compras"]
        generos_necesitados = list(compras.get("generos_nuevos", {}).keys()) + list(compras.get("generos_debiles", {}).keys())
        
        print("\n  🧠 Analizando tu biblioteca para generar búsquedas súper específicas...")
        for genero in generos_necesitados:
            artistas_top = extraer_artistas_top(genero, top_n=3)
            if artistas_top:
                print(f"     • {genero}: Se buscará a {', '.join(artistas_top)}")
                for art in artistas_top:
                    consultas.append(art)
            else:
                consultas.append(genero)
                
    return list(set(consultas))


def iniciar_sesion(page):
    print(f"\n  🔐 Navegando al login de DJTools...")
    page.goto(URL_LOGIN)
    page.fill("input[type='email'], #email", USER)
    page.fill("input[type='password'], #password", PASS)
    print("  ⌨️  Credenciales ingresadas. Iniciando sesión (presionando ENTER)...")
    page.press("#password", "Enter")
    try:
        page.wait_for_url(lambda url: "login" not in url, timeout=20000)
        print("  ✅ Inicio de sesión exitoso.")
    except PlaywrightTimeoutError:
        print("  ⚠️ El sistema tardó en loguear. Revisa si hay un Captcha.")
        input("  Resuélvelo manualmente y presiona ENTER aquí para continuar...")


def descargar_tracks_de_busqueda(page, query: str):
    query_encoded = query.replace(" ", "+")
    url = f"{URL_BUSQUEDA}{query_encoded}&type=name" 
    print(f"\n  🔍 Buscando artista: {query}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  ⚠️ Navegación abortada, reintentando... ({e})")
        time.sleep(2)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e2:
            print(f"  ❌ Fallo al navegar: {e2}")
            return
    
    try:
        page.wait_for_timeout(4000)
        descargas_hechas = 0
        resultados = page.query_selector_all(".producto, .producto_video")
        
        if not resultados:
            print("  ⚠️ No se encontraron tracks para esta búsqueda.")
            return

        for elemento in resultados:
            nodo_nombre = elemento.query_selector(".name")
            if not nodo_nombre:
                continue
                
            texto_track = nodo_nombre.inner_text().strip()
            texto_lower = texto_track.lower()
            
            es_version_dj = any(kw in texto_lower for kw in KEYWORDS_DJ)
            
            if es_version_dj:
                btn_descarga = elemento.query_selector(".downloadButton")
                if btn_descarga:
                    nombre_corto = (texto_track[:47] + '...') if len(texto_track) > 50 else texto_track
                    print(f"  📥 Ideal encontrado: {nombre_corto}")
                    try:
                        with page.expect_download(timeout=15000) as download_info:
                            btn_descarga.click()
                        
                        download = download_info.value
                        nombre_archivo = download.suggested_filename
                        ruta_destino = CARPETA_DESCARGAS / nombre_archivo
                        
                        download.save_as(ruta_destino)
                        print(f"  ✅ Descargado exitosamente.")
                        descargas_hechas += 1
                        
                        if descargas_hechas >= 3: 
                            print("  ⚠️ Límite de 3 tracks alcanzado para esta búsqueda.")
                            break
                    except Exception as e_dl:
                        print(f"  ❌ Falló la descarga de este track.")
                        
        print(f"  🏁 Búsqueda terminada. {descargas_hechas} tracks nuevos obtenidos.")
        
    except Exception as e:
        print(f"  ❌ Error procesando '{query}': {e}")


def main():
    parser = argparse.ArgumentParser(description="🤖 Robot Descargador DJTools")
    parser.add_argument("--report", type=Path, default=Path(__file__).parent / "gap_report.json")
    args = parser.parse_args()
    
    CARPETA_DESCARGAS.mkdir(parents=True, exist_ok=True)
    
    print(f"\n  ╔{'═' * 55}╗")
    print(f"  ║  🤖  DJTOOLS AUTO-DOWNLOADER{' ' * 26}║")
    print(f"  ╚{'═' * 55}╝")
    
    consultas = procesar_reporte(args.report)
    if not consultas:
        print("  ⚠️ No se encontró reporte JSON. Búsqueda de prueba (Aventura).")
        consultas = ["Aventura"]
        
    print(f"\n  📂 Destino: {CARPETA_DESCARGAS}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        
        iniciar_sesion(page)
        
        for i, query in enumerate(consultas, 1):
            print(f"\n  [{i}/{len(consultas)}] Procesando...")
            descargar_tracks_de_busqueda(page, query)
            time.sleep(2)
            
        print("\n  🎉 ¡Misión cumplida! Revisa la carpeta Nuevos_DJTools.")
        
        # Abrir la carpeta automáticamente para el usuario
        if os.name == 'nt':
            os.startfile(CARPETA_DESCARGAS)
            
        page.wait_for_timeout(5000)
        browser.close()


if __name__ == "__main__":
    main()
