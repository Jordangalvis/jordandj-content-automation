#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serato_crate_generator.py
=========================
Genera archivos .crate binarios para Serato DJ a partir de un JSON de paleta
producido por tracklist_engine.py.

Formato binario de Serato Crate:
  - Cabecera: b'vrsn' + 4 bytes longitud + cadena de versión en UTF-16BE
  - Cada pista: b'otrk' + 4 bytes longitud entrada + b'ptrk' + 4 bytes longitud ruta + ruta en UTF-16BE

Uso:
  python serato_crate_generator.py --palette palette.json
  python serato_crate_generator.py --palette palette.json --name "Mi Crate"
  python serato_crate_generator.py --palette palette.json --dry-run
  python serato_crate_generator.py --palette palette.json --force

Autor: JordanDJ Content System
"""

import argparse
import io
import json
import struct
import sys
from pathlib import Path
from datetime import datetime

# Fix encoding para Windows (cp1252 no soporta emoji/unicode)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# Constantes del formato Serato
SERATO_VERSION_STRING = "1.0/Serato ScratchLive Crate"
SERATO_DIRS = [
    Path(r"D:\_Serato_\Subcrates"),
    Path(r"C:\Users\jorda\Music\_Serato_\Subcrates"),
]
SERATO_SUBCRATES_DIR = SERATO_DIRS[0] if SERATO_DIRS[0].exists() else SERATO_DIRS[1]

# Tags binarias del formato crate
TAG_VRSN = b"vrsn"
TAG_OTRK = b"otrk"
TAG_PTRK = b"ptrk"


def _encode_utf16be(text: str) -> bytes:
    """Codifica una cadena a UTF-16BE sin BOM."""
    return text.encode("utf-16-be")


def _build_header() -> bytes:
    """Construye la cabecera del archivo .crate."""
    version_encoded = _encode_utf16be(SERATO_VERSION_STRING)
    header_length = len(version_encoded)
    return TAG_VRSN + struct.pack(">I", header_length) + version_encoded


def _build_track_entry(track_path: str) -> bytes:
    """Construye una entrada de pista para el crate."""
    path_encoded = _encode_utf16be(track_path)
    path_length = len(path_encoded)
    ptrk_block = TAG_PTRK + struct.pack(">I", path_length) + path_encoded
    otrk_length = len(ptrk_block)
    return TAG_OTRK + struct.pack(">I", otrk_length) + ptrk_block


def normalize_path_for_serato(ruta: str) -> str:
    """
    Normaliza una ruta al formato que Serato espera en Windows:
    - Sin letra de unidad (sin 'D:' ni 'C:')
    - Sin barra inicial (ej: 'DJ/Music/...' en lugar de '/DJ/Music/...')
    - Con forward slashes (/)
    """
    ruta_posix = Path(ruta).as_posix()
    # Eliminar letra de unidad si existe (ej. D: o C:)
    if len(ruta_posix) >= 2 and ruta_posix[1] == ":":
        ruta_posix = ruta_posix[2:]
    # Eliminar barra inicial
    ruta_posix = ruta_posix.lstrip("/")
    return ruta_posix


def resolver_ruta_real(ruta_str: str) -> Path | None:
    """Intenta encontrar el archivo si la ruta del CSV cambió."""
    p = Path(ruta_str)
    if p.exists():
        return p
    # Buscar en D:\DJ
    dj_root = Path(r"D:\DJ")
    if dj_root.exists():
        # Coincidencia por nombre exacto
        matches = list(dj_root.rglob(p.name))
        if matches:
            return matches[0]
        # Coincidencia por título limpio
        stem = p.stem.split(" - ")[0].split("[")[0].strip()
        if len(stem) > 4:
            matches_part = list(dj_root.rglob(f"*{stem}*.mp3")) + list(dj_root.rglob(f"*{stem}*.wav"))
            if matches_part:
                return matches_part[0]
    return None


def create_crate(name: str, track_paths: list[str], serato_dir: Path = None) -> list[Path]:
    """
    Crea el archivo .crate binario sincronizado en todos los directorios de Serato (D: y C:).
    """
    if not track_paths:
        raise ValueError("La lista de pistas no puede estar vacía.")

    # Construir el contenido binario con rutas normalizadas
    crate_data = _build_header()

    rutas_resueltas = []
    for ruta in track_paths:
        real = resolver_ruta_real(ruta)
        ruta_a_usar = str(real) if real else ruta
        ruta_normalizada = normalize_path_for_serato(ruta_a_usar)
        crate_data += _build_track_entry(ruta_normalizada)
        rutas_resueltas.append(ruta_normalizada)

    crate_filename = f"{name}.crate"
    created_paths = []

    # Escribir en todos los directorios de Serato existentes (D:\_Serato_ y C:\...\_Serato_)
    dirs_to_write = [d for d in SERATO_DIRS if d.exists()]
    if serato_dir and serato_dir.exists() and serato_dir not in dirs_to_write:
        dirs_to_write.append(serato_dir)

    for s_dir in dirs_to_write:
        # Si tiene carpeta padre (ej: YOUTUBE_SETS%%SET_...), crear también el padre si no existe
        if "%%" in name:
            padre_nombre = name.split("%%")[0]
            padre_file = s_dir / f"{padre_nombre}.crate"
            if not padre_file.exists():
                padre_file.write_bytes(_build_header())

        target_file = s_dir / crate_filename
        target_file.write_bytes(crate_data)
        created_paths.append(target_file)

    return created_paths


def load_palette(palette_path: Path) -> dict:
    """
    Carga y valida un archivo JSON de paleta.

    Espera encontrar al menos la clave 'serato_tracks' con una lista de rutas.
    También puede contener metadatos como 'fecha', 'genero', 'nombre', etc.

    Parámetros:
        palette_path: Ruta al archivo JSON de paleta

    Retorna:
        Diccionario con los datos de la paleta

    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError:        Si el JSON no tiene la estructura esperada
    """
    if not palette_path.exists():
        raise FileNotFoundError(f"Archivo de paleta no encontrado: {palette_path}")

    with open(palette_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validar que exista la lista de pistas
    if "serato_tracks" not in data:
        raise ValueError(
            f"El archivo de paleta no contiene la clave 'serato_tracks'.\n"
            f"Claves encontradas: {list(data.keys())}"
        )

    if not isinstance(data["serato_tracks"], list):
        raise ValueError("'serato_tracks' debe ser una lista de rutas de archivo.")

    if len(data["serato_tracks"]) == 0:
        raise ValueError("'serato_tracks' está vacío. No hay pistas para agregar al crate.")

    return data


def generate_crate_name(palette_data: dict, parent_folder: str = None) -> str:
    """
    Genera un nombre de crate automático basado en los metadatos de la paleta,
    organizado en carpetas de Serato para contenido largo y corto.

    Estructura en Serato:
      - Contenido Largo (YouTube): YOUTUBE_SETS%%SET_YYYY-MM-DD_Genero_30min
      - Contenido Corto (Reels):   REELS_TIKTOK%%REEL_YYYY-MM-DD_Genero

    Parámetros:
        palette_data:  Diccionario con los datos de la paleta
        parent_folder: Carpeta padre personalizada en Serato (opcional)

    Retorna:
        Nombre del crate con estructura jerárquica de Serato
    """
    meta = palette_data.get("metadata", {})
    tipo = meta.get("tipo", palette_data.get("tipo", "set")).lower()

    # Fecha
    fecha = meta.get("fecha", palette_data.get("fecha", None))
    if not fecha:
        fecha_gen = meta.get("fecha_generacion", "")
        if fecha_gen:
            fecha = fecha_gen.split("T")[0]
        else:
            fecha = datetime.now().strftime("%Y-%m-%d")

    # Género
    genero = meta.get("genero", palette_data.get("genero", palette_data.get("genre_carpeta", "Mix")))
    genero_limpio = genero.replace(" ", "").replace("/", "-").replace("&", "y").replace(",", "-")

    # Duración
    duracion = meta.get("duracion_min", None)

    # Determinar carpeta padre y nombre de subcrate
    if parent_folder is not None:
        padre = parent_folder.strip().replace("%%", "_")
    elif tipo == "reel":
        padre = "REELS_TIKTOK"
    else:
        padre = "YOUTUBE_SETS"

    if tipo == "reel":
        nombre_sub = f"REEL_{fecha}_{genero_limpio}"
    elif tipo == "crossover":
        dur_str = f"_{duracion}min" if duracion else ""
        nombre_sub = f"CROSSOVER_{fecha}_{genero_limpio}{dur_str}"
    else:
        dur_str = f"_{duracion}min" if duracion else ""
        volumen = meta.get("volumen", palette_data.get("volumen", 1))
        nombre_sub = f"SET_{fecha}_{genero_limpio}{dur_str}"

    if padre:
        return f"{padre}%%{nombre_sub}"
    return nombre_sub


def print_summary(crate_name: str, track_paths: list[str], serato_dir: Path,
                  dry_run: bool = False) -> None:
    """
    Imprime un resumen del crate que se va a crear (o se creó).

    Parámetros:
        crate_name:  Nombre del crate
        track_paths: Lista de rutas de pistas
        serato_dir:  Directorio destino
        dry_run:     Si es True, indica que es solo una simulación
    """
    modo = "🔍 SIMULACIÓN (--dry-run)" if dry_run else "📦 CREACIÓN DE CRATE"
    separador = "=" * 60

    print(f"\n{separador}")
    print(f"  {modo}")
    print(f"{separador}")
    print(f"  📁 Nombre del crate : {crate_name}")
    print(f"  📂 Archivo destino  : %%{crate_name}.crate")
    print(f"  📍 Directorio Serato: {serato_dir}")
    print(f"  🎵 Total de pistas  : {len(track_paths)}")
    print(f"{separador}")
    print(f"  Lista de pistas:")
    print(f"  {'-' * 56}")

    for i, ruta in enumerate(track_paths, 1):
        ruta_normalizada = normalize_path_for_serato(ruta)
        # Mostrar solo el nombre del archivo para legibilidad
        nombre_archivo = Path(ruta).name
        print(f"  {i:3d}. {nombre_archivo}")
        print(f"       → {ruta_normalizada}")

    print(f"{separador}\n")


def confirm_action(crate_name: str) -> bool:
    """
    Solicita confirmación al usuario antes de escribir el crate.

    Parámetros:
        crate_name: Nombre del crate a crear

    Retorna:
        True si el usuario confirma, False si cancela
    """
    while True:
        respuesta = input(
            f"¿Deseas crear el crate '%%{crate_name}.crate'? [s/n]: "
        ).strip().lower()

        if respuesta in ("s", "si", "sí", "y", "yes"):
            return True
        elif respuesta in ("n", "no"):
            return False
        else:
            print("  Por favor, responde 's' (sí) o 'n' (no).")


def main():
    """Punto de entrada principal del script."""
    parser = argparse.ArgumentParser(
        description="Genera archivos .crate de Serato DJ desde un JSON de paleta.",
        epilog=(
            "Ejemplos de uso:\n"
            "  python serato_crate_generator.py --palette palette.json --dry-run\n"
            "  python serato_crate_generator.py --palette palette.json --name MiCrate\n"
            "  python serato_crate_generator.py --palette palette.json --force\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--palette",
        type=Path,
        required=True,
        help="Ruta al archivo JSON de paleta generado por tracklist_engine.py",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Carpeta contenedora en Serato (ej: YOUTUBE_SETS, REELS_TIKTOK). Por defecto se auto-detecta según el tipo de contenido.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Nombre personalizado para el subcrate (por defecto se auto-genera desde los metadatos)",
    )
    parser.add_argument(
        "--serato-dir",
        type=Path,
        default=SERATO_SUBCRATES_DIR,
        help=f"Directorio de Subcrates de Serato (por defecto: {SERATO_SUBCRATES_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular la creación sin escribir archivos (recomendado para la primera prueba)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Crear el crate sin pedir confirmación interactiva",
    )

    args = parser.parse_args()

    # --- Cargar la paleta ---
    try:
        palette_data = load_palette(args.palette)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(f"❌ Error al cargar la paleta: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Extraer las pistas ---
    track_paths = palette_data["serato_tracks"]

    # Validar que las rutas existan (advertencia, no error fatal)
    pistas_faltantes = []
    for ruta in track_paths:
        if not Path(ruta).exists():
            pistas_faltantes.append(ruta)

    if pistas_faltantes:
        print(f"\n⚠️  Advertencia: {len(pistas_faltantes)} pista(s) no encontrada(s):")
        for ruta in pistas_faltantes[:5]:
            print(f"    → {ruta}")
        if len(pistas_faltantes) > 5:
            print(f"    ... y {len(pistas_faltantes) - 5} más.")
        print()

    # --- Determinar el nombre del crate ---
    if args.name:
        if args.folder:
            crate_name = f"{args.folder}%%{args.name}"
        else:
            crate_name = args.name
    else:
        crate_name = generate_crate_name(palette_data, parent_folder=args.folder)

    # Sanitizar el nombre: quitar caracteres problemáticos para nombres de archivo (preservando %%)
    caracteres_invalidos = '<>:"/\\|?*'
    for c in caracteres_invalidos:
        crate_name = crate_name.replace(c, "_")

    # --- Mostrar resumen ---
    print_summary(crate_name, track_paths, args.serato_dir, dry_run=args.dry_run)

    # --- Modo dry-run: solo mostrar y salir ---
    if args.dry_run:
        print("ℹ️  Modo simulación activado. No se escribió ningún archivo.")
        print("   Ejecuta sin --dry-run para crear el crate.\n")
        sys.exit(0)

    # --- Confirmación interactiva (si no se usa --force) ---
    if not args.force:
        if not confirm_action(crate_name):
            print("❌ Operación cancelada por el usuario.")
            sys.exit(0)

    # --- Crear el crate (y asegurar carpeta padre si aplica) ---
    try:
        crate_paths = create_crate(crate_name, track_paths, args.serato_dir)
        print(f"✅ Crate creado exitosamente en:")
        for p in crate_paths:
            print(f"   📍 {p}")
        print(f"   Abre Serato DJ y el crate '{crate_name}' debería aparecer en la lista.")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"❌ Error al escribir el archivo: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
