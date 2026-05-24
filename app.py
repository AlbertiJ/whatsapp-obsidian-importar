# -*- coding: utf-8 -*-
"""
WhatsApp Chat Importer — Streamlit Web Application
Allows uploading RAR files containing WhatsApp chat exports,
extracts content, parses messages, and generates Obsidian-compatible
Markdown files with embedded media references.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st
import subprocess
import platform

from parser import parse_chat_text, discover_chat_files, sanitize_filename, detect_file_type


# ── Configuration ────────────────────────────────────────────────────────────

DEFAULT_VAULT = ""
OUTPUT_SUBDIR = "WhatsAppImport"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
AUDIO_EXTS = {".mp3", ".opus", ".ogg", ".m4a", ".aac", ".wav", ".amr"}
VIDEO_EXTS = {".mp4", ".3gp", ".mkv", ".avi", ".mov", ".webm"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def safe_copy(src: str, dst: str) -> bool:
    """Copy file, renaming on conflict. Returns True if successful."""
    try:
        if os.path.exists(dst):
            name, ext = os.path.splitext(dst)
            dst = f"{name}_副本{ext}"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        st.warning(f"No se pudo copiar {src}: {e}")
        return False


def check_7z_installed() -> bool:
    """Check if 7-Zip is installed and in PATH."""
    try:
        result = subprocess.run(
            ["7z", "--help"], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        return result.returncode in (0, 1)  # 0 = help shown, 1 = no files specified
    except FileNotFoundError:
        return False
    except Exception:
        return False


def extract_archive(archive_path: str, dest_dir: str) -> str:
    """Auto-detect format and extract using 7z command line tool."""
    ext = Path(archive_path).suffix.lower()
    
    # First check if 7z is available
    if not check_7z_installed():
        raise RuntimeError(
            "❌ 7-Zip no encontrado.\n\n"
            "Esta app necesita 7-Zip para extraer archivos RAR/ZIP.\n\n"
            "📥 Instalalo gratis desde: https://www.7-zip.org/\n"
            "Después de instalar, cerrá y reabrí la terminal (PowerShell) para que se actualice el PATH."
        )
    
    # Build 7z command (works for both RAR and ZIP)
    cmd = ["7z", "x", "-y", f"-o{dest_dir}", archive_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Error desconocido"
            raise RuntimeError(f"Error al extraer con 7z:\n{error_msg}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("❌ La extracción tardó demasiado. ¿El archivo es muy grande?")
    except FileNotFoundError:
        raise RuntimeError(
            "❌ 7z.exe no encontrado.\n"
            "Verificá que 7-Zip esté instalado y en el PATH del sistema."
        )
    
    return dest_dir


def collect_media(extracted_dir: str, media_dir: str) -> dict[str, int]:
    """Copy all media files to media_dir. Returns copy stats."""
    stats = {"copied": 0, "skipped": 0}
    for root, _dirs, files in os.walk(extracted_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            ext = Path(fname).suffix.lower()
            if ext in IMAGE_EXTS or ext in AUDIO_EXTS or ext in VIDEO_EXTS:
                dst = os.path.join(media_dir, fname)
                if safe_copy(fpath, dst):
                    stats["copied"] += 1
                else:
                    stats["skipped"] += 1
    return stats


def build_preview_html(sessions: list, max_messages: int = 50) -> str:
    """Build a simple HTML preview of the parsed chat sessions."""
    html_parts = ['<div style="font-family: monospace; font-size: 13px; background: #111827; color: #e5e7eb; padding: 16px; border-radius: 8px;">']

    for session in sessions:
        html_parts.append(
            f'<div style="margin-bottom: 16px; padding: 10px; background: #1f2937; border-radius: 6px;">'
            f'<strong style="color: #60a5fa;">📱 {session.contact_name}</strong>'
            f'<span style="color: #9ca3af; font-size: 12px;"> — {session.stats["total"]} msgs</span>'
        )
        for msg in session.messages[:max_messages]:
            media_tag = ""
            if msg.media_file:
                ft = detect_file_type(msg.media_file)
                if ft == "image":
                    media_tag = f' <span style="color: #fbbf24;">🖼️ {msg.media_file}</span>'
                elif ft == "audio":
                    media_tag = f' <span style="color: #a78bfa;">🎤 {msg.media_file}</span>'
                elif ft == "video":
                    media_tag = f' <span style="color: #f87171;">🎬 {msg.media_file}</span>'
            cls = "#6b7280" if msg.is_system else "#d1d5db"
            html_parts.append(
                f'<div style="color: {cls}; margin: 4px 0;">'
                f'<span style="color: #9ca3af; font-size: 11px;">[{msg.timestamp}]</span> '
                f'<span style="color: #34d399;">{msg.sender}</span>: '
                f'{msg.content or media_tag}'
                f'</div>'
            )
        html_parts.append("</div>")

    html_parts.append("</div>")
    return "\n".join(html_parts)


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="WhatsApp Chat Importer",
        page_icon="💬",
        layout="centered",
    )

    # Custom CSS
    st.markdown("""
    <style>
    .stApp { background-color: #0f172a; }
    h1, h2, h3 { color: #f1f5f9; }
    .stTextInput > div > div > input,
    .stFileUploader > div > div > div {
        background-color: #1e293b;
        color: #f1f5f9;
        border-color: #334155;
    }
    .stButton > button {
        background-color: #3b82f6;
        color: white;
        border: none;
        font-weight: 600;
    }
    .stButton > button:hover { background-color: #2563eb; }
    .stSuccess { color: #4ade80; }
    .stWarning { color: #fbbf24; }
    .stInfo { color: #60a5fa; }
    </style>
    """, unsafe_allow_html=True)

    st.title("💬 WhatsApp Chat Importer")
    st.markdown("Subí un archivo RAR (o ZIP) exportado desde WhatsApp y generá notas Obsidian con tus chats.")

    # ── Step 1: Output vault ──────────────────────────────────────────────────
    st.markdown("### 📁 Bóveda de salida")
    vault_path = st.text_input(
        "Ruta de la bóveda Obsidian",
        value=DEFAULT_VAULT,
        help="Carpeta donde se guardarán los archivos generados."
    )

    output_subdir = st.text_input(
        "Subcarpeta de salida",
        value=OUTPUT_SUBDIR,
        help="Se creará dentro de la bóveda."
    )

    # ── Step 2: Upload ────────────────────────────────────────────────────────
    st.markdown("### 📦 Subir archivo")
    
    # Pre-check: verify 7z is available
    if not check_7z_installed():
        st.error(
            "⚠️ **7-Zip no instalado**\n\n"
            "Esta app necesita 7-Zip para extraer archivos RAR/ZIP.\n\n"
            "📥 [Descargalo de 7-zip.org](https://www.7-zip.org/) e instalalo.\n"
            "Después de instalar, **cerrá y reabrí esta terminal** y volvé a ejecutar `streamlit run app.py`."
        )
        st.stop()
    
    uploaded_file = st.file_uploader(
        "Arrastrá o seleccioná un archivo RAR / ZIP",
        type=["rar", "zip"],
        help="Archivo exportado desde WhatsApp.",
    )

    # ── Step 3: Process ───────────────────────────────────────────────────────
    if uploaded_file is not None:
        st.markdown("---")
        st.markdown("### 🔍 Procesando...")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Save uploaded file
            archive_path = os.path.join(tmp_dir, uploaded_file.name)
            with open(archive_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Extract
            try:
                with st.spinner("Extrayendo archivo..."):
                    extract_dir = os.path.join(tmp_dir, "extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    extract_archive(archive_path, extract_dir)
                st.success("✅ Archivo extraído correctamente.")
            except Exception as e:
                st.error(f"❌ Error al extraer: {e}")
                return

            # Discover files
            discovered = discover_chat_files(extract_dir)
            chat_files = discovered["chats"]

            if not chat_files:
                st.warning("⚠️ No se encontraron archivos .txt de chat en el RAR.")
                # List discovered files for debugging
                all_files = []
                for root, _dirs, files in os.walk(extract_dir):
                    for fname in files:
                        all_files.append(os.path.join(root, fname))
                if all_files:
                    st.info(f"Archivos detectados: {all_files[:20]}")
                return

            # ── Step 4: Preview ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### 👁️ Vista previa")

            all_sessions = []
            for chat_path in chat_files:
                with open(chat_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                sessions = parse_chat_text(text)
                all_sessions.extend(sessions)

            if not all_sessions:
                st.warning("⚠️ No se detectaron mensajes con el formato esperado.")
                return

            # Show sessions summary
            cols = st.columns(len(all_sessions))
            for i, session in enumerate(all_sessions):
                with cols[i]:
                    st.metric(
                        label=session.contact_name[:20],
                        value=f"{session.stats['total']} msgs",
                        delta=f"{session.stats['images']} 🖼 {session.stats['audio']} 🎤"
                    )

            # HTML preview
            preview_html = build_preview_html(all_sessions)
            st.markdown("#### Mensajes")
            st.markdown(preview_html, unsafe_allow_html=True)

            # Statistics
            st.markdown("#### 📊 Estadísticas")
            total_msgs = sum(s.stats["total"] for s in all_sessions)
            total_imgs = sum(s.stats["images"] for s in all_sessions)
            total_auds = sum(s.stats["audio"] for s in all_sessions)
            total_vids = sum(s.stats["video"] for s in all_sessions)
            total_sys = sum(s.stats["system"] for s in all_sessions)

            stat_cols = st.columns(5)
            metric_data = [
                ("Mensajes totales", total_msgs),
                ("Fotos", total_imgs),
                ("Audios", total_auds),
                ("Videos", total_vids),
                ("Mensajes de sistema", total_sys),
            ]
            for i, (label, value) in enumerate(metric_data):
                with stat_cols[i]:
                    st.metric(label=label, value=value)

            # ── Step 5: Export ────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### 💾 Exportar a Obsidian")

            if st.button("📝 Generar archivos .md en la bóveda", use_container_width=True):
                # Build output paths
                base_out = os.path.join(vault_path, output_subdir)

                for session in all_sessions:
                    # Sanitize contact name for folder
                    safe_name = sanitize_filename(session.contact_name)
                    session_dir = os.path.join(base_out, safe_name)
                    os.makedirs(session_dir, exist_ok=True)

                    # Copy media
                    media_dir = os.path.join(session_dir, "media")
                    os.makedirs(media_dir, exist_ok=True)
                    collect_media(extract_dir, media_dir)

                    # Write .md
                    md_path = os.path.join(session_dir, f"{safe_name}.md")
                    md_content = session.to_markdown()
                    with open(md_path, "w", encoding="utf-8") as f:
                        f.write(md_content)

                st.success(
                    f"✅ Generados {len(all_sessions)} archivos .md "
                    f"en `{os.path.abspath(base_out)}`"
                )

                # Show generated files
                for session in all_sessions:
                    safe_name = sanitize_filename(session.contact_name)
                    st.code(
                        f"{os.path.join(base_out, safe_name, safe_name + '.md')}",
                        language="markdown",
                    )


if __name__ == "__main__":
    main()