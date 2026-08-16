#!/usr/bin/env python3
"""
pipeline.py — Orquestador Maestro del Sistema JordanDJ.

Unifica todo el flujo en un solo comando:
1. Genera la paleta musical (tracklist_engine.py)
2. Inyecta el Crate directamente en Serato DJ (serato_crate_generator.py)
3. Genera la metadata completa de YouTube/Reels (youtube_metadata.py)

Uso:
    python pipeline.py set --genre Reggaeton --duration 40 --vibra perreo
    python pipeline.py reel --genre Reggaeton --count 8
    python pipeline.py crossover --genres "Hip Hop Night Club,Reggaeton" --duration 40
"""

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
PALETAS_DIR = BASE_DIR / "paletas"


def ejecutar_comando(cmd: list[str]) -> str:
    """Ejecuta un comando de Python y captura la salida."""
    resultado = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=BASE_DIR
    )
    if resultado.returncode != 0:
        print(f"❌ Error ejecutando: {' '.join(cmd)}", file=sys.stderr)
        print(resultado.stderr, file=sys.stderr)
    return resultado.stdout


def obtener_ultima_paleta() -> Path | None:
    """Encuentra el archivo JSON de paleta más reciente."""
    if not PALETAS_DIR.exists():
        return None
    paletas = list(PALETAS_DIR.glob("palette_*.json"))
    if not paletas:
        return None
    return max(paletas, key=lambda p: p.stat().st_mtime)


def main():
    parser = argparse.ArgumentParser(
        description="🎧 Orquestador Todo-en-Uno: Paleta -> Serato Crate -> YouTube Metadata",
    )
    sub = parser.add_subparsers(dest="modo", required=True)

    # Modo SET
    set_parser = sub.add_parser("set", help="Generar Set para YouTube")
    set_parser.add_argument("--genre", type=str, required=True, help="Género principal")
    set_parser.add_argument("--duration", type=int, default=40, help="Duración en minutos (default: 40)")
    set_parser.add_argument("--vibra", type=str, default="", help="Vibra/mood (ej: perreo, romantico, party)")
    set_parser.add_argument("--vol", type=int, default=1, help="Número de volumen")

    # Modo REEL
    reel_parser = sub.add_parser("reel", help="Generar opciones para Reel / TikTok")
    reel_parser.add_argument("--genre", type=str, required=True, help="Género")
    reel_parser.add_argument("--count", type=int, default=8, help="Cantidad de tracks (default: 8)")

    # Modo CROSSOVER
    cross_parser = sub.add_parser("crossover", help="Generar Set Crossover multi-género")
    cross_parser.add_argument("--genres", type=str, required=True, help="Géneros separados por coma (ej: 'Hip Hop Night Club,Reggaeton')")
    cross_parser.add_argument("--duration", type=int, default=40, help="Duración en minutos")
    cross_parser.add_argument("--vol", type=int, default=1, help="Número de volumen")

    args = parser.parse_args()

    print("\n" + "═" * 70)
    print("  🚀 JORDAN DJ CONTENT PIPELINE — EJECUCIÓN AUTOMÁTICA")
    print("═" * 70)

    # 1. Generar Paleta
    print("\n  [Paso 1/3] 🧠 Generando paleta creativa...")
    if args.modo == "set":
        cmd_paleta = [
            sys.executable, str(BASE_DIR / "tracklist_engine.py"),
            "set", "--genre", args.genre, "--duration", str(args.duration)
        ]
        if args.vibra:
            cmd_paleta.extend(["--vibra", args.vibra])
    elif args.modo == "reel":
        cmd_paleta = [
            sys.executable, str(BASE_DIR / "tracklist_engine.py"),
            "reel", "--genre", args.genre, "--count", str(args.count)
        ]
    elif args.modo == "crossover":
        cmd_paleta = [
            sys.executable, str(BASE_DIR / "tracklist_engine.py"),
            "crossover", "--genres", args.genres, "--duration", str(args.duration)
        ]

    out_paleta = ejecutar_comando(cmd_paleta)
    print(out_paleta)

    paleta_file = obtener_ultima_paleta()
    if not paleta_file:
        print("❌ Error: No se encontró el archivo de paleta generado.")
        sys.exit(1)

    # 2. Generar Crate de Serato
    print("\n  [Paso 2/3] 🎚️ Inyectando Crate directamente en Serato DJ...")
    cmd_crate = [
        sys.executable, str(BASE_DIR / "serato_crate_generator.py"),
        "--palette", str(paleta_file),
        "--force"
    ]
    out_crate = ejecutar_comando(cmd_crate)
    print(out_crate)

    # 3. Generar Metadata YouTube (solo para sets y crossover)
    if args.modo in ["set", "crossover"]:
        vol = getattr(args, "vol", 1)
        print("\n  [Paso 3/3] 🎬 Generando Títulos, Timestamps y Tags de YouTube...")
        cmd_meta = [
            sys.executable, str(BASE_DIR / "youtube_metadata.py"),
            "--palette", str(paleta_file),
            "--vol", str(vol)
        ]
        out_meta = ejecutar_comando(cmd_meta)
        print(out_meta)

    print("\n" + "═" * 70)
    print("  ✨ ¡TODO LISTO! Solo abre Serato DJ y tu música estará esperándote.")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    main()
