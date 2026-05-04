@echo off
echo ============================================================
echo  Video Editor IA - Instalador y Lanzador
echo ============================================================
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+ desde https://python.org
    pause
    exit /b 1
)

:: Verifica FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] FFmpeg no encontrado en el PATH.
    echo.
    echo  Opciones para instalar FFmpeg:
    echo   1. winget install Gyan.FFmpeg
    echo   2. Descarga manual: https://ffmpeg.org/download.html
    echo      y agrega la carpeta bin al PATH del sistema.
    echo.
    pause
    exit /b 1
)

echo [OK] Python y FFmpeg detectados.
echo.

:: Crea entorno virtual si no existe
if not exist "venv\" (
    echo Creando entorno virtual...
    python -m venv venv
)

:: Activa entorno
call venv\Scripts\activate.bat

:: Instala dependencias
echo Instalando dependencias Python...
pip install -r requirements.txt --quiet

echo.
echo ============================================================
echo  Iniciando aplicacion en http://localhost:8501
echo ============================================================
echo.
streamlit run app.py --server.maxUploadSize 4096

pause
