#!/usr/bin/env python3
"""
gap_analyzer.py — Analizador de brechas para la biblioteca musical DJ.

Lee el CSV de la biblioteca musical y genera un reporte comprehensivo
de análisis de brechas: cobertura de géneros, distribución de BPM,
niveles de energía, frescura del catálogo, cobertura de versiones
y lista de compras recomendada.

Uso:
    python gap_analyzer.py
    python gap_analyzer.py --csv "D:\\DJ\\analisis\\biblioteca_v3.csv"
    python gap_analyzer.py --output reporte.json
    python gap_analyzer.py --dry-run
"""

import argparse
import csv
import io
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Fix encoding para Windows (cp1252 no soporta emoji/unicode)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Configuración de géneros objetivo ────────────────────────────────────────

# Géneros actuales (ya tenemos contenido significativo)
GENEROS_ACTUALES = [
    "Reggaeton", "Bachata", "SALSA", "Merengue",
    "Hip Hop Night Club", "RnB"
]

# Géneros nuevos o a expandir
GENEROS_EXPANDIR = [
    "Cumbia", "Dembow", "Afrobeats", "FUNK NV", "Musica Mexicana"
]

# Todos los géneros objetivo
GENEROS_OBJETIVO = GENEROS_ACTUALES + GENEROS_EXPANDIR

# Rangos de BPM "sweet spot" por género
BPM_SWEET_SPOTS: dict[str, tuple[float, float]] = {
    "Reggaeton":          (88, 100),
    "Bachata":            (125, 135),
    "SALSA":              (85, 100),
    "Merengue":           (130, 140),
    "Hip Hop Night Club": (85, 100),
    "RnB":                (90, 105),
    "Dembow":             (115, 125),
    "Cumbia":             (95, 105),
}

# Mínimo de tracks para un set viable por género nuevo
MINIMO_SET_VIABLE = 50

# Tipos de versión reconocidos
TIPOS_VERSION = [
    "FULL", "INTRO", "CLEAN", "EXTENDED", "DIRTY", "INTRO-OUTRO",
    "ACAPELLA", "MASHUP", "STARTER", "OPEN SHOW", "TRANSITION",
    "OUTRO", "REDRUM", "PERCAPELLA"
]

# Año actual para análisis de frescura
AÑO_ACTUAL = 2026


# ─── Funciones de utilidad para formato de consola ────────────────────────────

def linea_doble(ancho: int = 80) -> str:
    """Dibuja una línea doble ═."""
    return "═" * ancho


def linea_simple(ancho: int = 80) -> str:
    """Dibuja una línea simple ─."""
    return "─" * ancho


def titulo_seccion(texto: str, emoji: str = "📊", ancho: int = 80) -> str:
    """Genera un título de sección con formato bonito."""
    lineas = []
    lineas.append("")
    lineas.append(f"╔{linea_doble(ancho - 2)}╗")
    contenido = f" {emoji}  {texto} "
    relleno = ancho - 2 - len(contenido)
    lineas.append(f"║{contenido}{' ' * max(0, relleno)}║")
    lineas.append(f"╚{linea_doble(ancho - 2)}╝")
    return "\n".join(lineas)


def subtitulo(texto: str, emoji: str = "▸") -> str:
    """Genera un subtítulo con formato."""
    return f"\n  {emoji} {texto}\n  {linea_simple(len(texto) + 4)}"


def barra_horizontal(valor: int, maximo: int, ancho_barra: int = 30) -> str:
    """Genera una barra horizontal de progreso con bloques."""
    if maximo == 0:
        return "░" * ancho_barra
    proporcion = min(valor / maximo, 1.0)
    llenos = int(proporcion * ancho_barra)
    vacios = ancho_barra - llenos
    return "█" * llenos + "░" * vacios


def formatear_porcentaje(parte: int, total: int) -> str:
    """Formatea un porcentaje con manejo de división por cero."""
    if total == 0:
        return "  0.0%"
    return f"{(parte / total) * 100:5.1f}%"


# ─── Lectura del CSV ─────────────────────────────────────────────────────────

