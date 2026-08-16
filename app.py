#!/usr/bin/env python3
"""
app.py — JordanDJ AI Suite: Dashboard Web Visual e Interactivo.

Interfaz moderna en Streamlit para el control total de la curaduría musical,
generación de sets, visualización armónica, detección viral e inyección
directa de Crates en Serato DJ Pro.

Ejecutar:
    streamlit run app.py
"""

import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="JordanDJ AI Suite",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent
PALETAS_DIR = BASE_DIR / "paletas"
CSV_PATH = Path(r"D:\DJ\analisis\biblioteca_v3.csv")
VIRAL_JSON = BASE_DIR / "viral_trends.json"
CALENDAR_JSON = BASE_DIR / "content_calendar.json"

# Estilos CSS personalizados (Dark Theme Pro DJ)
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button {
        background: linear-gradient(90deg, #ff4b4b 0%, #ff758c 100%);
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.4);
    }
    .metric-card {
        background: #1a1c23;
        border: 1px solid #2d3139;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .block-header {
        font-size: 18px;
        font-weight: bold;
        padding: 8px 12px;
        border-radius: 6px;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    .block-intro { background: rgba(46, 204, 113, 0.2); border-left: 4px solid #2ecc71; color: #2ecc71; }
    .block-build { background: rgba(241, 196, 15, 0.2); border-left: 4px solid #f1c40f; color: #f1c40f; }
    .block-peak { background: rgba(231, 76, 60, 0.2); border-left: 4px solid #e74c3c; color: #e74c3c; }
    .block-cooldown { background: rgba(52, 152, 219, 0.2); border-left: 4px solid #3498db; color: #3498db; }
    .block-wildcard { background: rgba(155, 89, 182, 0.2); border-left: 4px solid #9b59b6; color: #9b59b6; }
</style>
""", unsafe_allow_html=True)


def ejecutar_script(script_name: str, args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un script auxiliar de Python."""
    cmd = [sys.executable, str(BASE_DIR / script_name)] + args
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=BASE_DIR
    )
    return res.returncode, res.stdout, res.stderr


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=600&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("🎧 JordanDJ AI Suite")
    st.caption("Sistema Autónomo de Curaduría & Producción")
    st.divider()

    # Estado del disco D:
    d_exists = CSV_PATH.exists()
    st.markdown(f"**Biblioteca:** {'🟢 Conectada (D:)' if d_exists else '🔴 Desconectada'}")
    if d_exists:
        try:
            st.caption(f"📍 `D:\\DJ\\Music`")
        except:
            pass

    st.divider()
    st.markdown("### ⚡ Acciones Rápidas")
    if st.button("📂 Abrir Carpeta de Música (D:)", use_container_width=True):
        if os.name == "nt":
            os.startfile(r"D:\DJ\Music")

    if st.button("🤖 Abrir Nuevos_DJTools", use_container_width=True):
        p = Path(r"D:\DJ\Music\Nuevos_DJTools")
        p.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(p)


# ---------------------------------------------------------
# TABS PRINCIPALES
# ---------------------------------------------------------
tab_studio, tab_camelot, tab_viral, tab_calendar, tab_marketing = st.tabs([
    "🎚️ Estudio de Sets & Reels",
    "📊 Curva de Energía & Camelot",
    "🌐 Radar de Tendencias Virales",
    "📅 Calendario & Roadmap 4 Fases",
    "🎬 Marketing & YouTube Copy",
])


# ---------------------------------------------------------
# TAB 1: ESTUDIO DE SETS & REELS
# ---------------------------------------------------------
with tab_studio:
    st.header("🎚️ Generador Inteligente de Sets y Reels")
    st.write("Genera paletas musicales optimizadas con mezcla armónica y prepara tus Crates para Serato DJ.")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        tipo_set = st.selectbox(
            "Tipo de Contenido:",
            ["Set Largo (YouTube)", "Reel Viral (Instagram / TikTok)", "Set Crossover Multi-Género"],
        )

    with col2:
        generos_disponibles = [
            "Reggaeton", "Bachata", "SALSA", "Merengue", "Hip Hop Night Club",
            "RnB", "Cumbia", "Dembow", "Afrobeats", "FUNK NV", "Musica Mexicana"
        ]
        if tipo_set == "Set Crossover Multi-Género":
            generos_sel = st.multiselect(
                "Selecciona 2 Géneros:",
                generos_disponibles,
                default=["Hip Hop Night Club", "Reggaeton"],
                max_selections=2
            )
            genero_final = ",".join(generos_sel)
        else:
            genero_final = st.selectbox("Género Principal:", generos_disponibles, index=0)

    with col3:
        if "Reel" in tipo_set:
            duracion = st.slider("Cantidad de Canciones para el Reel:", min_value=4, max_value=12, value=8)
            vibra = ""
        else:
            duracion = st.slider("Duración del Set (Minutos):", min_value=15, max_value=60, value=30, step=5)
            vibra = st.text_input("Vibra / Mood (Opcional):", placeholder="ej: perreo, romantico, clasico")

    st.markdown("<br>", unsafe_allow_html=True)
    btn_generar = st.button("🚀 Generar Paleta & Preparar Set", use_container_width=True)

    if btn_generar:
        with st.spinner("🧠 Analizando biblioteca, calculando compatibilidad Camelot y curva de energía..."):
            if "Reel" in tipo_set:
                args = ["reel", "--genre", genero_final, "--count", str(duracion)]
            elif "Crossover" in tipo_set:
                args = ["crossover", "--genres", genero_final, "--duration", str(duracion)]
            else:
                args = ["set", "--genre", genero_final, "--duration", str(duracion)]
                if vibra:
                    args.extend(["--vibra", vibra])

            code, out, err = ejecutar_script("tracklist_engine.py", args)

            if code == 0:
                st.success("✅ ¡Paleta generada exitosamente!")
            else:
                st.error(f"Error generando paleta: {err}")

    # Mostrar la última paleta generada
    paletas_existentes = list(PALETAS_DIR.glob("palette_*.json")) if PALETAS_DIR.exists() else []
    if paletas_existentes:
        ultima_paleta = max(paletas_existentes, key=lambda p: p.stat().st_mtime)
        with open(ultima_paleta, "r", encoding="utf-8") as f:
            data_paleta = json.load(f)

        meta = data_paleta.get("metadata", {})
        st.divider()
        st.subheader(f"📋 Paleta Activa: {meta.get('genero', 'Mix')} ({meta.get('tipo', 'set').upper()})")

        # Botón de inyección directa a Serato
        col_serato1, col_serato2 = st.columns([2, 1])
        with col_serato1:
            st.info(f"📂 Archivo de paleta: `{ultima_paleta.name}`")
        with col_serato2:
            if st.button("🎛️ Inyectar a Serato DJ", use_container_width=True):
                with st.spinner("Escribiendo crate en D:\\_Serato_ y C:\\_Serato_..."):
                    code, out, err = ejecutar_script("serato_crate_generator.py", ["--palette", str(ultima_paleta), "--force"])
                    if code == 0:
                        st.balloons()
                        st.success("🎉 ¡Crate inyectado directamente en Serato DJ! Abre Serato y estará listo.")
                    else:
                        st.error(f"Error inyectando en Serato: {err}")

        # Mostrar tracks organizados por bloques
        if "bloques" in data_paleta:
            bloques = data_paleta["bloques"]

            for nombre_bloque, items in bloques.items():
                if not items:
                    continue
                clase_css = f"block-{nombre_bloque.lower()}"
                st.markdown(f"<div class='block-header {clase_css}'>{nombre_bloque.upper()} ({len(items)} opciones)</div>", unsafe_allow_html=True)

                df_bloque = pd.DataFrame(items)
                cols_mostrar = ["titulo", "artista", "bpm", "key", "energy", "version", "popularidad", "trending"]
                cols_validas = [c for c in cols_mostrar if c in df_bloque.columns]

                st.dataframe(
                    df_bloque[cols_validas],
                    use_container_width=True,
                    hide_index=True
                )
        elif "opciones_reel" in data_paleta:
            st.markdown("<div class='block-header block-peak'>OPCIONES DE ALTO IMPACTO PARA REEL</div>", unsafe_allow_html=True)
            df_reel = pd.DataFrame(data_paleta["opciones_reel"])
            cols_mostrar = ["titulo", "artista", "bpm", "key", "energy", "version"]
            cols_validas = [c for c in cols_mostrar if c in df_reel.columns]
            st.dataframe(df_reel[cols_validas], use_container_width=True, hide_index=True)


# ---------------------------------------------------------
# TAB 2: VISUALIZADOR CAMELOT & ENERGÍA
# ---------------------------------------------------------
with tab_camelot:
    st.header("📊 Curva de Energía & Mezcla Armónica")
    st.write("Analiza visualmente la progresión dinámica de tu set antes de grabarlo.")

    paletas_existentes = list(PALETAS_DIR.glob("palette_*.json")) if PALETAS_DIR.exists() else []
    if paletas_existentes:
        ultima_paleta = max(paletas_existentes, key=lambda p: p.stat().st_mtime)
        with open(ultima_paleta, "r", encoding="utf-8") as f:
            data_paleta = json.load(f)

        tracks_all = []
        if "bloques" in data_paleta:
            for b_name, b_tracks in data_paleta["bloques"].items():
                for t in b_tracks:
                    t_copy = dict(t)
                    t_copy["bloque"] = b_name
                    tracks_all.append(t_copy)
        elif "opciones_reel" in data_paleta:
            tracks_all = data_paleta["opciones_reel"]

        if tracks_all:
            df_tracks = pd.DataFrame(tracks_all)

            col_g1, col_g2 = st.columns([1, 1])

            with col_g1:
                st.subheader("🎢 Curva de Energía Dinámica")
                fig_energy = px.line(
                    df_tracks,
                    y="energy",
                    hover_data=["titulo", "artista", "bpm", "key"],
                    title="Nivel de Energía a lo largo del Set (1-10)",
                    markers=True,
                    color_discrete_sequence=["#ff4b4b"]
                )
                fig_energy.update_layout(
                    template="plotly_dark",
                    yaxis=dict(range=[1, 10], title="Energía MIK"),
                    xaxis=dict(title="Progresión de Tracks")
                )
                st.plotly_chart(fig_energy, use_container_width=True)

            with col_g2:
                st.subheader("⏱️ Progresión de Velocidad (BPM)")
                fig_bpm = px.scatter(
                    df_tracks,
                    y="bpm",
                    color="key",
                    hover_data=["titulo", "artista", "energy"],
                    title="Distribución de Tempo (BPM) y Clave Camelot",
                    size=[12] * len(df_tracks),
                )
                fig_bpm.update_layout(
                    template="plotly_dark",
                    yaxis=dict(title="BPM"),
                    xaxis=dict(title="Pistas")
                )
                st.plotly_chart(fig_bpm, use_container_width=True)
    else:
        st.info("Genera una paleta en la pestaña 'Estudio' para ver sus gráficos armónicos.")


# ---------------------------------------------------------
# TAB 3: RADAR DE TENDENCIAS VIRALES
# ---------------------------------------------------------
with tab_viral:
    st.header("🌐 Radar de Tendencias Virales en Tiempo Real")
    st.write("Monitorea los éxitos de TikTok, Apple Music y Billboard Hot Latin Songs cruzados con tu catálogo.")

    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        if st.button("🔄 Escanear Tendencias Virales Ahora", use_container_width=True):
            with st.spinner("Consultando feeds de TikTok, Spotify y Billboard..."):
                code, out, err = ejecutar_script("viral_trend_scraper.py", [])
                if code == 0:
                    st.success("✅ ¡Tendencias actualizadas con éxito!")

    if VIRAL_JSON.exists():
        with open(VIRAL_JSON, "r", encoding="utf-8") as f:
            v_data = json.load(f)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hits Analizados", v_data.get("total_analizados", 0))
        m2.metric("Ya en tu Biblioteca", v_data.get("total_en_biblioteca", 0))
        m3.metric("Oportunidades Virales", v_data.get("total_faltantes", 0), delta=f"-{v_data.get('total_faltantes', 0)} faltantes", delta_color="inverse")
        m4.metric("Cobertura de Catálogo", f"{v_data.get('porcentaje_cobertura', 0)}%")

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🔥 Top Hits Virales que te Faltan Descargar:")

        faltantes = v_data.get("faltantes_virales", [])
        if faltantes:
            df_faltantes = pd.DataFrame(faltantes)
            st.dataframe(
                df_faltantes[["posicion", "titulo", "artista", "fuente"]],
                use_container_width=True,
                hide_index=True
            )

            col_dl1, col_dl2 = st.columns([2, 1])
            with col_dl2:
                if st.button("🤖 Descargar con Robot DJTools", use_container_width=True):
                    st.info("Lanzando Auto-Downloader en segundo plano...")
                    if os.name == "nt":
                        subprocess.Popen(
                            [sys.executable, str(BASE_DIR / "djtools_auto_downloader.py"), "--report", str(VIRAL_JSON)],
                            cwd=BASE_DIR,
                            creationflags=subprocess.CREATE_NEW_CONSOLE
                        )
                    st.success("Robot iniciado en una nueva ventana. ¡Revisa tu pantalla!")


# ---------------------------------------------------------
# TAB 4: CALENDARIO & ROADMAP
# ---------------------------------------------------------
with tab_calendar:
    st.header("📅 Calendario Estratégico & Roadmap (12 Semanas)")
    st.write("Plan de crecimiento en 4 fases para dominar tu audiencia local y expandirte internacionalmente.")

    if CALENDAR_JSON.exists():
        with open(CALENDAR_JSON, "r", encoding="utf-8") as f:
            cal_data = json.load(f)

        if isinstance(cal_data, list):
            semanas = cal_data
        elif isinstance(cal_data, dict):
            semanas = cal_data.get("semanas", [])
        else:
            semanas = []

        for sem in semanas:
            set_info = sem.get("set", sem.get("set_youtube", {}))
            reel_info = sem.get("reel", {})
            fase_txt = sem.get("fase_nombre", f"Fase {sem.get('fase', 1)}")
            tema_txt = set_info.get("tema", "Set Semanal")

            with st.expander(f"📍 Semana {sem.get('semana')}: {tema_txt} ({fase_txt})"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown("**🎬 Set YouTube:**")
                    st.write(f"• Género: `{set_info.get('genero', 'Varios')}`")
                    st.write(f"• Duración: `{set_info.get('duracion_min', 30)} min`")
                    st.write(f"• Tema: `{set_info.get('tema', 'Mix')}`")
                with col_c2:
                    st.markdown("**📱 Reel / TikTok:**")
                    st.write(f"• Género: `{reel_info.get('genero', 'Varios')}`")
                    st.write(f"• Concepto: `{reel_info.get('tema', reel_info.get('concepto', 'Drop Viral'))}`")


# ---------------------------------------------------------
# TAB 5: MARKETING & YOUTUBE COPY
# ---------------------------------------------------------
with tab_marketing:
    st.header("🎬 Marketing Hub & Metadatos YouTube")
    st.write("Títulos SEO optimizados, timestamps automáticos y hashtags listos para copiar y pegar.")

    paletas_existentes = list(PALETAS_DIR.glob("palette_*.json")) if PALETAS_DIR.exists() else []
    if paletas_existentes:
        ultima_paleta = max(paletas_existentes, key=lambda p: p.stat().st_mtime)

        if st.button("📝 Regenerar Metadatos YouTube de la Paleta Activa"):
            code, out, err = ejecutar_script("youtube_metadata.py", ["--palette", str(ultima_paleta)])
            if code == 0:
                st.success("✅ Metadatos generados.")

        txt_files = list(PALETAS_DIR.glob("metadata_*.txt"))
        if txt_files:
            ultimo_txt = max(txt_files, key=lambda p: p.stat().st_mtime)
            contenido = ultimo_txt.read_text(encoding="utf-8", errors="replace")
            st.text_area("Contenido Completo (Copiar y Pegar en YouTube):", contenido, height=450)
    else:
        st.info("Genera un set primero para ver los metadatos de YouTube.")
