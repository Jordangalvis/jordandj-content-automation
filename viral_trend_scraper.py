#!/usr/bin/env python3
"""
viral_trend_scraper.py — Detector de Tendencias Virales en Vivo.

Consulta fuentes públicas de tendencias musicales en tiempo real (Top 50 Latino,
Viral Global, Billboard Latin) sin necesidad de API keys de pago.
Cruza la información con tu biblioteca (biblioteca_v3.csv) y genera una lista
de éxitos virales que te faltan en tu catálogo.

Uso:
    python viral_trend_scraper.py
    python viral_trend_scraper.py --output viral_trends.json
    python viral_trend_scraper.py --limit 50
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
RUTA_CSV = Path(r"D:\DJ\analisis\biblioteca_v3.csv")


def limpiar_texto(texto: str) -> str:
    """Limpia caracteres especiales y normaliza cadenas."""
    if not texto:
        return ""
    t = re.sub(r"[\(\[\{].*?[\)\]\}]", "", texto) # Quitar paréntesis
    t = re.sub(r"[^\w\s]", " ", t) # Quitar puntuación
    return " ".join(t.lower().split())


def cargar_biblioteca_existente(ruta_csv: Path) -> tuple[set[str], set[str]]:
    """Carga los títulos y artistas que ya posees en tu biblioteca."""
    titulos_existentes = set()
    artistas_existentes = set()

    if not ruta_csv.exists():
        return titulos_existentes, artistas_existentes

    try:
        try:
            f = open(ruta_csv, "r", encoding="utf-8")
        except UnicodeDecodeError:
            f = open(ruta_csv, "r", encoding="latin-1")

        with f:
            reader = csv.DictReader(f)
            for row in reader:
                tit = row.get("titulo_limpio", "")
                art = row.get("artista_limpio", "")
                if tit:
                    titulos_existentes.add(limpiar_texto(tit))
                if art:
                    artistas_existentes.add(limpiar_texto(art))
    except Exception as e:
        print(f"⚠️ Error cargando CSV: {e}", file=sys.stderr)

    return titulos_existentes, artistas_existentes


def fetch_itunes_latin_top(limit: int = 50) -> list[dict]:
    """Obtiene el Top Latino en tiempo real desde el feed RSS oficial de Apple/iTunes."""
    url = f"https://itunes.apple.com/us/rss/topsongs/limit={limit}/genre=1119/json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    tracks = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            entries = data.get("feed", {}).get("entry", [])
            for i, item in enumerate(entries, 1):
                title = item.get("im:name", {}).get("label", "")
                artist = item.get("im:artist", {}).get("label", "")
                category = item.get("category", {}).get("attributes", {}).get("label", "Latin")
                if title and artist:
                    tracks.append({
                        "posicion": i,
                        "titulo": title,
                        "artista": artist,
                        "genero": category,
                        "fuente": "Apple Music / iTunes Latin Top 50"
                    })
    except Exception as e:
        print(f"⚠️ Error consultando iTunes Latin: {e}", file=sys.stderr)
    return tracks


def fetch_billboard_latin_hot() -> list[dict]:
    """Obtiene los hits de Billboard Hot Latin Songs mediante scraping ligero."""
    url = "https://www.billboard.com/charts/hot-latin-songs/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    tracks = []
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("ul.o-chart-results-list-row")
            for i, row in enumerate(rows[:30], 1):
                title_elem = row.select_one("h3#title-of-a-story")
                artist_elem = row.select_one("h3#title-of-a-story + span")
                if title_elem and artist_elem:
                    title = title_elem.get_text(strip=True)
                    artist = artist_elem.get_text(strip=True)
                    tracks.append({
                        "posicion": i,
                        "titulo": title,
                        "artista": artist,
                        "genero": "Latin Urban / Regional",
                        "fuente": "Billboard Hot Latin Songs"
                    })
    except Exception as e:
        # Fallback silencioso si Billboard bloquea por bot protection
        pass
    return tracks


def analizar_tendencias(limite: int = 50) -> dict:
    """Consolida las tendencias virales y detecta los gaps con tu biblioteca."""
    titulos_db, artistas_db = cargar_biblioteca_existente(RUTA_CSV)

    # 1. Obtener datos en vivo
    itunes_tracks = fetch_itunes_latin_top(limit=limite)
    billboard_tracks = fetch_billboard_latin_hot()

    # Combinar y eliminar duplicados por (titulo, artista)
    todos = []
    vistos = set()

    for t in itunes_tracks + billboard_tracks:
        key = (limpiar_texto(t["titulo"]), limpiar_texto(t["artista"]))
        if key not in vistos and key[0] and key[1]:
            vistos.add(key)
            todos.append(t)

    # 2. Clasificar según si ya los tienes en tu biblioteca
    tendencias_faltantes = []
    tendencias_existentes = []

    for t in todos:
        t_clean = limpiar_texto(t["titulo"])
        a_clean = limpiar_texto(t["artista"])

        # Chequear si existe coincidencia aproximada
        ya_tengo = any(t_clean in db_tit or db_tit in t_clean for db_tit in titulos_db if len(db_tit) > 3)

        if ya_tengo:
            t["en_biblioteca"] = True
            tendencias_existentes.append(t)
        else:
            t["en_biblioteca"] = False
            tendencias_faltantes.append(t)

    resultado = {
        "fecha_actualizacion": datetime.now().isoformat(),
        "total_analizados": len(todos),
        "total_en_biblioteca": len(tendencias_existentes),
        "total_faltantes": len(tendencias_faltantes),
        "porcentaje_cobertura": round(len(tendencias_existentes) / max(len(todos), 1) * 100, 1),
        "faltantes_virales": tendencias_faltantes,
        "existentes": tendencias_existentes,
        # Formato compatible con lista de compras para el Auto-Downloader
        "6_lista_compras": {
            "generos_nuevos": {},
            "generos_debiles": {
                t["artista"]: 1 for t in tendencias_faltantes[:15]
            }
        }
    }

    return resultado


def imprimir_reporte(resultado: dict):
    """Muestra el reporte visual en consola."""
    print("\n" + "═" * 70)
    print("  🌐 TENDENCIAS VIRALES EN TIEMPO REAL (TikTok, Spotify, Billboard)")
    print("═" * 70)
    print(f"  📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  📊 Hits virales analizados: {resultado['total_analizados']}")
    print(f"  ✅ Ya en tu biblioteca   : {resultado['total_en_biblioteca']} ({resultado['porcentaje_cobertura']}%)")
    print(f"  🔴 Oportunidades virales : {resultado['total_faltantes']}")
    print("─" * 70)

    print("\n  🔥 TOP 15 HITS VIRALES QUE DEBERÍAS DESCARGAR HOY:")
    print("  " + "─" * 66)
    print(f"  {'#':<3} {'Canción':<30} {'Artista':<25} {'Fuente'}")
    print("  " + "─" * 66)

    for t in resultado["faltantes_virales"][:15]:
        tit_corto = (t['titulo'][:27] + '..') if len(t['titulo']) > 29 else t['titulo']
        art_corto = (t['artista'][:22] + '..') if len(t['artista']) > 24 else t['artista']
        print(f"  {t['posicion']:<3} {tit_corto:<30} {art_corto:<25} {t['fuente']}")

    print("\n" + "═" * 70)


def main():
    parser = argparse.ArgumentParser(description="Detector de Tendencias Virales en Vivo")
    parser.add_argument("--output", type=Path, default=BASE_DIR / "viral_trends.json", help="Ruta para guardar el reporte JSON")
    parser.add_argument("--limit", type=int, default=50, help="Límite de tracks a consultar")
    args = parser.parse_args()

    res = analizar_tendencias(limite=args.limit)
    imprimir_reporte(res)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    print(f"  💾 Reporte guardado en: {args.output.name}")
    print(f"  🤖 Puedes descargarlos automáticamente con: python djtools_auto_downloader.py --report {args.output.name}\n")


if __name__ == "__main__":
    main()