def leer_csv(ruta_csv: Path) -> list[dict[str, str]]:
    """
    Lee el CSV de la biblioteca musical.
    Intenta UTF-8 primero, luego latin-1 como respaldo.
    Retorna lista de diccionarios (filas).
    """
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(ruta_csv, "r", encoding=encoding, newline="") as f:
                lector = csv.DictReader(f)
                datos = list(lector)
            if datos:
                print(f"  ✅ CSV leído correctamente con encoding '{encoding}'")
                print(f"  📁 Total de filas: {len(datos):,}")
                # Mostrar columnas detectadas para diagnóstico
                columnas = list(datos[0].keys())
                print(f"  📋 Columnas detectadas: {len(columnas)}")
                return datos
        except (UnicodeDecodeError, UnicodeError):
            continue
        except FileNotFoundError:
            print(f"  ❌ Error: No se encontró el archivo: {ruta_csv}")
            sys.exit(1)

    print(f"  ❌ Error: No se pudo leer el CSV con ningún encoding")
    sys.exit(1)


def detectar_columna_tamaño(fila: dict[str, str]) -> str | None:
    """
    Detecta el nombre real de la columna de tamaño en MB.
    Puede ser 'tamaño_mb' o 'tama_o_mb' según el encoding.
    """
    for candidato in ("tamaño_mb", "tama_o_mb", "tamano_mb", "tama\u00f1o_mb"):
        if candidato in fila:
            return candidato
    # Buscar por coincidencia parcial
    for col in fila:
        if "tama" in col.lower() and "mb" in col.lower():
            return col
    return None


def detectar_columna_año(fila: dict[str, str]) -> str | None:
    """
    Detecta el nombre real de la columna de año.
    Puede ser 'año_spotify' o variantes según encoding.
    """
    for candidato in ("año_spotify", "a\u00f1o_spotify", "ano_spotify"):
        if candidato in fila:
            return candidato
    for col in fila:
        if "spotify" in col.lower() and ("año" in col.lower() or "ano" in col.lower() or "a\u00f1o" in col.lower()):
            return col
    return None


# ─── Funciones de parseo seguro ──────────────────────────────────────────────

def parsear_float(valor: str | None) -> float | None:
    """Parsea un valor flotante de forma segura."""
    if valor is None or valor.strip() == "":
        return None
    try:
        return float(valor.strip())
    except (ValueError, TypeError):
        return None


def parsear_bool(valor: str | None) -> bool:
    """Parsea un valor booleano desde string."""
    if valor is None:
        return False
    return valor.strip().lower() in ("true", "1", "sí", "si", "yes")


def parsear_año(valor: str | None) -> int | None:
    """Parsea un año desde string (puede tener .0)."""
    f = parsear_float(valor)
    if f is not None and 1900 < f < 2100:
        return int(f)
    return None


# ─── Análisis principal ──────────────────────────────────────────────────────

def analizar_cobertura_generos(datos: list[dict], col_año: str | None) -> dict[str, Any]:
    """
    Análisis 1: Cobertura de géneros objetivo.
    Para cada género: total, únicos, con BPM, con energía, desglose de versiones.
    """
    resultados: dict[str, Any] = {}

    for genero in GENEROS_OBJETIVO:
        # Filtrar tracks de este género (comparación case-insensitive)
        tracks = [
            r for r in datos
            if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()
        ]
        total = len(tracks)

        # Tracks únicos (no duplicados)
        unicos = [t for t in tracks if not parsear_bool(t.get("es_duplicado"))]
        total_unicos = len(unicos)

        # Tracks con BPM
        con_bpm = sum(1 for t in tracks if parsear_float(t.get("bpm_mik")) is not None)

        # Tracks con energía
        con_energia = sum(1 for t in tracks if parsear_float(t.get("energy_mik")) is not None)

        # Desglose de versiones
        version_counts: Counter = Counter()
        for t in tracks:
            v = (t.get("version_tipo") or "").strip().upper()
            if v:
                version_counts[v] += 1
            else:
                version_counts["SIN TIPO"] += 1

        # Tracks por año (para frescura)
        por_año: Counter = Counter()
        if col_año:
            for t in tracks:
                año = parsear_año(t.get(col_año))
                if año:
                    por_año[año] += 1

        resultados[genero] = {
            "total": total,
            "unicos": total_unicos,
            "duplicados": total - total_unicos,
            "con_bpm": con_bpm,
            "con_energia": con_energia,
            "versiones": dict(version_counts.most_common()),
            "por_año": dict(sorted(por_año.items())),
            "categoria": "actual" if genero in GENEROS_ACTUALES else "expandir",
        }

    return resultados


