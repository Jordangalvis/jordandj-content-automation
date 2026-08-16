#!/usr/bin/env python3
"""
trend_detector.py — Detector de tendencias musicales.

Analiza la frescura de la biblioteca, identifica artistas populares
subrepresentados, y genera lista de prioridades de descarga.

Uso:
    python trend_detector.py
    python trend_detector.py --genre Reggaeton
    python trend_detector.py --top 30
"""

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

CSV_DEFAULT = Path(r"D:\DJ\analisis\biblioteca_v3.csv")
SPOTIFY_CACHE = Path(r"D:\DJ\analisis\spotify_cache.json")
AÑO_ACTUAL = 2026

GENEROS_TARGET = [
    "Reggaeton", "Bachata", "SALSA", "Merengue",
    "Hip Hop Night Club", "RnB", "Cumbia", "Dembow",
    "Afrobeats", "FUNK NV", "Musica Mexicana",
]


def safe_float(val) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def safe_int(val) -> int | None:
    f = safe_float(val)
    return int(f) if f is not None and 1900 < f < 2100 else None


def leer_csv(ruta: Path) -> list[dict]:
    """Lee el CSV con fallback de encoding."""
    for enc in ("utf-8", "latin-1"):
        try:
            with open(ruta, "r", encoding=enc, newline="") as f:
                datos = list(csv.DictReader(f))
            if datos:
                print(f"  ✅ CSV cargado ({enc}): {len(datos):,} tracks")
                return datos
        except (UnicodeDecodeError, UnicodeError):
            continue
    print("  ❌ No se pudo leer el CSV")
    sys.exit(1)


def detectar_col_año(fila: dict) -> str | None:
    for c in ("año_spotify", "a\u00f1o_spotify", "ano_spotify"):
        if c in fila:
            return c
    for c in fila:
        if "spotify" in c.lower() and ("año" in c.lower() or "ano" in c.lower()):
            return c
    return None


def analizar_frescura(datos: list[dict], col_año: str, genero_filtro: str = None):
    """Analiza frescura del catálogo por género."""
    print(f"\n  ╔{'═' * 75}╗")
    print(f"  ║  📅  ANÁLISIS DE FRESCURA DEL CATÁLOGO{' ' * 35}║")
    print(f"  ╚{'═' * 75}╝")

    generos = [genero_filtro] if genero_filtro else GENEROS_TARGET

    print(f"\n  {'Género':<22} {'Total':>6} {'2026':>6} {'2025':>6} {'2024':>6} {'<2024':>6} {'% Rec':>6}  Estado")
    print(f"  {'─' * 75}")

    resultados = {}
    for genero in generos:
        tracks = [r for r in datos
                  if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()]
        total = len(tracks)
        if total == 0:
            continue

        años = [safe_int(t.get(col_año)) for t in tracks]
        años = [a for a in años if a]

        t26 = sum(1 for a in años if a >= 2026)
        t25 = sum(1 for a in años if a == 2025)
        t24 = sum(1 for a in años if a == 2024)
        ant = sum(1 for a in años if a < 2024)
        recientes = t26 + t25
        pct_rec = (recientes / len(años) * 100) if años else 0

        if pct_rec < 5:
            estado = "🔴 Urgente"
        elif pct_rec < 15:
            estado = "🟡 Necesita"
        else:
            estado = "🟢 OK"

        print(f"  {genero:<22} {total:>6} {t26:>6} {t25:>6} {t24:>6} {ant:>6} {pct_rec:>5.1f}%  {estado}")

        resultados[genero] = {
            "total": total, "2026": t26, "2025": t25, "2024": t24,
            "anteriores": ant, "pct_recientes": round(pct_rec, 1), "estado": estado,
        }

    return resultados


