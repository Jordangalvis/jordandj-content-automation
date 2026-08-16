#!/usr/bin/env python3
"""
youtube_metadata.py — Generador de metadata para YouTube.

Genera títulos, descripciones con tracklist + timestamps, y tags SEO
a partir de un JSON de paleta producido por tracklist_engine.py.

Uso:
    python youtube_metadata.py --palette palette.json
    python youtube_metadata.py --palette palette.json --vol 3
    python youtube_metadata.py --palette palette.json --output metadata.txt
"""

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── Emoji por género ────────────────────────────────────────────────────────
EMOJI_GENERO = {
    "reggaeton": "🔥", "bachata": "💃", "salsa": "🎺", "merengue": "🥁",
    "hip hop night club": "🎤", "rnb": "🎵", "r&b": "🎵", "cumbia": "🇦🇷",
    "dembow": "🔊", "afrobeats": "🌍", "funk nv": "🇧🇷", "funk": "🇧🇷",
    "musica mexicana": "🇲🇽", "edm": "⚡", "retro": "📻",
}

# ─── Tags SEO por género ─────────────────────────────────────────────────────
TAGS_GENERO = {
    "reggaeton": ["reggaeton mix", "reggaeton 2026", "perreo mix", "reggaeton session",
                  "mix reggaeton nuevo", "reggaeton para bailar", "dj reggaeton"],
    "bachata": ["bachata mix", "bachata 2026", "bachata romantica", "bachata session",
                "mix bachata para bailar", "bachata sensual"],
    "salsa": ["salsa mix", "salsa 2026", "salsa para bailar", "salsa session",
              "salsa clasica mix", "salsa romantica"],
    "merengue": ["merengue mix", "merengue 2026", "merengue para bailar",
                 "merengue clasico", "merengue session"],
    "hip hop night club": ["hip hop mix", "hip hop 2026", "hip hop classics",
                           "r&b hip hop mix", "club mix", "nightclub mix"],
    "rnb": ["r&b mix", "rnb 2026", "r&b session", "slow jams mix",
            "r&b playlist", "rnb para bailar"],
    "cumbia": ["cumbia argentina mix", "rkt mix", "cumbia 2026",
               "cumbia villera", "cumbia session"],
    "dembow": ["dembow mix", "dembow 2026", "dembow session", "dembow para bailar"],
    "afrobeats": ["afrobeats mix", "afrobeats 2026", "afro latin mix"],
    "funk nv": ["funk brasileiro mix", "baile funk", "funk 2026"],
    "musica mexicana": ["musica mexicana mix", "regional mexicano 2026",
                        "corridos mix", "musica mexicana session"],
}

TAGS_GENERALES = [
    "dj mix", "live mix", "dj set", "party mix", "mix para fiestas",
    "DJ Jordan", "dj jordan mix",
]


def cargar_paleta(ruta: Path) -> dict:
    """Carga un archivo JSON de paleta."""
    if not ruta.exists():
        print(f"❌ No se encontró: {ruta}", file=sys.stderr)
        sys.exit(1)
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_tracks_ordenados(paleta: dict) -> list[dict]:
    """Extrae todos los tracks de la paleta en orden de set."""
    bloques_orden = ["intro", "build", "peak", "cooldown", "wildcards"]
    tracks = []
    bloques = paleta.get("bloques", {})
    for bloque in bloques_orden:
        for t in bloques.get(bloque, []):
            tracks.append(t)
    return tracks


