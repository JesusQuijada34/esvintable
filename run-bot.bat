@echo off
REM Script para ejecutar esVintable Bot en Windows

echo 🚀 Iniciando esVintable Bot...
echo Sistema detectado: Windows

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado o no está en PATH.
    pause
    exit /b 1
)

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo 📦 Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Instalar/actualizar dependencias
echo 📥 Instalando dependencias...
pip install -r lib/requirements.txt -q

REM Verificar que .env existe
if not exist ".env" (
    echo ❌ Archivo .env no encontrado.
    echo Por favor, copia .env.example a .env y configura tu token.
    pause
    exit /b 1
)

REM Ejecutar bot
echo ✅ Iniciando bot...
python esvintable-bot.py

pause

