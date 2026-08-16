#!/usr/bin/env python3
"""
djtools_auditor.py — Asistente de descargas para DJTools.

Lee las prioridades de descarga (reporte de gap_analyzer o trend_detector)
y automatiza la búsqueda en el portal de DJTools para facilitar tu descarga manual.
(Filosofía Sous-Chef: el sistema te prepara las opciones, tú eliges y descargas).

Requisitos:
    pip install playwright python-dotenv
    playwright install chromium
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("❌ Error: Falta la librería 'playwright'.")
    print("Ejecuta en tu terminal: pip install playwright && playwright install chromium")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: Falta la librería 'python-dotenv'.")
    print("Ejecuta en tu terminal: pip install python-dotenv")
    sys.exit(1)

# Cargar credenciales desde .env
load_dotenv(Path(__file__).parent / ".env")
USER = os.getenv("DJTOOLS_USER", "djtools2026new@hotmail.com")
PASS = os.getenv("DJTOOLS_PASS", "+musicq2026@")

URL_LOGIN = "https://djtools.vip/login"  # Ajustar si el portal es diferente
URL_BUSQUEDA = "https://djtools.vip/search?q="

def procesar_reporte(ruta_reporte: Path) -> list[str]:
    """Extrae las consultas de búsqueda a partir de los reportes JSON."""
    if not ruta_reporte.exists():
        print(f"❌ No se encontró el reporte: {ruta_reporte}")
        return []
    
    with open(ruta_reporte, "r", encoding="utf-8") as f:
        datos = json.load(f)
    
    consultas = []
    
    # Si es el reporte de trend_detector.py
    if "prioridades" in datos:
        for p in datos["prioridades"]:
            # Extraer nombres de artistas de la razón si es de prioridad NORMAL
            if p["prioridad"] == "NORMAL" and "Artista popular" in p["razon"]:
                artista = p["accion"].replace("Buscar nuevos lanzamientos de ", "").strip()
                consultas.append(artista)
            # Para géneros, agregar el nombre del género y año
            elif p["prioridad"] in ["ALTA", "MEDIA"]:
                genero = p["genero"]
                consultas.append(f"{genero} 2026")
                
    # Si es el reporte de gap_analyzer.py
    elif "6_lista_compras" in datos:
        compras = datos["6_lista_compras"]
        for genero in compras.get("generos_nuevos", {}):
            consultas.append(f"{genero} 2026")
        for genero in compras.get("generos_debiles", {}):
            consultas.append(f"{genero} intro")
            consultas.append(f"{genero} 2026")
            
    return list(set(consultas)) # Eliminar duplicados


def iniciar_sesion_y_buscar(consultas: list[str], max_tabs: int = 5):
    """Abre el navegador, inicia sesión y prepara pestañas de búsqueda."""
    print(f"\n  🚀 Iniciando Playwright para automatizar DJTools...")
    print(f"  🧑‍💻 Usuario: {USER}")
    
    with sync_playwright() as p:
        # Lanzar el navegador en modo no-headless para que el usuario pueda ver e interactuar
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            print(f"\n  🔐 Navegando al login de DJTools...")
            # Aquí podrías necesitar ajustar los selectores dependiendo de la página real
            page.goto(URL_LOGIN, timeout=60000)
            
            # Intentar llenar el formulario de login (ajustar selectores si es necesario)
            print(f"  ⌨️  Ingresando credenciales...")
            # Usando selectores genéricos comunes (type=email, type=password)
            page.fill("input[type='email'], input[name='email'], input[name='username']", USER)
            page.fill("input[type='password'], input[name='password']", PASS)
            page.click("button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Entrar')")
            
            # Esperar a que la página cargue tras el login
            page.wait_for_load_state("networkidle", timeout=15000)
            print(f"  ✅ Inicio de sesión completado (asumiendo éxito).")
            
        except PlaywrightTimeoutError:
            print(f"  ⚠️ Timeout durante el login. Puede que la estructura de la página sea distinta.")
            print(f"  👉 Por favor, inicia sesión manualmente en la ventana que se abrió.")
            input("  Presiona ENTER aquí cuando hayas iniciado sesión...")
        except Exception as e:
            print(f"  ❌ Error inesperado: {e}")
            input("  Presiona ENTER si lograste iniciar sesión manualmente...")

        print(f"\n  🔍 Abriendo pestañas de búsqueda (Mostrando hasta {max_tabs} consultas)...")
        
        # Limitar la cantidad de pestañas para no saturar la memoria
        consultas_a_mostrar = consultas[:max_tabs]
        
        for query in consultas_a_mostrar:
            query_encoded = query.replace(" ", "+")
            url = f"{URL_BUSQUEDA}{query_encoded}"
            print(f"  🔗 Abriendo búsqueda para: {query}")
            nueva_pestana = context.new_page()
            nueva_pestana.goto(url)
            time.sleep(1) # Pequeña pausa entre pestañas
            
        faltantes = len(consultas) - max_tabs
        if faltantes > 0:
            print(f"\n  ℹ️ Hay {faltantes} consultas adicionales que no se abrieron para no saturar el navegador.")
            print(f"     Siguientes en la lista: {', '.join(consultas[max_tabs:max_tabs+3])}...")

        print(f"\n  🎯 ¡Todo listo, Chef!")
        print(f"  El navegador está abierto con las búsquedas listas.")
        print(f"  Descarga los tracks que más te gusten a tu carpeta principal.")
        print(f"\n  🛑 Cierra el navegador manualmente cuando termines (o presiona ENTER aquí para cerrar y salir).")
        
        input()
        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="🎧 Asistente de descargas DJTools",
    )
    parser.add_argument("--report", type=Path, default=Path(__file__).parent / "gap_report.json",
                        help="Ruta al JSON de reporte (gap_report.json o trend_report.json)")
    parser.add_argument("--tabs", type=int, default=5,
                        help="Máximo número de pestañas a abrir (default: 5)")
    
    args = parser.parse_args()
    
    print(f"\n  ╔{'═' * 55}╗")
    print(f"  ║  🛒  DJTOOLS AUDITOR — Asistente de Descargas{' ' * 5}║")
    print(f"  ╚{'═' * 55}╝")
    
    consultas = procesar_reporte(args.report)
    
    if not consultas:
        print("\n  ⚠️ No se encontraron recomendaciones de búsqueda en el reporte.")
        print("  Asegúrate de haber generado el reporte con gap_analyzer.py o trend_detector.py")
        sys.exit(1)
        
    print(f"\n  📋 Se encontraron {len(consultas)} términos clave a buscar:")
    for c in consultas:
        print(f"    • {c}")
        
    iniciar_sesion_y_buscar(consultas, args.tabs)


if __name__ == "__main__":
    main()
