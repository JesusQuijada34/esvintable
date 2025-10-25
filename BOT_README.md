# 🎵 esVintable Telegram Bot

Bot de Telegram para extraer metadatos de archivos de audio directamente desde la aplicación de Telegram.

## 🚀 Características

- 📊 **Extraer Metadatos**: Obtén información completa del archivo (título, artista, álbum, año, etc.)
- 🔍 **Extraer ISRC**: Extrae el código ISRC del archivo de audio
- 👆 **Generar Fingerprint**: Crea un fingerprint SHA256 del archivo
- 🎨 **Interfaz Intuitiva**: Botones inline y mensajes formateados en markdown
- 🌍 **Multiplataforma**: Compatible con Windows, Linux y macOS

## 📋 Formatos Soportados

- MP3
- FLAC
- M4A / MP4
- AAC
- OGG
- OPUS
- WMA

## 🔧 Instalación

### Requisitos Previos

- Python 3.8+
- pip (gestor de paquetes de Python)

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/JesusQuijada34/esvintable.git
cd esvintable
```

### Paso 2: Configurar el Token

1. Copia el archivo `.env.example` a `.env`:
   ```bash
   cp .env.example .env
   ```

2. Abre el archivo `.env` y reemplaza `your_bot_token_here` con tu token de bot de Telegram:
   ```
   ESVINTABLE_BOT_TOKEN=tu_token_aqui
   ```

3. Para obtener tu token, habla con [@BotFather](https://t.me/BotFather) en Telegram.

### Paso 3: Instalar Dependencias

**Linux/macOS:**
```bash
./run-bot.sh
```

**Windows:**
```bash
run-bot.bat
```

O manualmente:
```bash
pip install -r lib/requirements.txt
python esvintable-bot.py
```

## 📱 Uso

1. Abre Telegram y busca tu bot
2. Envía `/start` para ver el menú principal
3. Selecciona una opción:
   - 📊 Extraer Metadatos
   - 🔍 Extraer ISRC
   - 👆 Generar Fingerprint
4. Envía el archivo de audio
5. ¡El bot procesará el archivo y te mostrará los resultados!

## 🔐 Seguridad

- El token del bot se almacena en el archivo `.env` que está incluido en `.gitignore`
- **Nunca** compartas tu token de bot
- El archivo `.env` no se sincroniza con el repositorio

## 📝 Comandos Disponibles

- `/start` - Mostrar menú principal
- `/help` - Mostrar ayuda
- `/about` - Información del bot

## 🛠️ Desarrollo

Para contribuir al proyecto:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT.

## 👨‍💻 Autor

**Jesús Quijada** - [@JesusQuijada34](https://github.com/JesusQuijada34)

## 🤝 Contribuidores

- [@MkelCT](https://github.com/MkelCT)

## 📞 Soporte

Si encuentras algún problema, por favor abre un [issue](https://github.com/JesusQuijada34/esvintable/issues).

---

**Powered by python-telegram-bot** 🚀