def analizar_bpm(datos: list[dict]) -> dict[str, Any]:
    """
    Análisis 2: Distribución de BPM por género en buckets de 5 BPM.
    Identifica sweet spots subrepresentados.
    """
    resultados: dict[str, Any] = {}

    for genero in GENEROS_OBJETIVO:
        tracks = [
            r for r in datos
            if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()
        ]

        # Extraer BPMs válidos
        bpms = []
        for t in tracks:
            bpm = parsear_float(t.get("bpm_mik"))
            if bpm is not None and 40 < bpm < 250:
                bpms.append(bpm)

        if not bpms:
            resultados[genero] = {
                "total_con_bpm": 0,
                "distribucion": {},
                "sweet_spot": BPM_SWEET_SPOTS.get(genero),
                "sweet_spot_count": 0,
                "sweet_spot_porcentaje": 0,
                "alerta": "⚠️ Sin datos de BPM",
                "bpm_min": None,
                "bpm_max": None,
                "bpm_media": None,
            }
            continue

        # Distribución en buckets de 5 BPM
        buckets: Counter = Counter()
        for bpm in bpms:
            bucket = int(bpm // 5) * 5
            buckets[bucket] += 1

        # Análisis de sweet spot
        sweet = BPM_SWEET_SPOTS.get(genero)
        sweet_count = 0
        if sweet:
            lo, hi = sweet
            sweet_count = sum(1 for b in bpms if lo <= b <= hi)

        porcentaje_sweet = (sweet_count / len(bpms) * 100) if bpms else 0

        # Determinar si el sweet spot está subrepresentado (<40% de tracks)
        alerta = None
        if sweet and porcentaje_sweet < 40:
            alerta = f"⚠️ Sweet spot subrepresentado ({porcentaje_sweet:.1f}%)"

        resultados[genero] = {
            "total_con_bpm": len(bpms),
            "distribucion": dict(sorted(buckets.items())),
            "sweet_spot": sweet,
            "sweet_spot_count": sweet_count,
            "sweet_spot_porcentaje": round(porcentaje_sweet, 1),
            "alerta": alerta,
            "bpm_min": round(min(bpms), 1),
            "bpm_max": round(max(bpms), 1),
            "bpm_media": round(sum(bpms) / len(bpms), 1),
        }

    return resultados


def analizar_energia(datos: list[dict]) -> dict[str, Any]:
    """
    Análisis 3: Distribución de energía por género (niveles 1-10).
    Alerta si faltan tracks de alta (8-10) o baja (1-4) energía.
    """
    resultados: dict[str, Any] = {}

    for genero in GENEROS_OBJETIVO:
        tracks = [
            r for r in datos
            if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()
        ]

        # Energías válidas
        energias = []
        for t in tracks:
            e = parsear_float(t.get("energy_mik"))
            if e is not None and 1 <= e <= 10:
                energias.append(int(round(e)))

        distribucion = Counter(energias)
        # Asegurar que todos los niveles estén presentes
        dist_completa = {i: distribucion.get(i, 0) for i in range(1, 11)}

        # Conteos por rango
        baja = sum(dist_completa[i] for i in range(1, 5))      # 1-4
        media = sum(dist_completa[i] for i in range(5, 8))      # 5-7
        alta = sum(dist_completa[i] for i in range(8, 11))       # 8-10
        total_e = len(energias)

        alertas = []
        if total_e > 0:
            if alta == 0:
                alertas.append("🔴 Sin tracks de alta energía (8-10) para peaks")
            elif alta / total_e < 0.15:
                alertas.append(f"🟡 Pocos tracks de alta energía: {alta} ({alta/total_e*100:.0f}%)")
            if baja == 0:
                alertas.append("🔴 Sin tracks de baja energía (1-4) para intros")
            elif baja / total_e < 0.10:
                alertas.append(f"🟡 Pocos tracks de baja energía: {baja} ({baja/total_e*100:.0f}%)")
        elif len(tracks) > 0:
            alertas.append("⚠️ Sin datos de energía")

        resultados[genero] = {
            "total_con_energia": total_e,
            "distribucion": dist_completa,
            "baja_1_4": baja,
            "media_5_7": media,
            "alta_8_10": alta,
            "alertas": alertas,
        }

    return resultados


def analizar_frescura(datos: list[dict], col_año: str | None) -> dict[str, Any]:
    """
    Análisis 4: Frescura del catálogo por año y género.
    Alerta si >80% de tracks son anteriores a 2024.
    """
    resultados: dict[str, Any] = {}

    if not col_año:
        return {"error": "No se encontró columna de año en el CSV"}

    for genero in GENEROS_OBJETIVO:
        tracks = [
            r for r in datos
            if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()
        ]

        años = []
        for t in tracks:
            a = parsear_año(t.get(col_año))
            if a:
                años.append(a)

        total_con_año = len(años)
        conteo_años: Counter = Counter(años)

        # Tracks recientes vs antiguos
        t_2026 = sum(1 for a in años if a >= 2026)
        t_2025 = sum(1 for a in años if a == 2025)
        t_2024 = sum(1 for a in años if a == 2024)
        t_antiguos = sum(1 for a in años if a < 2024)

        pct_antiguos = (t_antiguos / total_con_año * 100) if total_con_año > 0 else 0

        alertas = []
        if total_con_año > 0 and pct_antiguos > 80:
            alertas.append(f"🔴 Catálogo envejecido: {pct_antiguos:.0f}% anterior a 2024")
        if t_2025 == 0 and t_2026 == 0 and len(tracks) > 0:
            alertas.append("🟡 Sin tracks de 2025-2026")
        if total_con_año == 0 and len(tracks) > 0:
            alertas.append("⚠️ Sin datos de año")

        resultados[genero] = {
            "total_con_año": total_con_año,
            "2026": t_2026,
            "2025": t_2025,
            "2024": t_2024,
            "anteriores": t_antiguos,
            "pct_antiguos": round(pct_antiguos, 1),
            "desglose_años": dict(sorted(conteo_años.items(), reverse=True)),
            "alertas": alertas,
        }

    return resultados


def analizar_versiones(datos: list[dict]) -> dict[str, Any]:
    """
    Análisis 5: Cobertura de versiones para contenido.
    Revisa disponibilidad de INTRO, MASHUP y TRANSITION por género.
    """
    resultados: dict[str, Any] = {}

    for genero in GENEROS_OBJETIVO:
        tracks = [
            r for r in datos
            if (r.get("genre_carpeta") or "").strip().lower() == genero.lower()
        ]

        total = len(tracks)
        version_counts: Counter = Counter()
        for t in tracks:
            v = (t.get("version_tipo") or "").strip().upper()
            if v:
                version_counts[v] += 1

        # Verificaciones clave para contenido
        intros = version_counts.get("INTRO", 0) + version_counts.get("INTRO-OUTRO", 0)
        mashups = version_counts.get("MASHUP", 0)
        transitions = version_counts.get("TRANSITION", 0)
        extendeds = version_counts.get("EXTENDED", 0)

        alertas = []
        if total > 0:
            pct_intro = intros / total * 100
            if intros == 0:
                alertas.append("🔴 Sin versiones INTRO — esencial para mezcla pro")
            elif pct_intro < 20:
                alertas.append(f"🟡 Pocas versiones INTRO: {intros} ({pct_intro:.0f}%)")
            if mashups == 0:
                alertas.append("🟡 Sin MASHUP — útil para reels")
            if transitions == 0:
                alertas.append("🟡 Sin TRANSITION — útil para sets multi-género")

        resultados[genero] = {
            "total": total,
            "intros": intros,
            "mashups": mashups,
            "transitions": transitions,
            "extendeds": extendeds,
            "desglose": dict(version_counts.most_common()),
            "alertas": alertas,
        }

    return resultados


def generar_lista_compras(
    cobertura: dict[str, Any],
    bpm_data: dict[str, Any],
    frescura: dict[str, Any],
    versiones: dict[str, Any],
) -> dict[str, Any]:
    """
    Análisis 6: Lista de compras recomendada.
    Estima cuántos tracks necesitamos por categoría.
    """
    compras: dict[str, Any] = {
        "generos_nuevos": {},
        "generos_debiles": {},
        "brechas_trending": {},
        "resumen_total": 0,
    }

    # --- Géneros nuevos: necesitan mínimo MINIMO_SET_VIABLE tracks ---
    generos_nuevos_especificos = {
        "Cumbia": "Cumbia Argentina / RKT",
        "FUNK NV": "Funk Brasileiro",
    }

    for genero in GENEROS_EXPANDIR:
        info = cobertura.get(genero, {})
        actual = info.get("unicos", 0)
        if actual < MINIMO_SET_VIABLE:
            faltan = MINIMO_SET_VIABLE - actual
            nombre_display = generos_nuevos_especificos.get(genero, genero)
            compras["generos_nuevos"][genero] = {
                "nombre_display": nombre_display,
                "tiene": actual,
                "necesita": MINIMO_SET_VIABLE,
                "faltan": faltan,
                "prioridad": "ALTA" if actual < 20 else "MEDIA",
            }
            compras["resumen_total"] += faltan

    # --- Géneros débiles: actuales con pocos tracks ---
    umbrales_minimos = {
        "Reggaeton":          300,
        "Bachata":            300,
        "SALSA":              200,
        "Merengue":           200,
        "Hip Hop Night Club": 200,
        "RnB":                150,
    }

    for genero in GENEROS_ACTUALES:
        info = cobertura.get(genero, {})
        actual = info.get("unicos", 0)
        umbral = umbrales_minimos.get(genero, 150)
        if actual < umbral:
            faltan = umbral - actual
            compras["generos_debiles"][genero] = {
                "tiene": actual,
                "objetivo": umbral,
                "faltan": faltan,
                "prioridad": "ALTA" if actual < umbral * 0.5 else "MEDIA",
            }
            compras["resumen_total"] += faltan

    # --- Brechas trending: géneros sin tracks 2025-2026 ---
    for genero in GENEROS_OBJETIVO:
        info_fresca = frescura.get(genero, {})
        if isinstance(info_fresca, str):
            continue
        t_2025 = info_fresca.get("2025", 0)
        t_2026 = info_fresca.get("2026", 0)
        total_genero = cobertura.get(genero, {}).get("total", 0)
        if total_genero > 0 and t_2025 == 0 and t_2026 == 0:
            compras["brechas_trending"][genero] = {
                "tracks_totales": total_genero,
                "tracks_recientes": 0,
                "recomendacion": "Buscar al menos 10-20 tracks de 2025-2026",
            }

    return compras


# ─── Impresión del reporte en consola ─────────────────────────────────────────

def imprimir_reporte(
    cobertura: dict,
    bpm_data: dict,
    energia: dict,
    frescura: dict,
    versiones: dict,
    compras: dict,
    ruta_csv: Path,
) -> None:
    """Imprime el reporte completo formateado en consola."""

    print(titulo_seccion("ANÁLISIS DE BRECHAS — BIBLIOTECA DJ", "🎧"))
    print(f"  📂 Fuente: {ruta_csv}")
    total_global = sum(g.get("total", 0) for g in cobertura.values())
    unicos_global = sum(g.get("unicos", 0) for g in cobertura.values())
    print(f"  🎵 Tracks en géneros objetivo: {total_global:,} ({unicos_global:,} únicos)")

    # ── 1. Cobertura de Géneros ──────────────────────────────────────────────
    print(titulo_seccion("1. COBERTURA DE GÉNEROS", "📁"))

    # Tabla de géneros actuales
    print(subtitulo("Géneros Actuales (Core)", "🟢"))
    print(f"  {'Género':<22} {'Total':>6} {'Únicos':>7} {'BPM':>5} {'Energy':>7} {'Dupl':>5}")
    print(f"  {linea_simple(58)}")
    for genero in GENEROS_ACTUALES:
        g = cobertura.get(genero, {})
        print(
            f"  {genero:<22} {g.get('total',0):>6,} {g.get('unicos',0):>7,}"
            f" {g.get('con_bpm',0):>5,} {g.get('con_energia',0):>7,}"
            f" {g.get('duplicados',0):>5,}"
        )

    # Tabla de géneros a expandir
    print(subtitulo("Géneros a Expandir / Nuevos", "🟡"))
    print(f"  {'Género':<22} {'Total':>6} {'Únicos':>7} {'BPM':>5} {'Energy':>7} {'Dupl':>5}")
    print(f"  {linea_simple(58)}")
    for genero in GENEROS_EXPANDIR:
        g = cobertura.get(genero, {})
        indicador = "🔴" if g.get("total", 0) < 20 else ("🟡" if g.get("total", 0) < MINIMO_SET_VIABLE else "🟢")
        print(
            f"  {indicador} {genero:<19} {g.get('total',0):>6,} {g.get('unicos',0):>7,}"
            f" {g.get('con_bpm',0):>5,} {g.get('con_energia',0):>7,}"
            f" {g.get('duplicados',0):>5,}"
        )

    # ── 2. BPM ──────────────────────────────────────────────────────────────
    print(titulo_seccion("2. ANÁLISIS DE BPM POR GÉNERO", "🥁"))

    for genero in GENEROS_OBJETIVO:
        info = bpm_data.get(genero, {})
        total_bpm = info.get("total_con_bpm", 0)
        if total_bpm == 0:
            print(f"\n  ⚠️  {genero}: Sin datos de BPM")
            continue

        sweet = info.get("sweet_spot")
        sweet_label = f"{sweet[0]}-{sweet[1]}" if sweet else "N/A"

        print(subtitulo(
            f"{genero}  (Rango: {info['bpm_min']}-{info['bpm_max']} | "
            f"Media: {info['bpm_media']} | Sweet: {sweet_label})", "🎯"
        ))

        # Distribución en buckets
        dist = info.get("distribucion", {})
        max_count = max(dist.values()) if dist else 1
        for bucket in sorted(dist.keys()):
            count = dist[bucket]
            rango_str = f"{bucket:>3}-{bucket+4:<3}"
            bar = barra_horizontal(count, max_count, 25)

            # Marcar si está en sweet spot
            en_sweet = ""
            if sweet and sweet[0] <= bucket + 2 <= sweet[1]:
                en_sweet = " ★"

            print(f"    {rango_str} BPM │{bar}│ {count:>4}{en_sweet}")

        # Alerta de sweet spot
        if info.get("alerta"):
            print(f"\n    {info['alerta']}")
        else:
            pct = info.get("sweet_spot_porcentaje", 0)
            cnt = info.get("sweet_spot_count", 0)
            if sweet:
                print(f"    ✅ Sweet spot OK: {cnt} tracks ({pct:.1f}%)")

    # ── 3. Energía ──────────────────────────────────────────────────────────
    print(titulo_seccion("3. DISTRIBUCIÓN DE ENERGÍA", "⚡"))

    for genero in GENEROS_OBJETIVO:
        info = energia.get(genero, {})
        total_e = info.get("total_con_energia", 0)
        if total_e == 0:
            continue

        dist = info.get("distribucion", {})
        max_count = max(dist.values()) if dist else 1

        baja = info.get("baja_1_4", 0)
        media_e = info.get("media_5_7", 0)
        alta = info.get("alta_8_10", 0)

        print(subtitulo(
            f"{genero}  (Baja: {baja} | Media: {media_e} | Alta: {alta})",
            "🔋"
        ))

        for nivel in range(1, 11):
            count = dist.get(nivel, 0)
            bar = barra_horizontal(count, max_count, 20)
            # Color semántico
            if nivel <= 4:
                icono = "🟦"
            elif nivel <= 7:
                icono = "🟩"
            else:
                icono = "🟥"
            print(f"    {icono} E{nivel:>2} │{bar}│ {count:>4}")

        for alerta in info.get("alertas", []):
            print(f"    {alerta}")

    # ── 4. Frescura ─────────────────────────────────────────────────────────
    print(titulo_seccion("4. FRESCURA DEL CATÁLOGO", "📅"))

    if isinstance(frescura, dict) and "error" in frescura:
        print(f"  ⚠️  {frescura['error']}")
    else:
        print(f"\n  {'Género':<22} {'2026':>6} {'2025':>6} {'2024':>6} {'<2024':>6} {'%Ant':>6}  Estado")
        print(f"  {linea_simple(68)}")

        for genero in GENEROS_OBJETIVO:
            info = frescura.get(genero, {})
            if isinstance(info, str):
                continue
            total_a = info.get("total_con_año", 0)
            if total_a == 0 and cobertura.get(genero, {}).get("total", 0) == 0:
                continue

            t26 = info.get("2026", 0)
            t25 = info.get("2025", 0)
            t24 = info.get("2024", 0)
            ant = info.get("anteriores", 0)
            pct = info.get("pct_antiguos", 0)

            if pct > 80:
                estado = "🔴 Envejecido"
            elif t25 + t26 == 0:
                estado = "🟡 Sin recientes"
            else:
                estado = "🟢 OK"

            print(
                f"  {genero:<22} {t26:>6} {t25:>6} {t24:>6} {ant:>6}"
                f" {pct:>5.1f}%  {estado}"
            )

        # Alertas destacadas
        alertas_frescura = []
        for genero in GENEROS_OBJETIVO:
            info = frescura.get(genero, {})
            if isinstance(info, dict):
                for a in info.get("alertas", []):
                    alertas_frescura.append(f"  {genero}: {a}")
        if alertas_frescura:
            print(f"\n  {'Alertas de frescura:':}")
            for a in alertas_frescura[:15]:  # Limitar a 15
                print(f"    {a}")

    # ── 5. Versiones ────────────────────────────────────────────────────────
    print(titulo_seccion("5. COBERTURA DE VERSIONES PARA CONTENIDO", "🔀"))

    print(f"\n  {'Género':<22} {'INTRO':>6} {'MASHUP':>7} {'TRANS':>6} {'EXTEND':>7} {'Total':>6}")
    print(f"  {linea_simple(60)}")

    for genero in GENEROS_OBJETIVO:
        info = versiones.get(genero, {})
        total_v = info.get("total", 0)
        if total_v == 0:
            continue
        print(
            f"  {genero:<22} {info.get('intros',0):>6}"
            f" {info.get('mashups',0):>7}"
            f" {info.get('transitions',0):>6}"
            f" {info.get('extendeds',0):>7}"
            f" {total_v:>6}"
        )

    # Alertas de versiones
    print()
    for genero in GENEROS_OBJETIVO:
        info = versiones.get(genero, {})
        for a in info.get("alertas", []):
            print(f"  {genero}: {a}")

    # ── 6. Lista de compras ─────────────────────────────────────────────────
    print(titulo_seccion("6. 🛒 LISTA DE COMPRAS RECOMENDADA", "💰"))

    # Géneros nuevos
    if compras.get("generos_nuevos"):
        print(subtitulo("Géneros Nuevos (necesitan base mínima)", "🆕"))
        for genero, info in compras["generos_nuevos"].items():
            prio = "🔴" if info["prioridad"] == "ALTA" else "🟡"
            print(
                f"  {prio} {info['nombre_display']:<25} "
                f"Tiene: {info['tiene']:>4} | Necesita: {info['necesita']:>4} | "
                f"Faltan: {info['faltan']:>4}"
            )

    # Géneros débiles
    if compras.get("generos_debiles"):
        print(subtitulo("Géneros Débiles (necesitan refuerzo)", "📉"))
        for genero, info in compras["generos_debiles"].items():
            prio = "🔴" if info["prioridad"] == "ALTA" else "🟡"
            print(
                f"  {prio} {genero:<25} "
                f"Tiene: {info['tiene']:>4} | Objetivo: {info['objetivo']:>4} | "
                f"Faltan: {info['faltan']:>4}"
            )

    # Brechas trending
    if compras.get("brechas_trending"):
        print(subtitulo("Sin Tracks Recientes (2025-2026)", "📆"))
        for genero, info in compras["brechas_trending"].items():
            print(
                f"  🟡 {genero:<25} "
                f"({info['tracks_totales']} tracks, ninguno reciente)"
            )
            print(f"     ➜ {info['recomendacion']}")

    # Resumen total
    print(f"\n  {'═' * 60}")
    print(f"  📦 TOTAL ESTIMADO DE TRACKS A ADQUIRIR: {compras['resumen_total']:,}")
    print(f"  {'═' * 60}")


# ─── Guardar reporte JSON ────────────────────────────────────────────────────

def guardar_json(
    ruta_json: Path,
    cobertura: dict,
    bpm_data: dict,
    energia: dict,
    frescura: dict,
    versiones: dict,
    compras: dict,
) -> None:
    """Guarda el reporte completo como JSON."""
    reporte = {
        "meta": {
            "descripcion": "Reporte de análisis de brechas — Biblioteca DJ",
            "generado_por": "gap_analyzer.py",
        },
        "1_cobertura_generos": cobertura,
        "2_analisis_bpm": _serializar_bpm(bpm_data),
        "3_distribucion_energia": energia,
        "4_frescura_catalogo": frescura,
        "5_cobertura_versiones": versiones,
        "6_lista_compras": compras,
    }

    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Reporte JSON guardado en: {ruta_json}")


def _serializar_bpm(bpm_data: dict) -> dict:
    """Convierte tuplas de sweet_spot a listas para serialización JSON."""
    resultado = {}
    for genero, info in bpm_data.items():
        copia = dict(info)
        sweet = copia.get("sweet_spot")
        if isinstance(sweet, tuple):
            copia["sweet_spot"] = list(sweet)
        resultado[genero] = copia
    return resultado


# ─── Punto de entrada ────────────────────────────────────────────────────────

def main() -> None:
    """Punto de entrada principal del analizador de brechas."""
    parser = argparse.ArgumentParser(
        description="🎧 Analizador de brechas para la biblioteca musical DJ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python gap_analyzer.py\n"
            "  python gap_analyzer.py --csv ruta/biblioteca.csv\n"
            "  python gap_analyzer.py --output mi_reporte.json\n"
            "  python gap_analyzer.py --dry-run\n"
        ),
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(r"D:\DJ\analisis\biblioteca_v3.csv"),
        help="Ruta al CSV de la biblioteca (default: D:\\DJ\\analisis\\biblioteca_v3.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta para el reporte JSON (default: gap_report.json junto al script)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo imprimir en consola, no guardar JSON",
    )

    args = parser.parse_args()

    # Ruta de salida por defecto: junto al script
    ruta_json = args.output or Path(__file__).parent / "gap_report.json"

    # ── Leer CSV ─────────────────────────────────────────────────────────────
    print(titulo_seccion("CARGANDO BIBLIOTECA", "📂"))
    datos = leer_csv(args.csv)

    # Detectar columnas especiales
    primera_fila = datos[0] if datos else {}
    col_tamaño = detectar_columna_tamaño(primera_fila)
    col_año = detectar_columna_año(primera_fila)
    print(f"  📏 Columna de tamaño detectada: {col_tamaño or '❌ No encontrada'}")
    print(f"  📅 Columna de año detectada: {col_año or '❌ No encontrada'}")

    # ── Ejecutar análisis ────────────────────────────────────────────────────
    print(f"\n  🔍 Ejecutando análisis de brechas...")

    cobertura = analizar_cobertura_generos(datos, col_año)
    bpm_data = analizar_bpm(datos)
    energia_data = analizar_energia(datos)
    frescura_data = analizar_frescura(datos, col_año)
    versiones_data = analizar_versiones(datos)
    compras_data = generar_lista_compras(
        cobertura, bpm_data, frescura_data, versiones_data
    )

    # ── Imprimir reporte ─────────────────────────────────────────────────────
    imprimir_reporte(
        cobertura, bpm_data, energia_data,
        frescura_data, versiones_data, compras_data,
        args.csv,
    )

    # ── Guardar JSON ─────────────────────────────────────────────────────────
    if not args.dry_run:
        guardar_json(
            ruta_json, cobertura, bpm_data, energia_data,
            frescura_data, versiones_data, compras_data,
        )

    print(f"\n  ✅ Análisis completado.")


if __name__ == "__main__":
    main()
