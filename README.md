# 🎧 JordanDJ Content Automation System

Sistema automatizado integral de curaduría musical, producción de sets para YouTube, creación de Reels virales, inyección directa de crates en **Serato DJ Pro** y descarga automática de música en **DJTools.vip**.

---

## 📁 Ubicación del Proyecto
El código reside en tu computadora en:
```text
C:\Users\jorda\.gemini\antigravity\scratch\jordandj_content\
```

---

## 🏛️ Arquitectura del Sistema

```text
                                 [ biblioteca_v3.csv ]
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│ gap_analyzer.py  │             │ trend_detector.py│             │content_calendar  │
│ (Auditoría Gaps) │             │ (Tendencias Top) │             │(Roadmap 12 Sem)  │
└────────┬─────────┘             └────────┬─────────┘             └──────────────────┘
         │                                │
         └────────────────┬───────────────┘
                          ▼
            ┌───────────────────────────┐
            │ djtools_auto_downloader.py│ ────▶ [ D:\DJ\Music\Nuevos_DJTools ]
            │ (Descarga Automática MP3) │
            └───────────────────────────┘
                          │
                          ▼
            ┌───────────────────────────┐
            │   tracklist_engine.py     │
            │ (Curva Energía + Camelot) │
            └─────────────┬─────────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│ serato_crate_generator.py │   │    youtube_metadata.py    │
│  (Inyección Crates D: y C:)│  │ (Títulos, Timestamps, Tags)│
└───────────────────────────┘   └───────────────────────────┘
```

---

## 🚀 Módulos y Comandos

### 1. Orquestador Maestro Todo-en-Uno (`pipeline.py`)
Ejecuta todo el flujo (paleta + Serato crate + metadata YouTube) en una sola línea:
```bash
# Set para YouTube
python pipeline.py set --genre Reggaeton --duration 40 --vibra perreo

# Reel para Instagram / TikTok
python pipeline.py reel --genre Reggaeton --count 8

# Set Crossover multi-género
python pipeline.py crossover --genres "Hip Hop Night Club,Reggaeton" --duration 40
```

### 2. Generador de Paletas Creativas (`tracklist_engine.py`)
Aplica mezcla armónica (Camelot Wheel) y curvas de energía (Intro → Build → Peak → Cooldown).
```bash
python tracklist_engine.py set --genre Reggaeton --duration 50
python tracklist_engine.py reel --genre Reggaeton --count 8
python tracklist_engine.py crossover --genres "Hip Hop Night Club,Reggaeton" --duration 40
```

### 3. Generador de Crates Serato (`serato_crate_generator.py`)
Inyecta crates binarios nativos en `D:\_Serato_\Subcrates\` y `C:\Users\jorda\Music\_Serato_\Subcrates\` organizados en subcarpetas:
- `YOUTUBE_SETS` (Contenido Largo)
- `REELS_TIKTOK` (Contenido Corto)
```bash
python serato_crate_generator.py --palette paletas/palette.json --force
```

### 4. Robot de Descargas Automáticas (`djtools_auto_downloader.py`)
Inicia sesión en DJTools, busca los top artistas de tus géneros débiles y descarga versiones exclusivas para DJ (Intro, Outro, Open Show, Dirty):
```bash
python djtools_auto_downloader.py
```

### 5. Auditor de Carencias (`gap_analyzer.py`)
```bash
python gap_analyzer.py
```

### 6. Detector de Tendencias (`trend_detector.py`)
```bash
python trend_detector.py --output trend_report.json
```

### 7. Calendario de Contenido y Roadmap 4 Fases (`content_calendar.py`)
```bash
python content_calendar.py generate --weeks 12
python content_calendar.py next
python content_calendar.py status
```

### 8. Generador de Metadatos YouTube (`youtube_metadata.py`)
```bash
python youtube_metadata.py --palette paletas/palette.json --vol 1
```

---

## 🔒 Seguridad de Credenciales
Tus credenciales de DJTools están protegidas en el archivo local `.env` (ignorado por Git):
```env
DJTOOLS_USER=tu_correo@ejemplo.com
DJTOOLS_PASS=tu_contraseña
```
