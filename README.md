# 🎧 JordanDJ Content Automation Suite v2.0

Sistema automatizado integral con **Dashboard Web Visual**, curaduría musical asistida por IA, producción de sets para YouTube, creación de Reels virales, inyección directa de crates en **Serato DJ Pro** y descarga automática de música en **DJTools.vip**.

---

## 📁 Ubicación del Proyecto
El código reside en tu computadora en:
```text
C:\Users\jorda\.gemini\antigravity\scratch\jordandj_content\
```

---

## 🖥️ Nuevo: Dashboard Web Visual (`app.py`)
Para abrir el centro de control visual en tu navegador:
```bash
streamlit run app.py
```
**Incluye:**
- 🎚️ **Estudio de Sets & Reels:** Sliders de duración, selector de género y botón de 1 clic para inyectar directo a Serato.
- 📊 **Visualizador Camelot & Energía:** Gráficos dinámicos interactivos con Plotly.
- 🌐 **Radar de Tendencias Virales:** Escaneo en tiempo real de TikTok, Apple Music y Billboard con descarga en 1 clic.
- 📅 **Calendario & Roadmap:** Vista completa del plan de 12 semanas en 4 fases.
- 🎬 **Marketing Hub:** Títulos, descripciones y hashtags listos para copiar.

---

## 🌐 Nuevo: Scraper de Tendencias Virales en Vivo (`viral_trend_scraper.py`)
Consulta las listas públicas de éxitos virales (Top 50 Latino de Apple Music y Billboard Hot Latin) y las cruza en tiempo real con tu biblioteca:
```bash
python viral_trend_scraper.py
```

---

## 🚀 Módulos de Consola y Pipeline

### 1. Orquestador Maestro Todo-en-Uno (`pipeline.py`)
```bash
# Set para YouTube
python pipeline.py set --genre Reggaeton --duration 40 --vibra perreo

# Reel para Instagram / TikTok
python pipeline.py reel --genre Reggaeton --count 8

# Set Crossover multi-género
python pipeline.py crossover --genres "Hip Hop Night Club,Reggaeton" --duration 40
```

### 2. Generador de Paletas Creativas (`tracklist_engine.py`)
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
Inicia sesión en DJTools, busca los top artistas de tus géneros débiles o tendencias virales y descarga versiones exclusivas para DJ:
```bash
python djtools_auto_downloader.py
python djtools_auto_downloader.py --report viral_trends.json
```

### 5. Auditor de Carencias (`gap_analyzer.py`)
```bash
python gap_analyzer.py
```

### 6. Detector de Tendencias Locales (`trend_detector.py`)
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
