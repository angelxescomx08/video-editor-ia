# 🎬 Video Editor IA

Aplicación web local para automatizar la edición de videos de YouTube.  
Elimina silencios automáticamente y combina cortes inteligentes generados por Gemini Advanced.

---

## Requisitos previos

### 1. Python 3.10 o superior
Descarga desde [python.org](https://www.python.org/downloads/).  
Durante la instalación marca **"Add Python to PATH"**.

Verifica:
```powershell
python --version
```

### 2. FFmpeg
```powershell
winget install Gyan.FFmpeg
```
Cierra y vuelve a abrir la terminal después de instalarlo.

Verifica:
```powershell
ffmpeg -version
```

---

## Instalación

```powershell
# 1. Entra al directorio del proyecto
cd video-editor-ia

# 2. Crea el entorno virtual
python -m venv venv

# 3. Actívalo
.\venv\Scripts\activate

# 4. Instala las dependencias
pip install -r requirements.txt
```

---

## Arrancar la aplicación

```powershell
.\venv\Scripts\activate
streamlit run app.py
```

La app abre automáticamente en `http://localhost:8501`.

> **Alternativa en Windows:** doble clic en `instalar_y_arrancar.bat`.  
> Crea el entorno, instala todo y lanza la app en un solo paso.

---

## Flujo de uso

### Paso 1 · Seleccionar video
Pega la ruta completa a tu archivo de OBS o cualquier video (MP4, MKV, MOV, AVI, MKV…).  
**Sin límite de tamaño** — la app trabaja directamente con el archivo en disco, sin copiarlo.

Ejemplo:
```
C:\Users\TuUsuario\Videos\OBS\grabacion.mkv
```

### Paso 2 · Generar Proxy para Gemini
Haz clic en **"Preparar para Gemini"**.  
El botón genera una versión comprimida del video (CRF 28, MP3 128k) de menos de 2 GB  
lista para subir a [Gemini Advanced](https://gemini.google.com).

### Paso 3 · Detectar silencios
Haz clic en **"Detectar Silencios"**.  
La app analiza el audio y calcula los segmentos a conservar según estos parámetros  
(configurables en la barra lateral):

| Parámetro | Valor por defecto |
|-----------|-------------------|
| Umbral de volumen | 25 % |
| Duración mínima de silencio | 0.7 s |
| Buffer de zona segura | 0.2 s |

### Paso 4 · Integrar cortes de Gemini *(opcional)*
En Gemini Advanced pide los timestamps de muletillas o errores.  
Pega el JSON resultante en el área de texto y haz clic en **"Combinar Cortes"**.

Formato JSON aceptado:
```json
[
  {"start": 10.5, "end": 12.3},
  {"start": 45.0, "end": 47.2}
]
```
También acepta tiempos en formato `"MM:SS"` o `"HH:MM:SS"`.

### Paso 5 · Exportar video final
Elige la calidad en la barra lateral y haz clic en **"Exportar Video"**:

| Opción | Configuración | Uso recomendado |
|--------|--------------|-----------------|
| Sin reducción | CRF 18 | Subir a YouTube en máxima calidad |
| Reducir calidad | CRF 18–35 (slider) | Compartir o archivar con menor peso |

El archivo exportado se guarda en la misma carpeta que el video original.

---

## Estructura del proyecto

```
video-editor-ia/
├── app.py                    ← Aplicación principal
├── requirements.txt          ← Dependencias Python
├── instalar_y_arrancar.bat   ← Instalador/lanzador para Windows
└── .streamlit/
    └── config.toml           ← Tema oscuro y límite de 4 GB
```

---

## Dependencias

| Paquete | Uso |
|---------|-----|
| `streamlit` | Interfaz web |
| `moviepy` | Análisis de audio para detección de silencios |
| `ffmpeg-python` | Inspección de metadatos del video |
| `numpy` | Cálculo de RMS por segmento de audio |
| `ffmpeg` (CLI) | Compresión, corte y exportación |
