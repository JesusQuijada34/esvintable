#!/bin/bash
# Script para ejecutar esVintable Bot en Linux/Mac

# Detectar el sistema operativo
OS=$(uname -s)

echo "🚀 Iniciando esVintable Bot..."
echo "Sistema detectado: $OS"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado."
    exit 1
fi

# Instalar dependencias si es necesario
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar/actualizar dependencias
echo "📥 Instalando dependencias..."
pip install -r lib/requirements.txt -q

# Verificar que .env existe
if [ ! -f ".env" ]; then
    echo "❌ Archivo .env no encontrado."
    echo "Por favor, copia .env.example a .env y configura tu token."
    exit 1
fi

# Ejecutar bot
echo "✅ Iniciando bot..."
python3 esvintable-bot.py
