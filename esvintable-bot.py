#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esVintable Telegram Bot
Herramienta para extraer metadatos de archivos de audio vía Telegram
Autor: @JesusQuijada34
"""

import os
import sys
import logging
import json
import hashlib
from pathlib import Path
import yt_dlp
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, error as ID3error

# ===== CONFIGURACIÓN =====
load_dotenv()
BOT_TOKEN = os.getenv('ESVINTABLE_BOT_TOKEN', '')

if not BOT_TOKEN:
    print("❌ Error: ESVINTABLE_BOT_TOKEN no está configurado.")
    print("Por favor, establezca la variable de entorno ESVINTABLE_BOT_TOKEN")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados de conversación
SELECT_ACTION, WAITING_FILE, PROCESSING = range(3)

# ===== FUNCIONES AUXILIARES =====

def extract_metadata(file_path):
    """Extrae metadatos de un archivo de audio"""
    ext = os.path.splitext(file_path)[1].lower()
    metadata = {}
    
    try:
        if ext == ".mp3":
            try:
                audio = EasyID3(file_path)
                metadata["Título"] = audio.get("title", ["Desconocido"])[0]
                metadata["Artista"] = audio.get("artist", ["Desconocido"])[0]
                metadata["Álbum"] = audio.get("album", ["Desconocido"])[0]
                metadata["Año"] = audio.get("date", [""])[0]
            except ID3error:
                audio = ID3(file_path)
                metadata["Título"] = str(audio.get("TIT2", "Desconocido"))
                metadata["Artista"] = str(audio.get("TPE1", "Desconocido"))
                metadata["Álbum"] = str(audio.get("TALB", "Desconocido"))
        
        elif ext == ".flac":
            audio = FLAC(file_path)
            metadata["Título"] = audio.get("title", ["Desconocido"])[0]
            metadata["Artista"] = audio.get("artist", ["Desconocido"])[0]
            metadata["Álbum"] = audio.get("album", ["Desconocido"])[0]
            metadata["Año"] = audio.get("date", [""])[0]
        
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(file_path)
            metadata["Título"] = str(audio.get("\xa9nam", ["Desconocido"])[0])
            metadata["Artista"] = str(audio.get("\xa9ART", ["Desconocido"])[0])
            metadata["Álbum"] = str(audio.get("\xa9alb", ["Desconocido"])[0])
        
        metadata["Archivo"] = os.path.basename(file_path)
        metadata["Tamaño"] = f"{os.path.getsize(file_path) / (1024*1024):.2f} MB"
    
    except Exception as e:
        metadata["Error"] = str(e)
    
    return metadata

def extract_isrc(file_path):
    """Extrae ISRC de un archivo de audio"""
    result = {
        'filename': os.path.basename(file_path),
        'isrc': None,
        'artist': None,
        'title': None
    }
    
    try:
        audiofile = None
        fp = file_path.lower()
        
        if fp.endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                audiofile = ID3(file_path)
        elif fp.endswith('.flac'):
            audiofile = FLAC(file_path)
        elif fp.endswith(('.m4a', '.mp4', '.aac')):
            audiofile = MP4(file_path)
        
        if audiofile:
            for key in ('isrc', 'TSRC'):
                try:
                    if key in audiofile:
                        val = audiofile[key]
                        if isinstance(val, list):
                            val = val[0]
                        result['isrc'] = str(val).strip().upper()
                        break
                except Exception:
                    continue
            
            for art in ('artist', 'ARTIST', '©ART'):
                try:
                    if art in audiofile:
                        val = audiofile[art]
                        result['artist'] = val[0] if isinstance(val, list) else str(val)
                        break
                except Exception:
                    pass
            
            for tit in ('title', 'TITLE', '©nam'):
                try:
                    if tit in audiofile:
                        val = audiofile[tit]
                        result['title'] = val[0] if isinstance(val, list) else str(val)
                        break
                except Exception:
                    pass
    
    except Exception as e:
        result['error'] = str(e)
    
    return result

def generate_fingerprint(file_path):
    """Genera fingerprint SHA256 del archivo"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        return f"Error: {str(e)}"

def format_metadata_message(metadata):
    """Formatea los metadatos en un mensaje markdown"""
    message = "🎵 *Metadatos Extraídos*\n\n"
    for key, value in metadata.items():
        if key != "Error":
            message += f"*{key}:* `{value}`\n"
    return message

