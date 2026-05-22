# WhatsApp Chat Importer

Importa chats de WhatsApp exportados como archivos RAR/ZIP y genera notas Obsidian con formato Markdown + YAML frontmatter y embeds de medios.

---

## Requisitos

- Python 3.10+
- [7-Zip](https://www.7-zip.org/) instalado y en el `PATH` del sistema
  (necesario para extraer archivos RAR con `pyunrar` o vía subprocess)
- Bóveda Obsidian local (configurable en la app)

> **¿Por qué 7-Zip?** La librería `rarfile` de Python no incluye el código de
> extracción RAR (licencia shareware). Usar 7-Zip permite extraer sin instalar
> WinRAR ni unrar.exe propietario.

---

## Instalación

```bash
# 1. Clonar o copiar este directorio
cd whatsapp-importer

# 2. Crear entorno virtual (recomendado)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Instalación de 7-Zip (si no está en PATH)

1. Descargá [7-Zip](https://www.7-zip.org/) e instalalo.
2. Agregá la carpeta de instalación al PATH:
   ```
   Panel de Control > Sistema > Variables de entorno > PATH > Editar
   ```
   Agregá: `C:\Program Files\7-Zip` (o donde lo hayas instalado).

---

## Uso

```bash
streamlit run app.py
```

La aplicación se abrirá en el navegador en `http://localhost:8501`.

### Pasos

1. **Configurá la bóveda** — ruta donde se guardarán los archivos `.md`
2. **Subí el archivo RAR/ZIP** — exportado desde WhatsApp (`Chat > ⋮ > Exportar`)
3. **Revisá la vista previa** — se muestra un resumen con estadísticas y mensajes
4. **Hacé clic en "Generar archivos .md"** — se crean las notas en la bóveda

---

## Formato de salida

Cada chat genera:

```
Bovedamobil/WhatsAppImport/<Contacto>/
├── <Contacto>.md          ← Nota Obsidian
└── media/
    ├── imagen1.jpg        ← Fotos
    └── audio1.mp3         ← Audios
```

### Frontmatter YAML

```yaml
---
title: Chat Nombre del Contacto
date: 2026-05-21
contact: Nombre del Contacto
tags: [whatsapp, chat, importado]
---
```

### Mensajes en Obsidian

```markdown
- **[DD/MM/YYYY HH:MM:SS]** Remitente: Contenido del mensaje
- **[DD/MM/YYYY HH:MM:SS]** Remitente: ![](media/foto.jpg)
- **[DD/MM/YYYY HH:MM:SS]** Remitente: [🎤 audio.mp3](media/audio.mp3)
```

---

## Formatos soportados

| Tipo | Formatos |
|------|----------|
| Mensajes de texto | Todos los caracteres Unicode, emojis |
| Fotos | `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` |
| Audios | `.mp3`, `.opus`, `.ogg`, `.m4a`, `.aac`, `.wav` |
| Videos | `.mp4`, `.3gp`, `.mkv` |
| Archivos comprimidos | `.rar`, `.zip` |

### Formato de chat esperado

WhatsApp exporta en formato:

```
[DD/MM/YYYY HH:MM:SS] Contacto: Mensaje de texto
[DD/MM/YYYY HH:MM:SS] Contacto: Foto
[DD/MM/YYYY HH:MM:SS] Contacto: Audio
[DD/MM/YYYY HH:MM:SS] Contacto: <Media omitted>
```

---

## Solución de problemas

### "streamlit no se reconoce como comando"

Si aparece este error después de instalar:
```
"streamlit" no se reconoce como un comando interno o externo...
```

Significa que pip instaló los scripts en una carpeta que no está en tu PATH. Solución rápida:

```powershell
# Opción 1: Ejecutar con la ruta completa
& "$env:APPDATA\Python\Python<VERSION>\Scripts\streamlit.exe" run app.py

# Opción 2: Agregar Scripts al PATH (temporal para esta sesión)
$env:PATH += ";$env:APPDATA\Python\Python<VERSION>\Scripts"
streamlit run app.py
```

Reemplazá `<VERSION>` con tu versión de Python (ej: `Python312`, `Python314`).

**Opción 3 (permanente):** Agregá la carpeta al PATH del sistema:
1. Panel de Control → Sistema → Variables de entorno → PATH → Editar
2. Agregá: `%APPDATA%\Python\Python<VERSION>\Scripts`

O simplemente reinstalá Python marcando "Add Python to PATH" durante la instalación.

### "No se encontraron archivos .txt"

- El RAR debe contener los `.txt` exportados directamente (sin carpeta extra).
- Algunos exports vienen con estructura `WhatsApp Chat with X.txt`.

### "No se detectaron mensajes"

- El parser espera el formato `[DD/MM/YYYY HH:MM:SS] Contacto: Mensaje`.
- Si tu exportación usa otro formato (24h vs 12h, otro separador), ajustá
  la regex en `parser.py`.

---

## Estructura del proyecto

```
whatsapp-importer/
├── app.py           # Aplicación Streamlit
├── parser.py        # Módulo de parsing de chat
├── requirements.txt # Dependencias Python
├── README.md        # Este archivo
└── .gitignore
```

---

## Licencia

MIT License — usalo libremente, modificálo, compartilo.

```
MIT License

Copyright (c) 2026 WhatsApp Chat Importer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```