def generar_timestamps(tracks: list[dict], min_por_track: float = 3.5) -> list[str]:
    """Genera timestamps para la descripción de YouTube."""
    lineas = []
    minutos_acum = 0.0
    for t in tracks:
        h = int(minutos_acum // 60)
        m = int(minutos_acum % 60)
        s = int((minutos_acum % 1) * 60)
        if h > 0:
            ts = f"{h}:{m:02d}:{s:02d}"
        else:
            ts = f"{m}:{s:02d}"

        titulo = t.get("titulo", "???")[:50]
        artista = t.get("artista", "")[:30]
        if artista and artista != titulo:
            lineas.append(f"{ts} - {artista} - {titulo}")
        else:
            lineas.append(f"{ts} - {titulo}")
        minutos_acum += min_por_track
    return lineas


def generar_titulos(genero: str, vol: int, dj_name: str,
                    tipo: str = "set", año: int = 2026) -> list[str]:
    """Genera 5 sugerencias de título para YouTube."""
    g = genero.upper()
    emoji = EMOJI_GENERO.get(genero.lower(), "🎧")

    titulos = [
        f"{g} SESSION Vol.{vol} {emoji} | {dj_name} Live Mix {año}",
        f"{g} MIX {año} {emoji} | Lo Mejor del {g} | {dj_name}",
        f"{emoji} {g} PARA BAILAR Vol.{vol} | {dj_name} DJ Set",
        f"MIX {g} NUEVO {año} {emoji}{emoji} | {dj_name} Session",
        f"{dj_name} - {g} Vol.{vol} {emoji} | Live DJ Set {año}",
    ]

    if tipo == "crossover":
        generos = genero.split(",")
        if len(generos) >= 2:
            g1 = generos[0].strip().upper()
            g2 = generos[1].strip().upper()
            e1 = EMOJI_GENERO.get(generos[0].strip().lower(), "🎧")
            e2 = EMOJI_GENERO.get(generos[1].strip().lower(), "🔥")
            titulos = [
                f"{g1} vs {g2} {e1}{e2} | {dj_name} Crossover Mix {año}",
                f"{g1} × {g2} SESSION {e1}{e2} | The Bridge Mix | {dj_name}",
                f"DE {g1} A {g2} {e1}→{e2} | {dj_name} Live Mix {año}",
                f"{e1} {g1} MEETS {g2} {e2} | {dj_name} DJ Set",
                f"{dj_name} - {g1} vs {g2} Vol.{vol} {e1}{e2}",
            ]
    return titulos


def generar_descripcion(tracks: list[dict], genero: str, vol: int,
                        dj_name: str, duracion: int) -> str:
    """Genera la descripción completa para YouTube."""
    emoji = EMOJI_GENERO.get(genero.lower(), "🎧")
    timestamps = generar_timestamps(tracks)
    año = datetime.now().year

    desc = []
    desc.append(f"{emoji} {genero.upper()} SESSION Vol.{vol} | {dj_name}")
    desc.append("")
    desc.append(f"Mix de {duracion} minutos con lo mejor del {genero} {año}.")
    desc.append(f"Grabado en vivo por {dj_name}.")
    desc.append("")
    desc.append("─" * 40)
    desc.append(f"📋 TRACKLIST ({len(tracks)} tracks)")
    desc.append("─" * 40)
    for line in timestamps:
        desc.append(line)
    desc.append("")
    desc.append("─" * 40)
    desc.append("🔗 SÍGUEME")
    desc.append("─" * 40)
    desc.append("📸 Instagram: @jordandj")
    desc.append("🎵 TikTok: @jordandj")
    desc.append("📱 YouTube: @DJJordan")
    desc.append("")
    desc.append("─" * 40)
    desc.append("")

    # Hashtags
    tags_g = TAGS_GENERO.get(genero.lower(), [])
    hashtags = [f"#{t.replace(' ', '')}" for t in tags_g[:8]]
    hashtags.extend(["#djmix", "#liveset", f"#{genero.lower().replace(' ', '')}mix"])
    desc.append(" ".join(hashtags))

    return "\n".join(desc)


def generar_tags(tracks: list[dict], genero: str, dj_name: str) -> str:
    """Genera tags SEO para YouTube (max 500 chars)."""
    tags = list(TAGS_GENERALES)

    # Tags de género
    tags_g = TAGS_GENERO.get(genero.lower(), [])
    tags.extend(tags_g)

    # Tags de artistas (únicos, top 10 por popularidad)
    artistas = {}
    for t in tracks:
        a = t.get("artista", "").strip()
        p = t.get("popularidad", 0) or 0
        if a and len(a) > 2:
            artistas[a] = max(artistas.get(a, 0), p)

    top_artistas = sorted(artistas.items(), key=lambda x: x[1], reverse=True)[:10]
    for nombre, _ in top_artistas:
        tags.append(nombre.lower())

    # Unir y recortar a 500 chars
    resultado = ", ".join(dict.fromkeys(tags))  # elimina duplicados manteniendo orden
    if len(resultado) > 500:
        resultado = resultado[:497] + "..."
    return resultado


def main():
    parser = argparse.ArgumentParser(
        description="🎬 Generador de metadata para YouTube",
    )
    parser.add_argument("--palette", type=Path, required=True,
                        help="Ruta al JSON de paleta")
    parser.add_argument("--vol", type=int, default=1,
                        help="Número de volumen (default: 1)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Guardar metadata en archivo .txt")
    parser.add_argument("--dj-name", type=str, default="DJ Jordan",
                        help="Nombre del DJ (default: DJ Jordan)")

    args = parser.parse_args()

    # Cargar paleta
    paleta = cargar_paleta(args.palette)
    meta = paleta.get("metadata", {})
    genero = meta.get("genero", "Mix")
    duracion = meta.get("duracion_min", 30)
    tipo = meta.get("tipo", "set")

    tracks = obtener_tracks_ordenados(paleta)

    sep = "═" * 70

    # ── Títulos sugeridos ──
    print(f"\n{sep}")
    print(f"  🎬  METADATA PARA YOUTUBE — {genero.upper()} Vol.{args.vol}")
    print(f"{sep}\n")

    titulos = generar_titulos(genero, args.vol, args.dj_name, tipo)
    print("  📌 TÍTULOS SUGERIDOS (elige uno):")
    print(f"  {'─' * 60}")
    for i, t in enumerate(titulos, 1):
        marcador = " ★ RECOMENDADO" if i == 1 else ""
        print(f"  {i}. {t}{marcador}")

    # ── Descripción ──
    print(f"\n{'─' * 70}")
    print("  📝 DESCRIPCIÓN COMPLETA:")
    print(f"{'─' * 70}")
    desc = generar_descripcion(tracks, genero, args.vol, args.dj_name, duracion)
    for linea in desc.split("\n"):
        print(f"  {linea}")

    # ── Tags ──
    print(f"\n{'─' * 70}")
    print("  🏷️  TAGS SEO:")
    print(f"{'─' * 70}")
    tags = generar_tags(tracks, genero, args.dj_name)
    print(f"  {tags}")
    print(f"  ({len(tags)} / 500 caracteres)")

    # ── Thumbnail ──
    print(f"\n{'─' * 70}")
    print("  🖼️  SUGERENCIAS DE THUMBNAIL:")
    print(f"{'─' * 70}")
    emoji = EMOJI_GENERO.get(genero.lower(), "🎧")
    print(f"  • Texto principal: \"{genero.upper()} VOL.{args.vol}\"")
    print(f"  • Subtítulo: \"{args.dj_name} LIVE MIX\"")
    print(f"  • Estilo: Fondo oscuro, texto blanco bold, acento de color por género")
    print(f"  • Emoji destacado: {emoji}")

    print(f"\n{sep}")

    # ── Guardar archivo ──
    if args.output:
        salida = []
        salida.append(f"=== YOUTUBE METADATA — {genero.upper()} Vol.{args.vol} ===\n")
        salida.append("--- TÍTULOS SUGERIDOS ---")
        for i, t in enumerate(titulos, 1):
            salida.append(f"{i}. {t}")
        salida.append("\n--- DESCRIPCIÓN ---")
        salida.append(desc)
        salida.append("\n--- TAGS ---")
        salida.append(tags)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("\n".join(salida), encoding="utf-8")
        print(f"  💾 Metadata guardada en: {args.output}")
    else:
        default_out = Path(__file__).parent / "paletas" / f"metadata_{genero.lower().replace(' ', '_')}_vol{args.vol}.txt"
        default_out.parent.mkdir(parents=True, exist_ok=True)
        salida = []
        salida.append(f"=== YOUTUBE METADATA — {genero.upper()} Vol.{args.vol} ===\n")
        salida.append("--- TÍTULOS SUGERIDOS ---")
        for i, t in enumerate(titulos, 1):
            salida.append(f"{i}. {t}")
        salida.append("\n--- DESCRIPCIÓN ---")
        salida.append(desc)
        salida.append("\n--- TAGS ---")
        salida.append(tags)
        default_out.write_text("\n".join(salida), encoding="utf-8")
        print(f"  💾 Metadata guardada en: {default_out}")

    print(f"\n  ✅ ¡Metadata lista para YouTube! 🎬\n")


if __name__ == "__main__":
    main()
