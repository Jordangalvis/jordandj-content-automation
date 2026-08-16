#!/usr/bin/env python3
"""
content_calendar.py — Calendario de contenido con rotación de géneros.

Genera un calendario semanal siguiendo el roadmap de crecimiento
de 4 fases: Core Latino → Expansión Latina → Crossover → English Market.

Uso:
    python content_calendar.py generate --weeks 12
    python content_calendar.py next
    python content_calendar.py status
"""

import argparse
import io
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Fix encoding para Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

STATE_FILE = Path(__file__).parent / "calendar_state.json"

# ─── Roadmap de crecimiento ──────────────────────────────────────────────────

FASES = {
    1: {
        "nombre": "CORE LATINO",
        "emoji": "🇵🇷",
        "meses": "1-2",
        "sets": [
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Session", "emoji": "🔥"},
            {"genero": "Bachata", "tipo": "set", "tema": "Bachata & Salsa Night", "emoji": "💃"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Perreo", "emoji": "🔥"},
            {"genero": "Merengue", "tipo": "set", "tema": "Merengue Clásico + Moderno", "emoji": "🥁"},
            {"genero": "SALSA", "tipo": "set", "tema": "Salsa Session", "emoji": "🎺"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Romántico", "emoji": "💕"},
            {"genero": "Bachata,SALSA", "tipo": "crossover", "tema": "Bachata × Salsa Night", "emoji": "💃🎺"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Hits", "emoji": "🔥"},
        ],
        "reels": [
            {"genero": "Reggaeton", "tema": "Drop del momento", "emoji": "🔥"},
            {"genero": "Bachata", "tema": "Bachata trending", "emoji": "💃"},
            {"genero": "Reggaeton", "tema": "Perreo mashup", "emoji": "🔊"},
            {"genero": "Merengue", "tema": "Merengue hit", "emoji": "🥁"},
            {"genero": "SALSA", "tema": "Salsa viral", "emoji": "🎺"},
            {"genero": "Reggaeton", "tema": "Reggaeton romántico clip", "emoji": "💕"},
            {"genero": "Bachata", "tema": "Bachata sensual", "emoji": "💃"},
            {"genero": "Reggaeton", "tema": "Hit del momento", "emoji": "🔥"},
        ],
    },
    2: {
        "nombre": "EXPANSIÓN LATINA",
        "emoji": "🌎",
        "meses": "2-4",
        "sets": [
            {"genero": "Cumbia", "tipo": "set", "tema": "Cumbia Argentina Session", "emoji": "🇦🇷"},
            {"genero": "Reggaeton,Dembow", "tipo": "crossover", "tema": "Reggaeton × Dembow", "emoji": "🔥🔊"},
            {"genero": "FUNK NV", "tipo": "set", "tema": "Funk Brasileiro Mix", "emoji": "🇧🇷"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Latin Party Mix", "emoji": "🎉"},
            {"genero": "Musica Mexicana", "tipo": "set", "tema": "Música Mexicana Session", "emoji": "🇲🇽"},
            {"genero": "Cumbia,Reggaeton", "tipo": "crossover", "tema": "Cumbia × Reggaeton", "emoji": "🇦🇷🔥"},
            {"genero": "Dembow", "tipo": "set", "tema": "Dembow Session", "emoji": "🔊"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Power", "emoji": "🔥"},
        ],
        "reels": [
            {"genero": "Cumbia", "tema": "RKT viral moment", "emoji": "🇦🇷"},
            {"genero": "Dembow", "tema": "Dembow drop", "emoji": "🔊"},
            {"genero": "FUNK NV", "tema": "Funk viral", "emoji": "🇧🇷"},
            {"genero": "Reggaeton", "tema": "Best of mes", "emoji": "🔥"},
            {"genero": "Musica Mexicana", "tema": "Regional hit", "emoji": "🇲🇽"},
            {"genero": "Cumbia", "tema": "Cumbia remix", "emoji": "🇦🇷"},
            {"genero": "Dembow", "tema": "Dembow x Reggaeton clip", "emoji": "🔊"},
            {"genero": "Reggaeton", "tema": "Trending drop", "emoji": "🔥"},
        ],
    },
    3: {
        "nombre": "CROSSOVER",
        "emoji": "🌉",
        "meses": "4-6",
        "sets": [
            {"genero": "Reggaeton,RnB", "tipo": "crossover", "tema": "Reggaeton Romántico × R&B", "emoji": "💕🎵"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Power", "emoji": "🔥"},
            {"genero": "Hip Hop Night Club,Reggaeton", "tipo": "crossover", "tema": "Hip-Hop Classics vs Reggaeton", "emoji": "🎤🔥"},
            {"genero": "Afrobeats", "tipo": "set", "tema": "Afrobeats × Latino", "emoji": "🌍"},
            {"genero": "RnB", "tipo": "set", "tema": "R&B Smooth Session", "emoji": "🎵"},
            {"genero": "Reggaeton,Bachata", "tipo": "crossover", "tema": "Latin Love Mix", "emoji": "💕💃"},
            {"genero": "Hip Hop Night Club", "tipo": "set", "tema": "Hip-Hop Night Session", "emoji": "🎤"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Session", "emoji": "🔥"},
        ],
        "reels": [
            {"genero": "RnB", "tema": "Love song mashup", "emoji": "💕"},
            {"genero": "Reggaeton", "tema": "Hit del momento", "emoji": "🔥"},
            {"genero": "Hip Hop Night Club", "tema": "The Bridge moment", "emoji": "🎤"},
            {"genero": "Afrobeats", "tema": "Afro-latin drop", "emoji": "🌍"},
            {"genero": "RnB", "tema": "R&B smooth clip", "emoji": "🎵"},
            {"genero": "Reggaeton", "tema": "Reggaeton romántico", "emoji": "💕"},
            {"genero": "Hip Hop Night Club", "tema": "Hip-Hop classic", "emoji": "🎤"},
            {"genero": "Reggaeton", "tema": "Perreo clip", "emoji": "🔥"},
        ],
    },
    4: {
        "nombre": "ENGLISH MARKET",
        "emoji": "🇺🇸",
        "meses": "6+",
        "sets": [
            {"genero": "RnB", "tipo": "set", "tema": "R&B Session (English)", "emoji": "🎵"},
            {"genero": "Reggaeton,RnB", "tipo": "crossover", "tema": "Latin × English Party", "emoji": "🌎🎵"},
            {"genero": "Hip Hop Night Club", "tipo": "set", "tema": "Hip-Hop Classics Night", "emoji": "🎤"},
            {"genero": "Reggaeton", "tipo": "set", "tema": "Reggaeton Session", "emoji": "🔥"},
            {"genero": "RnB,Hip Hop Night Club", "tipo": "crossover", "tema": "R&B × Hip-Hop Mix", "emoji": "🎵🎤"},
            {"genero": "Afrobeats,RnB", "tipo": "crossover", "tema": "Afro × R&B Session", "emoji": "🌍🎵"},
            {"genero": "Hip Hop Night Club,Reggaeton", "tipo": "crossover", "tema": "The Bridge Mix Vol.2", "emoji": "🎤🔥"},
            {"genero": "RnB", "tipo": "set", "tema": "Late Night R&B", "emoji": "🌙"},
        ],
        "reels": [
            {"genero": "RnB", "tema": "R&B hit", "emoji": "🎵"},
            {"genero": "Reggaeton", "tema": "Latin x English", "emoji": "🌎"},
            {"genero": "Hip Hop Night Club", "tema": "Classic hip-hop", "emoji": "🎤"},
            {"genero": "Reggaeton", "tema": "Drop trending", "emoji": "🔥"},
            {"genero": "RnB", "tema": "Smooth R&B clip", "emoji": "🎵"},
            {"genero": "Afrobeats", "tema": "Afro moment", "emoji": "🌍"},
            {"genero": "Hip Hop Night Club", "tema": "Throwback hip-hop", "emoji": "🎤"},
            {"genero": "RnB", "tema": "Late night vibe", "emoji": "🌙"},
        ],
    },
}


def cargar_estado() -> dict:
    """Carga el estado del calendario desde JSON."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"volumenes": {}, "semanas_completadas": [], "tracks_usados": []}


def guardar_estado(estado: dict):
    """Guarda el estado del calendario."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def obtener_volumen(estado: dict, genero: str) -> int:
    """Obtiene y incrementa el número de volumen para un género."""
    vols = estado.setdefault("volumenes", {})
    vol = vols.get(genero, 0) + 1
    vols[genero] = vol
    return vol


def determinar_fase(semana_num: int) -> int:
    """Determina la fase según el número de semana."""
    if semana_num <= 8:
        return 1
    elif semana_num <= 16:
        return 2
    elif semana_num <= 24:
        return 3
    else:
        return 4


def generar_calendario(semanas: int, fecha_inicio: datetime, fase_override: int = None):
    """Genera el calendario de contenido."""
    estado = cargar_estado()
    calendario = []

    print()
    print(f"  ╔{'═' * 78}╗")
    print(f"  ║  📅  CALENDARIO DE CONTENIDO — {semanas} SEMANAS{' ' * (78 - 42 - len(str(semanas)))}║")
    print(f"  ║  📆  Inicio: {fecha_inicio.strftime('%Y-%m-%d')}{' ' * 57}║")
    print(f"  ╚{'═' * 78}╝")

    fase_actual = None

    for i in range(semanas):
        fecha = fecha_inicio + timedelta(weeks=i)
        sem_num = i + 1
        fase_num = fase_override or determinar_fase(sem_num)
        fase = FASES[fase_num]

        # Imprimir encabezado de fase si cambió
        if fase_num != fase_actual:
            fase_actual = fase_num
            print(f"\n  {fase['emoji']} ═══ FASE {fase_num}: {fase['nombre']} (Meses {fase['meses']}) ═══")

        # Seleccionar set y reel de la rotación
        idx_set = i % len(fase["sets"])
        idx_reel = i % len(fase["reels"])
        set_info = fase["sets"][idx_set]
        reel_info = fase["reels"][idx_reel]

        # Obtener volumen
        vol = obtener_volumen(estado, set_info["tema"])

        # Construir entrada del calendario
        entrada = {
            "semana": sem_num,
            "fecha": fecha.strftime("%Y-%m-%d"),
            "fase": fase_num,
            "fase_nombre": fase["nombre"],
            "set": {
                "genero": set_info["genero"],
                "tipo": set_info["tipo"],
                "tema": f"{set_info['tema']} Vol.{vol}",
                "emoji": set_info["emoji"],
            },
            "reel": {
                "genero": reel_info["genero"],
                "tema": reel_info["tema"],
                "emoji": reel_info["emoji"],
            },
        }
        calendario.append(entrada)

        # Imprimir
        fecha_str = fecha.strftime("%d %b")
        print(f"  │ Sem {sem_num:>2} │ {fecha_str} │ "
              f"🎧 {set_info['emoji']} {entrada['set']['tema']:<42} │ "
              f"📱 {reel_info['emoji']} {reel_info['tema']:<20} │")

    # Guardar
    estado["calendario"] = calendario
    guardar_estado(estado)

    cal_file = Path(__file__).parent / "content_calendar.json"
    with open(cal_file, "w", encoding="utf-8") as f:
        json.dump(calendario, f, ensure_ascii=False, indent=2)

    print(f"\n  {'═' * 78}")
    print(f"  📦 Calendario de {semanas} semanas generado")
    print(f"  💾 Guardado en: {cal_file}")
    print(f"  💾 Estado en: {STATE_FILE}")
    print(f"\n  ✅ ¡Calendario listo! 📅\n")


def mostrar_siguiente():
    """Muestra la sugerencia para la próxima semana."""
    estado = cargar_estado()
    cal = estado.get("calendario", [])
    completadas = estado.get("semanas_completadas", [])

    if not cal:
        print("\n  ⚠️  No hay calendario generado. Ejecuta 'generate' primero.\n")
        return

    # Encontrar la próxima semana no completada
    siguiente = None
    for entrada in cal:
        if entrada["semana"] not in completadas:
            siguiente = entrada
            break

    if not siguiente:
        print("\n  🎉 ¡Todas las semanas del calendario están completadas!\n")
        return

    print()
    print(f"  ╔{'═' * 60}╗")
    print(f"  ║  📅  PRÓXIMA SEMANA: {siguiente['fecha']}{' ' * (60 - 24 - len(siguiente['fecha']))}║")
    print(f"  ║  🏷️  Fase {siguiente['fase']}: {siguiente['fase_nombre']}{' ' * (60 - 14 - len(str(siguiente['fase'])) - len(siguiente['fase_nombre']))}║")
    print(f"  ╠{'═' * 60}╣")
    print(f"  ║  🎧 SET YOUTUBE:{' ' * 44}║")
    s = siguiente['set']
    tema_line = f"     {s['emoji']} {s['tema']}"
    print(f"  ║{tema_line}{' ' * (60 - len(tema_line))}║")
    genero_line = f"     Género: {s['genero']} | Tipo: {s['tipo']}"
    print(f"  ║{genero_line}{' ' * (60 - len(genero_line))}║")
    print(f"  ║{' ' * 60}║")
    print(f"  ║  📱 REEL:{' ' * 50}║")
    r = siguiente['reel']
    reel_line = f"     {r['emoji']} {r['tema']}"
    print(f"  ║{reel_line}{' ' * (60 - len(reel_line))}║")
    reel_g = f"     Género: {r['genero']}"
    print(f"  ║{reel_g}{' ' * (60 - len(reel_g))}║")
    print(f"  ╚{'═' * 60}╝")

    print(f"\n  💡 Comandos sugeridos:")
    g = s['genero'].split(',')[0]
    dur = 50 if s['tipo'] == 'set' else 40
    if s['tipo'] == 'crossover':
        print(f'     python tracklist_engine.py crossover --genres "{s["genero"]}" --duration {dur}')
    else:
        print(f'     python tracklist_engine.py set --genre "{g}" --duration {dur}')
    print(f'     python tracklist_engine.py reel --genre "{r["genero"]}" --count 8')
    print()


def mostrar_estado():
    """Muestra el estado actual del calendario."""
    estado = cargar_estado()
    cal = estado.get("calendario", [])
    completadas = estado.get("semanas_completadas", [])
    vols = estado.get("volumenes", {})

    print()
    print(f"  ╔{'═' * 50}╗")
    print(f"  ║  📊  ESTADO DEL CALENDARIO{' ' * 23}║")
    print(f"  ╠{'═' * 50}╣")
    print(f"  ║  Semanas planificadas: {len(cal):>4}{' ' * 21}║")
    print(f"  ║  Semanas completadas:  {len(completadas):>4}{' ' * 21}║")
    print(f"  ║  Semanas pendientes:   {len(cal) - len(completadas):>4}{' ' * 21}║")
    print(f"  ╚{'═' * 50}╝")

    if vols:
        print(f"\n  📦 Volúmenes por tema:")
        for tema, vol in sorted(vols.items()):
            print(f"     {tema}: Vol.{vol}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="📅 Calendario de contenido DJ con rotación de géneros",
    )
    sub = parser.add_subparsers(dest="comando", help="Comando a ejecutar")

    # generate
    gen = sub.add_parser("generate", help="Genera un calendario de N semanas")
    gen.add_argument("--weeks", type=int, default=12, help="Número de semanas (default: 12)")
    gen.add_argument("--start-date", type=str, default=None,
                     help="Fecha de inicio YYYY-MM-DD (default: próximo lunes)")
    gen.add_argument("--phase", type=int, default=None, choices=[1, 2, 3, 4],
                     help="Forzar una fase específica (1-4)")

    # next
    sub.add_parser("next", help="Muestra la próxima semana")

    # status
    sub.add_parser("status", help="Muestra el estado actual")

    args = parser.parse_args()

    if args.comando == "generate":
        if args.start_date:
            fecha = datetime.strptime(args.start_date, "%Y-%m-%d")
        else:
            hoy = datetime.now()
            dias_hasta_lunes = (7 - hoy.weekday()) % 7
            if dias_hasta_lunes == 0:
                dias_hasta_lunes = 7
            fecha = hoy + timedelta(days=dias_hasta_lunes)

        generar_calendario(args.weeks, fecha, args.phase)

    elif args.comando == "next":
        mostrar_siguiente()

    elif args.comando == "status":
        mostrar_estado()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