# ===== HANDLERS DEL BOT =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user = update.effective_user
    welcome_message = (
        f"¡Hola {user.first_name}! 👋\n\n"
        "Bienvenido a *esVintable Bot* 🎵\n\n"
        "Soy un bot para extraer metadatos de archivos de audio.\n\n"
        "¿Qué deseas hacer?"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Extraer Metadatos", callback_data="extract_metadata"),
            InlineKeyboardButton("🔍 Extraer ISRC", callback_data="extract_isrc")
        ],
        [
            InlineKeyboardButton("🎬 YouTube ISRC", callback_data="youtube_isrc")
            InlineKeyboardButton("👆 Fingerprint", callback_data="fingerprint"),
            InlineKeyboardButton("❓ Ayuda", callback_data="help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_message = (
        "*Comandos Disponibles:*\n\n"
        "/start - Mostrar menú principal\n"
        "/help - Mostrar esta ayuda\n"
        "/about - Información del bot\n\n"
        "*Funcionalidades:*\n"
        "• 📊 Extraer metadatos (título, artista, álbum, etc.)\n"
        "• 🔍 Extraer ISRC de archivos de audio\n"
        "• 👆 Generar fingerprint SHA256\n\n"
        "*Formatos Soportados:*\n"
        "`MP3, FLAC, M4A, MP4, AAC, OGG, OPUS, WMA`"
    )
    
    await update.message.reply_text(
        help_message,
        parse_mode=ParseMode.MARKDOWN
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /about"""
    about_message = (
        "*esVintable Bot v1.0* 🎵\n\n"
        "Herramienta para extraer metadatos de archivos de audio vía Telegram\n\n"
        "*Autor:* @JesusQuijada34\n"
        "*GitHub:* [JesusQuijada34/esvintable](https://github.com/JesusQuijada34/esvintable)\n\n"
        "Powered by python-telegram-bot"
    )
    
    await update.message.reply_text(
        about_message,
        parse_mode=ParseMode.MARKDOWN
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los clics de botones inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "extract_metadata":
        await query.edit_message_text(
            text="📤 Por favor, envía un archivo de audio para extraer sus metadatos.\n\n"
                 "Formatos soportados: MP3, FLAC, M4A, MP4, AAC",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['action'] = 'extract_metadata'
        return SELECT_ACTION
    
    elif query.data == "extract_isrc":
        await query.edit_message_text(
            text="📤 Por favor, envía un archivo de audio para extraer su ISRC.\n\n"
            "Formatos soportados: MP3, FLAC, M4A, MP4, AAC",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['action'] = 'extract_isrc'
        return SELECT_ACTION
    
    elif query.data == "youtube_isrc":
        await query.edit_message_text(
            text="🔗 Por favor, envía el enlace de YouTube del video que deseas procesar para extraer su ISRC.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['action'] = 'youtube_isrc'
        return WAITING_FILE # Usaremos el mismo estado de conversación para esperar el enlace
    
    elif query.data == "fingerprint":
        await query.edit_message_text(
            text="📤 Por favor, envía un archivo de audio para generar su fingerprint SHA256.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['action'] = 'fingerprint'
        return SELECT_ACTION
    
    elif query.data == "help":
        help_message = (
            "*Comandos Disponibles:*\n\n"
            "/start - Mostrar menú principal\n"
            "/help - Mostrar esta ayuda\n"
            "/about - Información del bot\n\n"
            "*Funcionalidades:*\n"
            "• 📊 Extraer metadatos\n"
            "• 🔍 Extraer ISRC\n"
            "• 👆 Generar fingerprint SHA256"
        )
        await query.edit_message_text(
            text=help_message,
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja archivos enviados"""
    document = update.message.document
    file_name = document.file_name
    
    # Verificar que sea un archivo de audio
    SUPPORTED_AUDIO = ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma')
    if not file_name.lower().endswith(SUPPORTED_AUDIO):
        await update.message.reply_text(
            "❌ Formato no soportado.\n\n"
            "Formatos válidos: `MP3, FLAC, M4A, MP4, AAC, OGG, OPUS, WMA`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Descargar archivo
    await update.message.reply_text("⏳ Procesando archivo...")
    
    try:
        file = await context.bot.get_file(document.file_id)
        # Usar un nombre de archivo seguro y único en /tmp
        temp_dir = Path("/tmp")
        # El nombre del archivo debe ser único para evitar colisiones
        unique_filename = f"{os.getpid()}_{document.file_unique_id}_{file_name}"
        file_path = temp_dir / unique_filename
        
        await file.download_to_drive(file_path)
        file_path = str(file_path) # Convertir a string para usar en las funciones auxiliares
        context.user_data['last_file_path'] = file_path # Guardar la ruta para limpieza/uso posterior
        
        action = context.user_data.get('action', 'extract_metadata')
        
        if action == 'extract_metadata':
            metadata = extract_metadata(file_path)
            message = format_metadata_message(metadata)
        
        elif action == 'extract_isrc':
            isrc_data = extract_isrc(file_path)
            metadata = extract_metadata(file_path)
            
            message = "🎵 *Información ISRC*\n\n"
            message += f"*Archivo:* `{isrc_data['filename']}`\n"
            message += f"*Artista:* `{isrc_data['artist'] or 'Desconocido'}`\n"
            message += f"*Título:* `{isrc_data['title'] or 'Desconocido'}`\n"
            message += f"*ISRC:* `{isrc_data['isrc'] or 'No encontrado'}`\n"
        
        elif action == 'fingerprint':
            fingerprint = generate_fingerprint(file_path)
            message = (
                "👆 *Fingerprint SHA256*\n\n"
                f"`{fingerprint}`"
            )
        
        else:
            message = "❌ Acción no reconocida."
        
        # Enviar resultado
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Limpiar archivo temporal
        if 'last_file_path' in context.user_data:
            os.remove(context.user_data.pop('last_file_path'))
        
        # Mostrar menú nuevamente
        keyboard = [
            [
                InlineKeyboardButton("📊 Extraer Metadatos", callback_data="extract_metadata"),
                InlineKeyboardButton("🔍 Extraer ISRC", callback_data="extract_isrc")
            ],
            [
                InlineKeyboardButton("👆 Fingerprint", callback_data="fingerprint"),
                InlineKeyboardButton("❓ Ayuda", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "¿Qué deseas hacer ahora?",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    except Exception as e:
        logger.error(f"Error procesando archivo: {e}")
        await update.message.reply_text(
            f"❌ Error procesando archivo:\n`{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto"""
    text = update.message.text
    action = context.user_data.get('action')
    
    if action == 'youtube_isrc' and ('youtube.com/' in text or 'youtu.be/' in text):
        await handle_youtube_link(update, context)
    else:
        await update.message.reply_text(
            "Hola 👋 Usa /start para ver el menú principal o /help para obtener ayuda.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja enlaces de YouTube para descargar y extraer ISRC"""
    url = update.message.text
    await update.message.reply_text(f"⏳ Enlace recibido: `{url}`. Iniciando descarga y procesamiento...", parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Configuración de yt-dlp para descargar solo el audio en el mejor formato
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Usamos un nombre de archivo temporal único para evitar colisiones
        temp_filename = f"/tmp/{os.getpid()}_youtube_audio"
        ydl_opts['outtmpl'] = f"{temp_filename}.%(ext)s"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            # El archivo descargado (o convertido por FFmpeg) tendrá un nombre con la extensión final
            downloaded_file = ydl.prepare_filename(info_dict)
            # Como usamos 'mp3' como preferredcodec, el archivo final será .mp3
            file_path = f"{temp_filename}.mp3"
            
            if not os.path.exists(file_path):
                # Intentar encontrar el archivo si la extensión no es mp3 (p. ej. si no se pudo convertir)
                for ext in ['.mp3', '.m4a', '.opus', '.webm']:
                    potential_path = f"{temp_filename}.{ext}"
                    if os.path.exists(potential_path):
                        file_path = potential_path
                        break
                
                if not os.path.exists(file_path):
                    raise FileNotFoundError("No se pudo encontrar el archivo de audio descargado.")

        context.user_data['last_file_path'] = file_path # Guardar para limpieza
        
        # 1. Extraer ISRC
        isrc_data = extract_isrc(file_path)
        
        # 2. Formatear mensaje
        message = "🎵 *Información ISRC de YouTube*\n\n"
        message += f"*Enlace:* `{url}`\n"
        message += f"*Archivo:* `{isrc_data['filename']}`\n"
        message += f"*Artista:* `{isrc_data['artist'] or 'Desconocido'}`\n"
        message += f"*Título:* `{isrc_data['title'] or 'Desconocido'}`\n"
        message += f"*ISRC:* `{isrc_data['isrc'] or 'No encontrado'}`\n"
        
        # 3. Enviar resultado
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # 4. Limpiar
        if 'last_file_path' in context.user_data:
            os.remove(context.user_data.pop('last_file_path'))
        context.user_data.pop('action', None)
        
        # 5. Mostrar menú nuevamente
        await start(update, context) # Reutilizar la función start para mostrar el menú
        
    except Exception as e:
        logger.error(f"Error procesando enlace de YouTube: {e}")
        await update.message.reply_text(
            f"❌ Error procesando enlace de YouTube:\n`{str(e)}`",
            parse_mode=ParseMode.MARKDOWN
        )
        # Limpiar si el archivo temporal existe
        if 'last_file_path' in context.user_data:
            os.remove(context.user_data.pop('last_file_path'))
        context.user_data.pop('action', None)
        await start(update, context) # Mostrar menú para que el usuario pueda continuar

# ===== FUNCIÓN PRINCIPAL =====

def main():
    """Inicia el bot"""
    print("🚀 Iniciando esVintable Bot...")
    
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    # Manejar mensajes de texto que no son comandos, incluyendo los enlaces de YouTube
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Iniciar bot
    print("✅ Bot iniciado. Escuchando mensajes...")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Bot detenido por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

