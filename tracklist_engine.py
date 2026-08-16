#!/usr/bin/env python3
"""
tracklist_engine.py — Motor principal del sistema de contenido DJ.

Lee la biblioteca musical (CSV) y genera paletas creativas expandidas
para sets de YouTube, reels de Instagram y sets crossover multi-género.

Filosofía: Somos el SOUS-CHEF, no el chef. Proporcionamos una paleta
EXPANDIDA con MÁS tracks de los necesarios. El DJ decide qué tocar.

Uso:
    python tracklist_engine.py set --genre Reggaeton --duration 50 --vibra perreo
    python tracklist_engine.py reel --genre Reggaeton --count 8
    python tracklist_engine.py crossover --genres "Hip Hop Night Club,Reggaeton" --duration 40
"""

import argparse
import io
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Fix encoding para Windows (cp1252 no soporta emoji/unicode)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

# ─── Configuración por defecto ───────────────────────────────────────────────
CSV_POR_DEFECTO = Path(r"D:\DJ\analisis\biblioteca_v3.csv")
DIRECTORIO_SALIDA = Path(__file__).parent / "paletas"
AÑO_ACTUAL = datetime.now().year

# ─── Colores ANSI para consola ───────────────────────────────────────────────
class Color:
    """Códigos ANSI para output bonito en consola."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ROJO = "\033[91m"
    VERDE = "\033[92m"
    AMARILLO = "\033[93m"
    AZUL = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BLANCO = "\033[97m"
    GRIS = "\033[90m"
    BG_VERDE = "\033[42m"
    BG_AMARILLO = "\033[43m"
    BG_ROJO = "\033[41m"
    BG_AZUL = "\033[44m"
    BG_MAGENTA = "\033[45m"


# ═══════════════════════════════════════════════════════════════════════════════
#  RUEDA DE CAMELOT — Sistema de compatibilidad armónica
# ═══════════════════════════════════════════════════════════════════════════════

# Mapeo completo de la rueda de Camelot
# Cada posición tiene: número (1-12) y modo (A=menor, B=mayor)
CAMELOT_VALIDOS = set()
for num in range(1, 13):
    CAMELOT_VALIDOS.add(f"{num}A")
    CAMELOT_VALIDOS.add(f"{num}B")


def parsear_camelot(key: str) -> Optional[tuple[int, str]]:
    """
    Parsea una clave Camelot como '8A' → (8, 'A').

    Args:
        key: Clave en notación Camelot (ej: '3A', '12B')

    Returns:
        Tupla (número, modo) o None si no es válida
    """
    if not key or not isinstance(key, str):
        return None
    key = key.strip().upper()
    if key not in CAMELOT_VALIDOS:
        return None
    # Separar número y letra
    modo = key[-1]
    numero = int(key[:-1])
    return (numero, modo)


def son_compatibles(key1: str, key2: str) -> bool:
    """
    Determina si dos claves Camelot son compatibles para mezcla armónica.

    Reglas de compatibilidad:
    - Misma clave = match perfecto (8A → 8A)
    - ±1 en número, mismo modo = compatible (8A → 7A o 9A)
    - Mismo número, cambio A↔B = compatible (8A → 8B)

    Args:
        key1: Primera clave Camelot
        key2: Segunda clave Camelot

    Returns:
        True si son compatibles para mezcla armónica
    """
    p1 = parsear_camelot(key1)
    p2 = parsear_camelot(key2)
    if not p1 or not p2:
        return False

    num1, modo1 = p1
    num2, modo2 = p2

    # Misma clave exacta
    if num1 == num2 and modo1 == modo2:
        return True

    # ±1 en número (circular: 12→1 y 1→12), mismo modo
    if modo1 == modo2:
        diff = abs(num1 - num2)
        if diff == 1 or diff == 11:  # 11 = vuelta circular (1↔12)
            return True

    # Mismo número, cambio de modo A↔B
    if num1 == num2 and modo1 != modo2:
        return True

    return False


def puntaje_compatibilidad(key1: str, key2: str) -> float:
    """
    Calcula un puntaje de compatibilidad armónica entre dos claves.

    Puntajes:
    - 1.0 = misma clave exacta (match perfecto)
    - 0.8 = ±1 en número, mismo modo (muy compatible)
    - 0.7 = mismo número, cambio A↔B (compatible)
    - 0.4 = ±2 en número, mismo modo (aceptable con cuidado)
    - 0.0 = incompatible

    Args:
        key1: Primera clave Camelot
        key2: Segunda clave Camelot

    Returns:
        Puntaje de 0.0 a 1.0
    """
    p1 = parsear_camelot(key1)
    p2 = parsear_camelot(key2)
    if not p1 or not p2:
        return 0.0

    num1, modo1 = p1
    num2, modo2 = p2

    # Diferencia circular en el número
    diff = abs(num1 - num2)
    diff_circular = min(diff, 12 - diff)

    # Misma clave exacta
    if diff_circular == 0 and modo1 == modo2:
        return 1.0

    # Mismo número, cambio de modo
    if diff_circular == 0 and modo1 != modo2:
        return 0.7

    # ±1, mismo modo
    if diff_circular == 1 and modo1 == modo2:
        return 0.8

    # ±1, diferente modo
    if diff_circular == 1 and modo1 != modo2:
        return 0.5

    # ±2, mismo modo (aceptable con cuidado)
    if diff_circular == 2 and modo1 == modo2:
        return 0.4

    # ±2, diferente modo
    if diff_circular == 2 and modo1 != modo2:
        return 0.3

    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

def cargar_biblioteca(ruta_csv: Path) -> pd.DataFrame:
    """
    Carga la biblioteca musical desde CSV con manejo robusto de encoding.

    Intenta UTF-8 primero, luego latin-1 como fallback.
    Limpia valores NaN y filtra duplicados no conservados.

    Args:
        ruta_csv: Ruta al archivo CSV de la biblioteca

    Returns:
        DataFrame limpio y filtrado
    """
    if not ruta_csv.exists():
        print(f"{Color.ROJO}❌ Error: No se encontró el archivo CSV: {ruta_csv}{Color.RESET}")
        sys.exit(1)

    # Intentar UTF-8 primero, luego latin-1
    df = None
    for encoding in ["utf-8", "latin-1"]:
        try:
            df = pd.read_csv(ruta_csv, encoding=encoding, low_memory=False)
            print(f"{Color.DIM}📂 Biblioteca cargada con encoding: {encoding}{Color.RESET}")
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        print(f"{Color.ROJO}❌ Error: No se pudo leer el CSV con ningún encoding{Color.RESET}")
        sys.exit(1)

    # ─── Limpieza de valores numéricos ────────────────────────────────────
    for col in ["bpm_mik", "energy_mik", "popularidad"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ─── Limpiar columnas de texto ────────────────────────────────────────
    for col in ["titulo_limpio", "artista_limpio", "genre_carpeta", "key_mik",
                 "version_tipo", "es_duplicado", "conservar"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    # ─── Columna de año (puede venir como float por NaN) ─────────────────
    if "año_spotify" in df.columns:
        df["año_spotify"] = pd.to_numeric(df["año_spotify"], errors="coerce")

    # ─── Filtrar duplicados no conservados ────────────────────────────────
    # Mantener tracks donde: no es duplicado O está marcado para conservar
    mask_mantener = (df["es_duplicado"].str.lower() != "true") | \
                    (df["conservar"].str.lower() == "true")
    total_antes = len(df)
    df = df[mask_mantener].copy()
    eliminados = total_antes - len(df)
    if eliminados > 0:
        print(f"{Color.DIM}🗑️  Filtrados {eliminados} duplicados no conservados{Color.RESET}")

    print(f"{Color.VERDE}✅ {len(df)} tracks disponibles en la biblioteca{Color.RESET}")
    return df


def filtrar_por_genero(df: pd.DataFrame, genero: str) -> pd.DataFrame:
    """
    Filtra el DataFrame por género (case-insensitive, match parcial).

    Args:
        df: DataFrame de la biblioteca
        genero: Nombre del género a filtrar

    Returns:
        DataFrame filtrado por género
    """
    mask = df["genre_carpeta"].str.lower().str.contains(genero.lower(), na=False)
    resultado = df[mask].copy()
    if resultado.empty:
        generos_disponibles = df["genre_carpeta"].unique()
        print(f"\n{Color.AMARILLO}⚠️  No se encontraron tracks para género '{genero}'{Color.RESET}")
        print(f"{Color.DIM}   Géneros disponibles: {', '.join(sorted(set(generos_disponibles)))}{Color.RESET}")
    return resultado


# ═══════════════════════════════════════════════════════════════════════════════
#  UTILIDADES DE SELECCIÓN Y SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def calcular_score_track(row: pd.Series, preferencias: dict = None) -> float:
    """
    Calcula un puntaje compuesto para un track basado en múltiples factores.

    Args:
        row: Fila del DataFrame (un track)
        preferencias: Dict con pesos opcionales

    Returns:
        Puntaje de 0 a 100
    """
    prefs = preferencias or {}
    score = 0.0

    # Popularidad (0-100) — peso 30%
    pop = row.get("popularidad", 0)
    if pd.notna(pop):
        score += float(pop) * 0.30

    # Energía (1-10) — peso 20%
    energy = row.get("energy_mik", 5)
    if pd.notna(energy):
        score += (float(energy) / 10) * 100 * 0.20

    # Trending bonus — año reciente (peso 20%)
    año = row.get("año_spotify", 0)
    if pd.notna(año) and año >= AÑO_ACTUAL:
        score += 20.0
    elif pd.notna(año) and año >= AÑO_ACTUAL - 1:
        score += 12.0
    elif pd.notna(año) and año >= AÑO_ACTUAL - 2:
        score += 6.0

    # Versión preferida — peso 15%
    version = str(row.get("version_tipo", "")).upper()
    versiones_preferidas = prefs.get("versiones_preferidas", ["FULL", "EXTENDED", "CLEAN"])
    if version in [v.upper() for v in versiones_preferidas]:
        score += 15.0

    # BPM en rango deseado — peso 15%
    bpm = row.get("bpm_mik", 0)
    bpm_objetivo = prefs.get("bpm_objetivo", None)
    if pd.notna(bpm) and bpm_objetivo:
        diff_bpm = abs(float(bpm) - bpm_objetivo)
        if diff_bpm <= 3:
            score += 15.0
        elif diff_bpm <= 8:
            score += 10.0
        elif diff_bpm <= 15:
            score += 5.0

    return min(score, 100.0)


def es_trending(row: pd.Series) -> bool:
    """Determina si un track es trending (año >= año actual)."""
    año = row.get("año_spotify", 0)
    return pd.notna(año) and año >= AÑO_ACTUAL


def obtener_etiqueta_trending(row: pd.Series) -> str:
    """Genera etiqueta de trending si aplica."""
    año = row.get("año_spotify", 0)
    if pd.notna(año) and año >= AÑO_ACTUAL:
        return f" {Color.MAGENTA}[🔥 TRENDING {int(año)}]{Color.RESET}"
    elif pd.notna(año) and año >= AÑO_ACTUAL - 1:
        return f" {Color.CYAN}[📈 RECIENTE {int(año)}]{Color.RESET}"
    return ""


def formatear_track(row: pd.Series, indice: int = 0, mostrar_compat: str = "") -> str:
    """
    Formatea un track para visualización en consola.

    Args:
        row: Fila del DataFrame
        indice: Número de orden
        mostrar_compat: Indicador de compatibilidad con track anterior

    Returns:
        String formateado para consola
    """
    titulo = str(row.get("titulo_limpio", "???"))[:40]
    artista = str(row.get("artista_limpio", "???"))[:25]
    bpm = row.get("bpm_mik", 0)
    key = str(row.get("key_mik", "?"))
    energy = row.get("energy_mik", 0)
    version = str(row.get("version_tipo", "?"))[:12]
    pop = row.get("popularidad", 0)

    # Formatear valores numéricos con manejo de NaN
    bpm_str = f"{float(bpm):.0f}" if pd.notna(bpm) and bpm else "---"
    energy_str = f"{float(energy):.0f}" if pd.notna(energy) and energy else "-"
    pop_str = f"{float(pop):.0f}" if pd.notna(pop) and pop else "--"

    # Barra visual de energía
    energy_val = float(energy) if pd.notna(energy) else 0
    barra = "█" * int(energy_val) + "░" * (10 - int(energy_val))

    # Color de energía
    if energy_val >= 7:
        energy_color = Color.ROJO
    elif energy_val >= 5:
        energy_color = Color.AMARILLO
    else:
        energy_color = Color.VERDE

    # Indicador de trending
    trending = obtener_etiqueta_trending(row)

    # Compatibilidad armónica
    compat_str = f" {Color.VERDE}🔗{Color.RESET}" if mostrar_compat else ""

    linea = (
        f"  {Color.DIM}{indice:>2}.{Color.RESET} "
        f"{Color.BOLD}{titulo:<40}{Color.RESET} "
        f"{Color.GRIS}│{Color.RESET} {artista:<25} "
        f"{Color.GRIS}│{Color.RESET} {Color.CYAN}{bpm_str:>3} BPM{Color.RESET} "
        f"{Color.GRIS}│{Color.RESET} {Color.AMARILLO}{key:>3}{Color.RESET} "
        f"{Color.GRIS}│{Color.RESET} {energy_color}{barra} {energy_str:>2}{Color.RESET} "
        f"{Color.GRIS}│{Color.RESET} {version:<12} "
        f"{Color.GRIS}│{Color.RESET} ⭐{pop_str:>3}"
        f"{trending}{compat_str}"
    )
    return linea


def imprimir_encabezado_bloque(emoji: str, nombre: str, color: str,
                                descripcion: str = "", cantidad: int = 0):
    """Imprime un encabezado visual para un bloque de tracks."""
    ancho = 130
    print()
    print(f"  {color}{'─' * ancho}{Color.RESET}")
    cant_str = f" ({cantidad} opciones)" if cantidad else ""
    print(f"  {emoji} {color}{Color.BOLD}{nombre}{Color.RESET}{cant_str}")
    if descripcion:
        print(f"     {Color.DIM}{descripcion}{Color.RESET}")
    print(f"  {color}{'─' * ancho}{Color.RESET}")
    # Encabezado de columnas
    print(
        f"  {Color.DIM}     {'TÍTULO':<40} │ {'ARTISTA':<25} "
        f"│ {'BPM':>7} │ {'KEY':>3} "
        f"│ {'ENERGÍA':>14} │ {'VERSIÓN':<12} "
        f"│ {'POP':>4}{Color.RESET}"
    )
    print(f"  {Color.DIM}{'─' * ancho}{Color.RESET}")


def seleccionar_tracks_bloque(df: pd.DataFrame,
                               energia_min: float, energia_max: float,
                               cantidad: int,
                               versiones_pref: list = None,
                               priorizar_popular: bool = False,
                               priorizar_trending: bool = False,
                               excluir_indices: set = None) -> pd.DataFrame:
    """
    Selecciona tracks para un bloque según criterios de energía y preferencias.

    Args:
        df: DataFrame fuente (ya filtrado por género)
        energia_min: Energía mínima del bloque
        energia_max: Energía máxima del bloque
        cantidad: Número de tracks a seleccionar
        versiones_pref: Versiones preferidas (ej: ['STARTER', 'INTRO'])
        priorizar_popular: Si True, ordena por popularidad
        priorizar_trending: Si True, prioriza tracks recientes
        excluir_indices: Índices a excluir (ya usados en otros bloques)

    Returns:
        DataFrame con los tracks seleccionados
    """
    excluir = excluir_indices or set()
    candidatos = df[~df.index.isin(excluir)].copy()

    # Filtrar por rango de energía (con tolerancia si hay pocos tracks)
    mask_energia = (
        (candidatos["energy_mik"] >= energia_min) &
        (candidatos["energy_mik"] <= energia_max)
    ) | candidatos["energy_mik"].isna()

    filtrados = candidatos[mask_energia].copy()

    # Si hay muy pocos, relajar el filtro de energía
    if len(filtrados) < cantidad:
        tolerancia = 2
        mask_relajada = (
            (candidatos["energy_mik"] >= energia_min - tolerancia) &
            (candidatos["energy_mik"] <= energia_max + tolerancia)
        ) | candidatos["energy_mik"].isna()
        filtrados = candidatos[mask_relajada].copy()

    # Si aún hay muy pocos, usar todos los candidatos disponibles
    if len(filtrados) < max(cantidad // 2, 2):
        filtrados = candidatos.copy()

    # Filtrar versiones preferidas si se especifican
    if versiones_pref and not filtrados.empty:
        mask_version = filtrados["version_tipo"].str.upper().isin(
            [v.upper() for v in versiones_pref]
        )
        con_version = filtrados[mask_version]
        sin_version = filtrados[~mask_version]
        # Tomar preferidas primero, luego completar con otras
        if len(con_version) >= cantidad:
            filtrados = con_version
        else:
            filtrados = pd.concat([con_version, sin_version])

    # Calcular score para cada track
    filtrados["_score"] = filtrados.apply(
        lambda r: calcular_score_track(r), axis=1
    )

    # Ajustar score según prioridades
    if priorizar_popular:
        filtrados["_score"] = filtrados["_score"] + \
            filtrados["popularidad"].fillna(0) * 0.5
    if priorizar_trending:
        filtrados["_score"] = filtrados["_score"] + \
            filtrados.apply(lambda r: 30 if es_trending(r) else 0, axis=1)

    # Ordenar por score y tomar los mejores
    filtrados = filtrados.sort_values("_score", ascending=False)
    seleccion = filtrados.head(cantidad).copy()

    # Ordenar la selección final por BPM para facilitar mezcla
    seleccion = seleccion.sort_values("bpm_mik", na_position="last")

    # Limpiar columna temporal
    if "_score" in seleccion.columns:
        seleccion = seleccion.drop(columns=["_score"])

    return seleccion


def imprimir_bloque(tracks_df: pd.DataFrame, emoji: str, nombre: str,
                     color: str, descripcion: str = ""):
    """
    Imprime un bloque completo de tracks con formato visual.

    Incluye indicadores de compatibilidad armónica entre tracks consecutivos.
    """
    imprimir_encabezado_bloque(emoji, nombre, color, descripcion, len(tracks_df))

    key_anterior = None
    for i, (idx, row) in enumerate(tracks_df.iterrows(), 1):
        key_actual = str(row.get("key_mik", ""))
        compat = ""
        if key_anterior and key_actual:
            compat = son_compatibles(key_anterior, key_actual)
        print(formatear_track(row, i, compat))
        key_anterior = key_actual


# ═══════════════════════════════════════════════════════════════════════════════
#  MODO 1: SET — Paleta para YouTube Set
# ═══════════════════════════════════════════════════════════════════════════════

def generar_paleta_set(df: pd.DataFrame, genero: str, duracion: int,
                        vibra: str = "") -> dict:
    """
    Genera una paleta expandida para un set de YouTube.

    Proporciona más tracks de los necesarios, organizados en bloques
    de energía (INTRO → BUILD → PEAK → COOLDOWN + WILDCARDS).

    Args:
        df: DataFrame de la biblioteca completa
        genero: Género del set
        duracion: Duración en minutos
        vibra: Vibra/mood del set (perreo, chill, party, etc.)

    Returns:
        Dict con la paleta completa para JSON
    """
    # ─── Filtrar por género ───────────────────────────────────────────────
    df_genero = filtrar_por_genero(df, genero)
    if df_genero.empty:
        return {}

    # ─── Calcular cuántos tracks necesitamos por bloque ──────────────────
    # Regla: ~3-3.5 min por track promedio
    tracks_necesarios = max(int(duracion / 3.5), 4)

    # Paleta expandida: ~1.6x los tracks necesarios
    factor_expansion = 1.6
    total_paleta = int(tracks_necesarios * factor_expansion)

    # Distribución por bloques (proporcional)
    n_intro = max(3, int(total_paleta * 0.15))
    n_build = max(5, int(total_paleta * 0.25))
    n_peak = max(6, int(total_paleta * 0.35))
    n_cooldown = max(3, int(total_paleta * 0.15))
    n_wildcards = 3

    # ─── Encabezado ──────────────────────────────────────────────────────
    print()
    print(f"  {Color.BOLD}{Color.AZUL}╔{'═' * 128}╗{Color.RESET}")
    print(f"  {Color.BOLD}{Color.AZUL}║{Color.RESET} 🎧 "
          f"{Color.BOLD}PALETA DJ — SET DE YOUTUBE{Color.RESET}"
          f"{' ' * 95}{Color.AZUL}║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.AZUL}╠{'═' * 128}╣{Color.RESET}")
    print(f"  {Color.AZUL}║{Color.RESET} 🎵 Género: {Color.BOLD}{genero}{Color.RESET}"
          f"  │  ⏱️  Duración: {Color.BOLD}{duracion} min{Color.RESET}"
          f"  │  🎯 Tracks necesarios: ~{tracks_necesarios}"
          f"  │  📦 Paleta: {total_paleta + n_wildcards} opciones"
          f"{' ' * 5}{Color.AZUL}║{Color.RESET}")
    if vibra:
        print(f"  {Color.AZUL}║{Color.RESET} 🌊 Vibra: {Color.MAGENTA}{Color.BOLD}{vibra}{Color.RESET}"
              f"{' ' * (117 - len(vibra))}{Color.AZUL}║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.AZUL}╚{'═' * 128}╝{Color.RESET}")

    # Nota de filosofía
    print(f"\n  {Color.DIM}💡 Recuerda: esto es una PALETA expandida. "
          f"Tú decides el orden y qué tracks usar.{Color.RESET}")
    print(f"  {Color.DIM}   🔗 = compatible armónicamente con el track anterior{Color.RESET}")

    # ─── Índices usados para evitar repeticiones entre bloques ────────────
    usados = set()

    # ─── BLOQUE INTRO ────────────────────────────────────────────────────
    versiones_intro = ["STARTER", "OPEN SHOW", "INTRO", "INTRO-OUTRO"]
    tracks_intro = seleccionar_tracks_bloque(
        df_genero, energia_min=2, energia_max=5, cantidad=n_intro,
        versiones_pref=versiones_intro, excluir_indices=usados
    )
    usados.update(tracks_intro.index)
    imprimir_bloque(
        tracks_intro, "🟢", "INTRO — Calentamiento",
        Color.VERDE,
        f"Energía 3-5 · Versiones STARTER/INTRO preferidas · {n_intro} opciones"
    )

    # ─── BLOQUE BUILD ────────────────────────────────────────────────────
    tracks_build = seleccionar_tracks_bloque(
        df_genero, energia_min=5, energia_max=7, cantidad=n_build,
        excluir_indices=usados
    )
    usados.update(tracks_build.index)
    imprimir_bloque(
        tracks_build, "🟡", "BUILD — Subiendo la energía",
        Color.AMARILLO,
        f"Energía 5-7 · Progresión BPM/Key · {n_build} opciones"
    )

    # ─── BLOQUE PEAK ─────────────────────────────────────────────────────
    tracks_peak = seleccionar_tracks_bloque(
        df_genero, energia_min=7, energia_max=10, cantidad=n_peak,
        priorizar_popular=True, priorizar_trending=True,
        excluir_indices=usados
    )
    usados.update(tracks_peak.index)
    imprimir_bloque(
        tracks_peak, "🔴", "PEAK — Máximo impacto",
        Color.ROJO,
        f"Energía 7-10 · Hits populares & trending · {n_peak} opciones"
    )

    # ─── BLOQUE COOLDOWN ─────────────────────────────────────────────────
    tracks_cooldown = seleccionar_tracks_bloque(
        df_genero, energia_min=3, energia_max=6, cantidad=n_cooldown,
        excluir_indices=usados
    )
    usados.update(tracks_cooldown.index)
    imprimir_bloque(
        tracks_cooldown, "🔵", "COOLDOWN — Bajando la energía",
        Color.AZUL,
        f"Energía 4-6 · Cierre suave · {n_cooldown} opciones"
    )

    # ─── WILDCARDS ────────────────────────────────────────────────────────
    # Buscar en otros géneros: mashups, trending, sorpresas
    df_otros = df[~df.index.isin(usados)].copy()
    df_otros = df_otros[
        df_otros["genre_carpeta"].str.lower() != genero.lower()
    ]
    mask_wildcard = (
        (df_otros["version_tipo"].str.upper().isin(["MASHUP", "TRANSITION"])) |
        (df_otros.apply(es_trending, axis=1)) |
        (df_otros["popularidad"].fillna(0) >= 70)
    )
    wildcards = df_otros[mask_wildcard].copy()
    if wildcards.empty:
        wildcards = df_otros.copy()

    wildcards["_score"] = wildcards.apply(
        lambda r: calcular_score_track(r), axis=1
    )
    wildcards = wildcards.sort_values("_score", ascending=False).head(n_wildcards)
    if "_score" in wildcards.columns:
        wildcards = wildcards.drop(columns=["_score"])

    imprimir_bloque(
        wildcards, "🎯", "WILDCARDS — Sorpresas & crossover",
        Color.MAGENTA,
        f"Tracks de otros géneros, mashups, trending · {n_wildcards} opciones"
    )

    # ─── Resumen final ───────────────────────────────────────────────────
    total_mostrados = (len(tracks_intro) + len(tracks_build) +
                       len(tracks_peak) + len(tracks_cooldown) +
                       len(wildcards))
    print(f"\n  {Color.BOLD}📊 RESUMEN DE LA PALETA{Color.RESET}")
    print(f"  {'─' * 60}")
    print(f"  🟢 Intro:     {len(tracks_intro):>3} opciones")
    print(f"  🟡 Build:     {len(tracks_build):>3} opciones")
    print(f"  🔴 Peak:      {len(tracks_peak):>3} opciones")
    print(f"  🔵 Cooldown:  {len(tracks_cooldown):>3} opciones")
    print(f"  🎯 Wildcards: {len(wildcards):>3} opciones")
    print(f"  {'─' * 60}")
    print(f"  📦 Total:     {total_mostrados:>3} opciones (necesitas ~{tracks_necesarios})")
    print()

    # ─── Construir resultado JSON ─────────────────────────────────────────
    def tracks_a_lista(tracks_df, bloque_nombre):
        """Convierte un DataFrame de tracks a lista de dicts para JSON."""
        resultado = []
        for _, row in tracks_df.iterrows():
            resultado.append({
                "titulo": str(row.get("titulo_limpio", "")),
                "artista": str(row.get("artista_limpio", "")),
                "bpm": float(row["bpm_mik"]) if pd.notna(row.get("bpm_mik")) else None,
                "key": str(row.get("key_mik", "")),
                "energy": float(row["energy_mik"]) if pd.notna(row.get("energy_mik")) else None,
                "version": str(row.get("version_tipo", "")),
                "popularidad": float(row["popularidad"]) if pd.notna(row.get("popularidad")) else None,
                "trending": es_trending(row),
                "año": int(row["año_spotify"]) if pd.notna(row.get("año_spotify")) else None,
                "ruta": str(row.get("ruta_completa", "")),
                "bloque": bloque_nombre
            })
        return resultado

    # Lista de rutas para Serato
    todos_tracks = pd.concat([
        tracks_intro, tracks_build, tracks_peak, tracks_cooldown, wildcards
    ])
    serato_tracks = [
        str(row.get("ruta_completa", ""))
        for _, row in todos_tracks.iterrows()
        if str(row.get("ruta_completa", "")).strip()
    ]

    paleta = {
        "metadata": {
            "tipo": "set",
            "genero": genero,
            "duracion_min": duracion,
            "vibra": vibra,
            "tracks_necesarios": tracks_necesarios,
            "tracks_en_paleta": total_mostrados,
            "fecha_generacion": datetime.now().isoformat(),
        },
        "bloques": {
            "intro": tracks_a_lista(tracks_intro, "intro"),
            "build": tracks_a_lista(tracks_build, "build"),
            "peak": tracks_a_lista(tracks_peak, "peak"),
            "cooldown": tracks_a_lista(tracks_cooldown, "cooldown"),
            "wildcards": tracks_a_lista(wildcards, "wildcards"),
        },
        "serato_tracks": serato_tracks
    }

    return paleta


# ═══════════════════════════════════════════════════════════════════════════════
#  MODO 2: REEL — Opciones para Reels de Instagram
# ═══════════════════════════════════════════════════════════════════════════════

def generar_opciones_reel(df: pd.DataFrame, genero: str, count: int = 8) -> dict:
    """
    Genera opciones de tracks para reels de Instagram.

    Prioriza: alta energía, popularidad, año reciente, mashups.

    Args:
        df: DataFrame de la biblioteca
        genero: Género a filtrar
        count: Número de opciones a generar (5-8)

    Returns:
        Dict con las opciones para JSON
    """
    count = max(5, min(count, 15))
    df_genero = filtrar_por_genero(df, genero)
    if df_genero.empty:
        return {}

    # ─── Scoring para reels ──────────────────────────────────────────────
    candidatos = df_genero.copy()
    candidatos["_reel_score"] = 0.0

    # Energía alta (>= 7) → gran bonus
    mask_alta_energia = candidatos["energy_mik"].fillna(0) >= 7
    candidatos.loc[mask_alta_energia, "_reel_score"] += 30

    # Popularidad alta (>= 50) → gran bonus
    mask_popular = candidatos["popularidad"].fillna(0) >= 50
    candidatos.loc[mask_popular, "_reel_score"] += 25

    # Trending (año >= actual) → bonus
    candidatos["_es_trending"] = candidatos.apply(es_trending, axis=1)
    candidatos.loc[candidatos["_es_trending"], "_reel_score"] += 25

    # Año reciente (>= año actual - 1)
    mask_reciente = candidatos["año_spotify"].fillna(0) >= AÑO_ACTUAL - 1
    candidatos.loc[mask_reciente, "_reel_score"] += 10

    # Mashups → bonus
    mask_mashup = candidatos["version_tipo"].str.upper() == "MASHUP"
    candidatos.loc[mask_mashup, "_reel_score"] += 15

    # Versiones sucias/completas con alta energía (reels = impacto)
    mask_dirty = candidatos["version_tipo"].str.upper().isin(["DIRTY", "FULL", "EXTENDED"])
    candidatos.loc[mask_dirty, "_reel_score"] += 5

    # Popularidad directa como factor
    candidatos["_reel_score"] += candidatos["popularidad"].fillna(0) * 0.2

    # Ordenar por score y seleccionar
    candidatos = candidatos.sort_values("_reel_score", ascending=False)
    seleccion = candidatos.head(count).copy()

    # ─── Determinar razón de selección para cada track ───────────────────
    def razon_reel(row):
        """Genera las razones por las que un track es bueno para reel."""
        razones = []
        if pd.notna(row.get("energy_mik")) and row["energy_mik"] >= 7:
            razones.append("⚡ Alta energía")
        if pd.notna(row.get("popularidad")) and row["popularidad"] >= 50:
            razones.append("🌟 Popular")
        if es_trending(row):
            razones.append("🔥 Trending")
        if str(row.get("version_tipo", "")).upper() == "MASHUP":
            razones.append("🔀 Mashup")
        año = row.get("año_spotify", 0)
        if pd.notna(año) and año >= AÑO_ACTUAL - 1:
            razones.append(f"📅 Reciente ({int(año)})")
        if pd.notna(row.get("popularidad")) and row["popularidad"] >= 80:
            razones.append("💎 Hit viral")
        return razones if razones else ["🎵 Buena opción"]

    # ─── Encabezado ──────────────────────────────────────────────────────
    print()
    print(f"  {Color.BOLD}{Color.MAGENTA}╔{'═' * 128}╗{Color.RESET}")
    print(f"  {Color.BOLD}{Color.MAGENTA}║{Color.RESET} 📱 "
          f"{Color.BOLD}OPCIONES PARA REELS DE INSTAGRAM{Color.RESET}"
          f"{' ' * 89}{Color.MAGENTA}║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.MAGENTA}╠{'═' * 128}╣{Color.RESET}")
    print(f"  {Color.MAGENTA}║{Color.RESET} 🎵 Género: {Color.BOLD}{genero}{Color.RESET}"
          f"  │  📦 {count} opciones de alto impacto"
          f"{' ' * (77 - len(genero))}{Color.MAGENTA}║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.MAGENTA}╚{'═' * 128}╝{Color.RESET}")

    print(f"\n  {Color.DIM}💡 Seleccionados por: energía alta, popularidad, "
          f"tendencia, mashups{Color.RESET}\n")

    # ─── Imprimir cada track con razones ─────────────────────────────────
    imprimir_encabezado_bloque(
        "📱", "OPCIONES DE REEL", Color.MAGENTA,
        "Tracks de alto impacto para contenido corto", len(seleccion)
    )

    for i, (idx, row) in enumerate(seleccion.iterrows(), 1):
        print(formatear_track(row, i))
        razones = razon_reel(row)
        print(f"       {Color.DIM}↳ {' · '.join(razones)}{Color.RESET}")

    print()

    # ─── Construir resultado JSON ─────────────────────────────────────────
    opciones = []
    for _, row in seleccion.iterrows():
        razones = razon_reel(row)
        opciones.append({
            "titulo": str(row.get("titulo_limpio", "")),
            "artista": str(row.get("artista_limpio", "")),
            "bpm": float(row["bpm_mik"]) if pd.notna(row.get("bpm_mik")) else None,
            "key": str(row.get("key_mik", "")),
            "energy": float(row["energy_mik"]) if pd.notna(row.get("energy_mik")) else None,
            "version": str(row.get("version_tipo", "")),
            "popularidad": float(row["popularidad"]) if pd.notna(row.get("popularidad")) else None,
            "trending": es_trending(row),
            "año": int(row["año_spotify"]) if pd.notna(row.get("año_spotify")) else None,
            "ruta": str(row.get("ruta_completa", "")),
            "razones_reel": [r for r in razones],
        })

    serato_tracks = [o["ruta"] for o in opciones if o["ruta"]]

    paleta = {
        "metadata": {
            "tipo": "reel",
            "genero": genero,
            "opciones_generadas": len(opciones),
            "fecha_generacion": datetime.now().isoformat(),
        },
        "opciones_reel": opciones,
        "serato_tracks": serato_tracks
    }

    return paleta


# ═══════════════════════════════════════════════════════════════════════════════
#  MODO 3: CROSSOVER — Set Multi-Género
# ═══════════════════════════════════════════════════════════════════════════════

def encontrar_zona_transicion_bpm(df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple:
    """
    Encuentra el rango de BPM donde dos géneros se solapan.

    Args:
        df_a: DataFrame del género A
        df_b: DataFrame del género B

    Returns:
        Tupla (bpm_min, bpm_max) de la zona de transición
    """
    bpm_a = df_a["bpm_mik"].dropna()
    bpm_b = df_b["bpm_mik"].dropna()

    if bpm_a.empty or bpm_b.empty:
        return (90, 110)  # Rango genérico de fallback

    # Rango del género A (percentiles 25-75 para evitar outliers)
    a_min, a_max = bpm_a.quantile(0.25), bpm_a.quantile(0.75)
    # Rango del género B
    b_min, b_max = bpm_b.quantile(0.25), bpm_b.quantile(0.75)

    # Zona de solapamiento
    overlap_min = max(a_min, b_min)
    overlap_max = min(a_max, b_max)

    if overlap_min <= overlap_max:
        return (overlap_min, overlap_max)

    # Si no hay solapamiento, usar la zona intermedia
    medio = (a_max + b_min) / 2 if a_max < b_min else (b_max + a_min) / 2
    return (medio - 5, medio + 5)


def generar_paleta_crossover(df: pd.DataFrame, generos: list[str],
                              duracion: int) -> dict:
    """
    Genera una paleta para set crossover multi-género.

    Organiza bloques por género con zona de transición entre ellos
    y un bloque fusión con mashups y tracks que conectan ambos géneros.

    Args:
        df: DataFrame de la biblioteca
        generos: Lista de géneros (mínimo 2)
        duracion: Duración total en minutos

    Returns:
        Dict con la paleta crossover para JSON
    """
    if len(generos) < 2:
        print(f"{Color.ROJO}❌ Crossover requiere al menos 2 géneros{Color.RESET}")
        return {}

    # ─── Preparar DataFrames por género ──────────────────────────────────
    dfs_genero = {}
    for g in generos:
        df_g = filtrar_por_genero(df, g)
        if not df_g.empty:
            dfs_genero[g] = df_g

    if len(dfs_genero) < 2:
        print(f"{Color.ROJO}❌ No hay suficientes géneros con tracks{Color.RESET}")
        return {}

    # ─── Cálculos de distribución ────────────────────────────────────────
    tracks_necesarios = max(int(duracion / 3.5), 6)
    tracks_por_genero = max(6, int(tracks_necesarios * 1.5 / len(generos)))
    n_transicion = max(3, int(tracks_necesarios * 0.2))
    n_fusion = max(2, int(tracks_necesarios * 0.15))

    # ─── Encabezado ──────────────────────────────────────────────────────
    generos_str = " × ".join(generos)
    print()
    print(f"  {Color.BOLD}{Color.CYAN}╔{'═' * 128}╗{Color.RESET}")
    print(f"  {Color.BOLD}{Color.CYAN}║{Color.RESET} 🌐 "
          f"{Color.BOLD}PALETA DJ — SET CROSSOVER{Color.RESET}"
          f"{' ' * 96}{Color.CYAN}║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.CYAN}╠{'═' * 128}╣{Color.RESET}")
    print(f"  {Color.CYAN}║{Color.RESET} 🎵 Géneros: {Color.BOLD}{generos_str}{Color.RESET}"
          f"  │  ⏱️  {duracion} min  │  ~{tracks_necesarios} tracks necesarios"
          f"{' ' * (67 - len(generos_str))}{Color.CYAN}║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.CYAN}╚{'═' * 128}╝{Color.RESET}")

    usados = set()
    bloques_json = {}
    colores_bloques = [Color.VERDE, Color.AMARILLO, Color.ROJO, Color.AZUL, Color.MAGENTA]

    # ─── Bloques por género ──────────────────────────────────────────────
    generos_keys = list(dfs_genero.keys())
    for i, genero in enumerate(generos_keys):
        df_g = dfs_genero[genero]
        color = colores_bloques[i % len(colores_bloques)]

        tracks_bloque = seleccionar_tracks_bloque(
            df_g, energia_min=3, energia_max=10, cantidad=tracks_por_genero,
            priorizar_popular=True, excluir_indices=usados
        )
        usados.update(tracks_bloque.index)

        num_bloque = i + 1
        imprimir_bloque(
            tracks_bloque,
            f"{'🟢🟡🔴🔵🟣'[i] if i < 5 else '⚪'}",
            f"BLOQUE {num_bloque}: {genero.upper()}",
            color,
            f"Tracks principales de {genero} · {len(tracks_bloque)} opciones"
        )

        bloques_json[f"bloque_{num_bloque}_{genero.lower().replace(' ', '_')}"] = []
        for _, row in tracks_bloque.iterrows():
            bloques_json[f"bloque_{num_bloque}_{genero.lower().replace(' ', '_')}"].append({
                "titulo": str(row.get("titulo_limpio", "")),
                "artista": str(row.get("artista_limpio", "")),
                "bpm": float(row["bpm_mik"]) if pd.notna(row.get("bpm_mik")) else None,
                "key": str(row.get("key_mik", "")),
                "energy": float(row["energy_mik"]) if pd.notna(row.get("energy_mik")) else None,
                "version": str(row.get("version_tipo", "")),
                "popularidad": float(row["popularidad"]) if pd.notna(row.get("popularidad")) else None,
                "genero": genero,
                "ruta": str(row.get("ruta_completa", "")),
            })

        # ─── Zona de transición entre géneros consecutivos ───────────────
        if i < len(generos_keys) - 1:
            genero_siguiente = generos_keys[i + 1]
            df_sig = dfs_genero[genero_siguiente]

            bpm_min, bpm_max = encontrar_zona_transicion_bpm(df_g, df_sig)

            # Buscar tracks de transición en ambos géneros
            df_combinado = pd.concat([df_g, df_sig])
            df_combinado = df_combinado[~df_combinado.index.isin(usados)]

            # Filtrar por zona de BPM
            mask_bpm = (
                (df_combinado["bpm_mik"] >= bpm_min - 5) &
                (df_combinado["bpm_mik"] <= bpm_max + 5)
            ) | df_combinado["bpm_mik"].isna()

            # Priorizar versiones de transición y mashups
            mask_version = df_combinado["version_tipo"].str.upper().isin(
                ["TRANSITION", "INTRO-OUTRO", "MASHUP"]
            )

            # Combinar: primero versiones de transición, luego otros en zona BPM
            trans_pref = df_combinado[mask_version & mask_bpm]
            trans_otros = df_combinado[mask_bpm & ~mask_version]
            trans_candidatos = pd.concat([trans_pref, trans_otros])

            if trans_candidatos.empty:
                trans_candidatos = df_combinado

            trans_candidatos = trans_candidatos.head(n_transicion)
            usados.update(trans_candidatos.index)

            imprimir_bloque(
                trans_candidatos,
                "🔀",
                f"TRANSICIÓN: {genero} → {genero_siguiente}",
                Color.CYAN,
                f"BPM zona: {bpm_min:.0f}-{bpm_max:.0f} · "
                f"Versiones TRANSITION/MASHUP preferidas · {len(trans_candidatos)} opciones"
            )

            bloques_json[f"transicion_{genero.lower().replace(' ', '_')}_a_{genero_siguiente.lower().replace(' ', '_')}"] = []
            for _, row in trans_candidatos.iterrows():
                bloques_json[f"transicion_{genero.lower().replace(' ', '_')}_a_{genero_siguiente.lower().replace(' ', '_')}"].append({
                    "titulo": str(row.get("titulo_limpio", "")),
                    "artista": str(row.get("artista_limpio", "")),
                    "bpm": float(row["bpm_mik"]) if pd.notna(row.get("bpm_mik")) else None,
                    "key": str(row.get("key_mik", "")),
                    "energy": float(row["energy_mik"]) if pd.notna(row.get("energy_mik")) else None,
                    "version": str(row.get("version_tipo", "")),
                    "tipo_transicion": "puente",
                    "ruta": str(row.get("ruta_completa", "")),
                })

    # ─── Bloque FUSIÓN ───────────────────────────────────────────────────
    df_fusion_candidatos = df[~df.index.isin(usados)].copy()
    mask_mashup = df_fusion_candidatos["version_tipo"].str.upper().isin(
        ["MASHUP", "TRANSITION"]
    )
    fusion = df_fusion_candidatos[mask_mashup].copy()

    if len(fusion) < n_fusion:
        # Completar con tracks populares de cualquier género involucrado
        extras = df_fusion_candidatos[~mask_mashup].copy()
        for g in generos:
            mask_g = extras["genre_carpeta"].str.lower().str.contains(g.lower(), na=False)
            fusion = pd.concat([fusion, extras[mask_g]])
        fusion = fusion.drop_duplicates()

    fusion["_score"] = fusion.apply(calcular_score_track, axis=1)
    fusion = fusion.sort_values("_score", ascending=False).head(n_fusion)
    if "_score" in fusion.columns:
        fusion = fusion.drop(columns=["_score"])

    imprimir_bloque(
        fusion, "💥", "FUSIÓN — Mashups & conexiones",
        Color.MAGENTA,
        f"Tracks que mezclan los géneros · {len(fusion)} opciones"
    )

    bloques_json["fusion"] = []
    for _, row in fusion.iterrows():
        bloques_json["fusion"].append({
            "titulo": str(row.get("titulo_limpio", "")),
            "artista": str(row.get("artista_limpio", "")),
            "bpm": float(row["bpm_mik"]) if pd.notna(row.get("bpm_mik")) else None,
            "key": str(row.get("key_mik", "")),
            "version": str(row.get("version_tipo", "")),
            "ruta": str(row.get("ruta_completa", "")),
        })

    # ─── Recopilar rutas Serato ──────────────────────────────────────────
    serato_tracks = []
    for bloque_lista in bloques_json.values():
        for track in bloque_lista:
            ruta = track.get("ruta", "")
            if ruta:
                serato_tracks.append(ruta)

    paleta = {
        "metadata": {
            "tipo": "crossover",
            "generos": generos,
            "duracion_min": duracion,
            "tracks_necesarios": tracks_necesarios,
            "fecha_generacion": datetime.now().isoformat(),
        },
        "bloques": bloques_json,
        "serato_tracks": serato_tracks
    }

    return paleta


# ═══════════════════════════════════════════════════════════════════════════════
#  GUARDADO DE PALETA EN JSON
# ═══════════════════════════════════════════════════════════════════════════════

def guardar_paleta_json(paleta: dict, genero: str, duracion: int = 0,
                         modo: str = "set") -> Path:
    """
    Guarda la paleta generada en un archivo JSON.

    Formato: palette_YYYY-MM-DD_genero_duracion.json

    Args:
        paleta: Dict con la paleta completa
        genero: Género principal
        duracion: Duración en minutos (0 para reels)
        modo: Modo de generación (set, reel, crossover)

    Returns:
        Path al archivo JSON guardado
    """
    DIRECTORIO_SALIDA.mkdir(parents=True, exist_ok=True)

    fecha = datetime.now().strftime("%Y-%m-%d")
    genero_limpio = genero.lower().replace(" ", "_").replace(",", "-")

    if modo == "reel":
        nombre = f"palette_{fecha}_{genero_limpio}_reel.json"
    elif modo == "crossover":
        nombre = f"palette_{fecha}_{genero_limpio}_crossover_{duracion}min.json"
    else:
        nombre = f"palette_{fecha}_{genero_limpio}_{duracion}min.json"

    ruta_salida = DIRECTORIO_SALIDA / nombre

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(paleta, f, ensure_ascii=False, indent=2)

    print(f"  {Color.VERDE}💾 Paleta guardada en: {ruta_salida}{Color.RESET}")
    print(f"  {Color.DIM}   Incluye {len(paleta.get('serato_tracks', []))} "
          f"rutas para crate de Serato{Color.RESET}")
    print()

    return ruta_salida


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI — INTERFAZ DE LÍNEA DE COMANDOS
# ═══════════════════════════════════════════════════════════════════════════════

def crear_parser() -> argparse.ArgumentParser:
    """
    Crea el parser de argumentos con subcomandos: set, reel, crossover.

    Returns:
        ArgumentParser configurado
    """
    parser = argparse.ArgumentParser(
        prog="tracklist_engine",
        description=(
            "🎧 Motor de paletas DJ — Genera opciones expandidas para sets, "
            "reels y crossovers. Sous-chef del DJ: tú decides, nosotros organizamos."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python tracklist_engine.py set --genre Reggaeton --duration 50 --vibra perreo
  python tracklist_engine.py reel --genre Bachata --count 8
  python tracklist_engine.py crossover --genres "Hip Hop Night Club,Reggaeton" --duration 40
        """
    )

    parser.add_argument(
        "--csv", type=str, default=str(CSV_POR_DEFECTO),
        help=f"Ruta al CSV de la biblioteca (default: {CSV_POR_DEFECTO})"
    )

    subparsers = parser.add_subparsers(dest="modo", help="Modo de generación")

    # ─── Subcomando: set ─────────────────────────────────────────────────
    parser_set = subparsers.add_parser(
        "set",
        help="Generar paleta para set de YouTube",
        description="🎧 Genera una paleta expandida para un set de YouTube/Twitch"
    )
    parser_set.add_argument(
        "--genre", "-g", required=True, type=str,
        help="Género del set (ej: Reggaeton, Bachata, SALSA)"
    )
    parser_set.add_argument(
        "--duration", "-d", required=True, type=int,
        help="Duración del set en minutos (ej: 50, 30, 60)"
    )
    parser_set.add_argument(
        "--vibra", "-v", type=str, default="",
        help="Vibra/mood del set (ej: perreo, chill, party, clasico)"
    )

    # ─── Subcomando: reel ────────────────────────────────────────────────
    parser_reel = subparsers.add_parser(
        "reel",
        help="Generar opciones para reels de Instagram",
        description="📱 Selecciona tracks de alto impacto para reels"
    )
    parser_reel.add_argument(
        "--genre", "-g", required=True, type=str,
        help="Género para el reel"
    )
    parser_reel.add_argument(
        "--count", "-c", type=int, default=8,
        help="Número de opciones a generar (default: 8)"
    )

    # ─── Subcomando: crossover ───────────────────────────────────────────
    parser_crossover = subparsers.add_parser(
        "crossover",
        help="Generar paleta multi-género con transiciones",
        description="🌐 Genera paleta crossover con zonas de transición entre géneros"
    )
    parser_crossover.add_argument(
        "--genres", "-g", required=True, type=str,
        help='Géneros separados por coma (ej: "Hip Hop Night Club,Reggaeton")'
    )
    parser_crossover.add_argument(
        "--duration", "-d", required=True, type=int,
        help="Duración total del set en minutos"
    )

    return parser