def analizar_artistas_top(datos: list[dict], top_n: int, genero_filtro: str = None):
    """Encuentra artistas más populares y su representación."""
    print(f"\n  ╔{'═' * 75}╗")
    print(f"  ║  ⭐  TOP ARTISTAS POR POPULARIDAD{' ' * 40}║")
    print(f"  ╚{'═' * 75}╝")

    if genero_filtro:
        datos = [r for r in datos
                 if (r.get("genre_carpeta") or "").strip().lower() == genero_filtro.lower()]

    # Agrupar por artista
    artistas = defaultdict(lambda: {"tracks": 0, "max_pop": 0, "generos": set(), "años": []})
    for r in datos:
        a = (r.get("artista_limpio") or "").strip()
        if not a or len(a) < 2:
            continue

        pop = safe_float(r.get("popularidad")) or 0
        año = safe_int(r.get(detectar_col_año(r))) if detectar_col_año(r) else None
        genero = (r.get("genre_carpeta") or "").strip()

        artistas[a]["tracks"] += 1
        artistas[a]["max_pop"] = max(artistas[a]["max_pop"], pop)
        artistas[a]["generos"].add(genero)
        if año:
            artistas[a]["años"].append(año)

    # Top por popularidad
    top = sorted(artistas.items(), key=lambda x: x[1]["max_pop"], reverse=True)[:top_n]

    print(f"\n  {'#':>3} {'Artista':<30} {'Tracks':>7} {'Pop Max':>8} {'Géneros':<20} {'Recientes':>9}")
    print(f"  {'─' * 80}")

    for i, (nombre, info) in enumerate(top, 1):
        recientes = sum(1 for a in info["años"] if a >= 2025)
        generos_str = ", ".join(list(info["generos"])[:2])
        indicador = " 🔥" if recientes > 0 else " ⚠️" if info["max_pop"] >= 70 and recientes == 0 else ""
        print(f"  {i:>3} {nombre:<30} {info['tracks']:>7} {info['max_pop']:>8.0f} {generos_str:<20} {recientes:>9}{indicador}")

    return {n: {"tracks": i["tracks"], "max_pop": i["max_pop"],
                "generos": list(i["generos"]), "recientes": sum(1 for a in i["años"] if a >= 2025)}
            for n, i in top}