def main():
    """Punto de entrada principal del motor de tracklists."""
    parser = crear_parser()
    args = parser.parse_args()

    if not args.modo:
        parser.print_help()
        print(f"\n{Color.AMARILLO}⚠️  Debes especificar un modo: set, reel o crossover{Color.RESET}")
        sys.exit(1)

    # ─── Banner ──────────────────────────────────────────────────────────
    print()
    print(f"  {Color.BOLD}{Color.CYAN}╔{'═' * 50}╗{Color.RESET}")
    print(f"  {Color.BOLD}{Color.CYAN}║  🎧 TRACKLIST ENGINE v1.0           ║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.CYAN}║  Motor de paletas para contenido DJ ║{Color.RESET}")
    print(f"  {Color.BOLD}{Color.CYAN}╚{'═' * 50}╝{Color.RESET}")
    print()

    # ─── Cargar biblioteca ───────────────────────────────────────────────
    ruta_csv = Path(args.csv)
    df = cargar_biblioteca(ruta_csv)

    # ─── Ejecutar modo seleccionado ──────────────────────────────────────
    paleta = {}

    if args.modo == "set":
        paleta = generar_paleta_set(df, args.genre, args.duration, args.vibra)
        if paleta:
            guardar_paleta_json(paleta, args.genre, args.duration, "set")

    elif args.modo == "reel":
        paleta = generar_opciones_reel(df, args.genre, args.count)
        if paleta:
            guardar_paleta_json(paleta, args.genre, modo="reel")

    elif args.modo == "crossover":
        generos = [g.strip() for g in args.genres.split(",")]
        paleta = generar_paleta_crossover(df, generos, args.duration)
        if paleta:
            genero_str = "-".join(generos)
            guardar_paleta_json(paleta, genero_str, args.duration, "crossover")

    if not paleta:
        print(f"\n{Color.ROJO}❌ No se pudo generar la paleta. "
              f"Verifica el género y los datos.{Color.RESET}")
        sys.exit(1)

    print(f"  {Color.VERDE}{Color.BOLD}✅ ¡Paleta lista! Ahora tú decides, chef. 🎧{Color.RESET}\n")


if __name__ == "__main__":
    main()