def analizar_crecimiento_generos(datos: list[dict], col_año: str):
    """Analiza qué géneros están creciendo vs estancados."""
    print(f"\n  ╔{'═' * 75}╗")
    print(f"  ║  📈  TENDENCIA DE CRECIMIENTO POR GÉNERO{' ' * 32}║")
    print(f"  ╚{'═' * 75}╝")

    resultados = {}
    for genero in GENEROS_TARGET:
        tracks = [r for r in datos
                  if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()]
        if not tracks:
            continue

        años = [safe_int(t.get(col_año)) for t in tracks]
        años = [a for a in años if a]

        t_2024 = sum(1 for a in años if a == 2024)
        t_2025 = sum(1 for a in años if a == 2025)
        t_2026 = sum(1 for a in años if a >= 2026)

        # Tendencia: comparar 2025-2026 vs 2024
        if t_2025 + t_2026 > t_2024 * 1.5:
            tendencia = "📈 Creciendo"
            barra = "▲" * min(10, (t_2025 + t_2026) // 5)
        elif t_2025 + t_2026 > t_2024:
            tendencia = "→  Estable"
            barra = "─" * 5
        elif t_2025 + t_2026 > 0:
            tendencia = "📉 Bajando"
            barra = "▼" * min(5, max(1, t_2024 // 10))
        else:
            tendencia = "⛔ Estancado"
            barra = "✖"

        print(f"  {genero:<22} 2024:{t_2024:>4} → 2025:{t_2025:>4} → 2026:{t_2026:>4}  {barra:<12} {tendencia}")
        resultados[genero] = {"2024": t_2024, "2025": t_2025, "2026": t_2026, "tendencia": tendencia}

    return resultados


def generar_lista_prioridades(frescura: dict, crecimiento: dict, artistas_top: dict):
    """Genera lista de prioridades de descarga para DJTools."""
    print(f"\n  ╔{'═' * 75}╗")
    print(f"  ║  🛒  LISTA DE PRIORIDADES PARA DJTOOLS{' ' * 35}║")
    print(f"  ╚{'═' * 75}╝")

    prioridades = []

    # 1. Géneros urgentes (poca música reciente)
    print(f"\n  🔴 PRIORIDAD ALTA — Géneros que necesitan música reciente:")
    print(f"  {'─' * 60}")
    for genero, info in frescura.items():
        if info["pct_recientes"] < 10:
            est = f"Solo {info['2025'] + info['2026']} tracks de 2025-2026"
            print(f"  • {genero:<22} {est}")
            prioridades.append({
                "genero": genero, "prioridad": "ALTA",
                "razon": f"Catálogo envejecido ({info['pct_recientes']:.0f}% reciente)",
                "accion": "Buscar tracks 2025-2026 en DJTools",
                "estimado": 20,
            })

    # 2. Géneros en crecimiento sin suficiente contenido
    print(f"\n  🟡 PRIORIDAD MEDIA — Géneros a expandir:")
    print(f"  {'─' * 60}")
    generos_debiles = {"Bachata": 300, "Dembow": 100, "FUNK NV": 80, "Afrobeats": 150}
    for genero, objetivo in generos_debiles.items():
        info = frescura.get(genero, {})
        total = info.get("total", 0)
        if total < objetivo:
            faltan = objetivo - total
            print(f"  • {genero:<22} Tiene: {total}, Objetivo: {objetivo}, Faltan: ~{faltan}")
            prioridades.append({
                "genero": genero, "prioridad": "MEDIA",
                "razon": f"Base insuficiente ({total}/{objetivo})",
                "accion": f"Descargar ~{faltan} tracks nuevos",
                "estimado": faltan,
            })

    # 3. Artistas populares sin tracks recientes
    print(f"\n  🟢 PRIORIDAD NORMAL — Artistas populares a actualizar:")
    print(f"  {'─' * 60}")
    for nombre, info in artistas_top.items():
        if info["max_pop"] >= 70 and info["recientes"] == 0:
            print(f"  • {nombre:<30} Pop: {info['max_pop']:.0f} | 0 tracks recientes")
            prioridades.append({
                "genero": ", ".join(info["generos"][:2]), "prioridad": "NORMAL",
                "razon": f"Artista popular ({info['max_pop']:.0f}) sin tracks de 2025-2026",
                "accion": f"Buscar nuevos lanzamientos de {nombre}",
                "estimado": 3,
            })

    # Resumen
    total_estimado = sum(p["estimado"] for p in prioridades)
    print(f"\n  {'═' * 60}")
    print(f"  📦 TOTAL ESTIMADO DE TRACKS A DESCARGAR: ~{total_estimado}")
    print(f"  {'═' * 60}")

    return prioridades


def main():
    parser = argparse.ArgumentParser(
        description="📈 Detector de tendencias musicales",
    )
    parser.add_argument("--csv", type=Path, default=CSV_DEFAULT,
                        help="Ruta al CSV de la biblioteca")
    parser.add_argument("--genre", type=str, default=None,
                        help="Filtrar a un género específico")
    parser.add_argument("--output", type=Path, default=None,
                        help="Guardar reporte JSON")
    parser.add_argument("--top", type=int, default=20,
                        help="Top N artistas a mostrar (default: 20)")

    args = parser.parse_args()

    print(f"\n  ╔{'═' * 55}╗")
    print(f"  ║  📈  TREND DETECTOR — Biblioteca DJ{' ' * 17}║")
    print(f"  ╚{'═' * 55}╝")

    # Cargar datos
    datos = leer_csv(args.csv)
    col_año = detectar_col_año(datos[0]) if datos else None
    if not col_año:
        print("  ⚠️ No se encontró columna de año en el CSV")

    # Análisis
    frescura = analizar_frescura(datos, col_año, args.genre) if col_año else {}
    artistas = analizar_artistas_top(datos, args.top, args.genre)
    crecimiento = analizar_crecimiento_generos(datos, col_año) if col_año and not args.genre else {}
    prioridades = generar_lista_prioridades(frescura, crecimiento, artistas)

    # Guardar reporte
    if args.output:
        reporte = {
            "frescura": frescura, "artistas_top": artistas,
            "crecimiento": crecimiento, "prioridades": prioridades,
            "generado": datetime.now().isoformat() if 'datetime' in dir() else "N/A",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2)
        print(f"\n  💾 Reporte guardado en: {args.output}")

    print(f"\n  ✅ Análisis de tendencias completado.\n")


if __name__ == "__main__":
    main()
