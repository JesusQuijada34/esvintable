import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import esvintable as mod


async def build_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Iniciar escáner", callback_data="start_scan")],
        [InlineKeyboardButton("Enviar mensaje de prueba", callback_data="send_test")],
        [InlineKeyboardButton("Mostrar configuración", callback_data="show_config")],
        [InlineKeyboardButton("Listar artistas", callback_data="list_artists")],
        [InlineKeyboardButton("Añadir artista", callback_data="add_artist")],
        [InlineKeyboardButton("Eliminar artista", callback_data="remove_artist")],
        [InlineKeyboardButton("Estado (.lastID / sent)", callback_data="status")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = await build_menu_keyboard()
    await update.message.reply_text("Bienvenido al bot de esvintable. Selecciona una acción:", reply_markup=kb)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_scan":
        app = context.application
        if app.bot_data.get("scanner_task"):
            await query.message.reply_text("El escáner ya está en ejecución.")
            return

        async def scanner_runner(app):
            current_dir = os.path.dirname(mod.__file__)
            last_id_path = os.path.join(current_dir, ".lastID")
            log_path = os.path.join(current_dir, "log.txt")
            if not os.path.exists(last_id_path):
                with open(last_id_path, "w") as f:
                    f.write("0")
                last_id = 0
            else:
                with open(last_id_path, "r") as f:
                    content = f.read().strip()
                    last_id = int(content) if content.isdigit() else 0

            last_id_object = open(last_id_path, "r+")
            log = open(log_path, "a", encoding="utf-8")
            try:
                await mod.process_ids(last_id + 1, 999999999, log, last_id_object, mod.load_artists(), mod.load_sent_ids())
            finally:
                try:
                    log.close()
                except Exception:
                    pass
                try:
                    last_id_object.close()
                except Exception:
                    pass
                app.bot_data.pop("scanner_task", None)

        task = context.application.create_task(scanner_runner(context.application))
        context.application.bot_data["scanner_task"] = task
        await query.message.reply_text("Escáner iniciado en segundo plano.")

    elif data == "send_test":
        context.user_data["state"] = "test_msg"
        await query.message.reply_text("Envía ahora el mensaje de prueba como respuesta en este chat.")

    elif data == "show_config":
        def _mask(token: str) -> str:
            if not token:
                return "(not set)"
            if len(token) <= 8:
                return token[:2] + "..."
            return token[:4] + "..." + token[-4:]

        API_TOKEN = getattr(mod, "API_TOKEN", os.getenv("API_TOKEN") or os.getenv("BOT_TOKEN"))
        CHAT_IDS = getattr(mod, "CHAT_IDS", [])
        ERROR_LIMIT = getattr(mod, "ERROR_LIMIT", "(none)")
        msg = (f"API_TOKEN: {_mask(API_TOKEN)}\n" f"CHAT_IDS: {', '.join(CHAT_IDS) if CHAT_IDS else '(none)'}\n" f"ERROR_LIMIT: {ERROR_LIMIT}\n")
        await query.message.reply_text(msg)

    elif data == "list_artists":
        artists = mod.load_artists()
        if not artists:
            await query.message.reply_text("No hay artistas cargados.")
            return
        text = "Artistas (mostrando 200 max):\n" + "\n".join(artists[:200])
        await query.message.reply_text(text)

    elif data == "add_artist":
        context.user_data["state"] = "add_artist"
        await query.message.reply_text("Envía el nombre exacto del artista a añadir.")

    elif data == "remove_artist":
        context.user_data["state"] = "remove_artist"
        await query.message.reply_text("Envía el nombre exacto del artista a eliminar.")

    elif data == "status":
        try:
            with open('.lastID','r') as f:
                last = f.read().strip()
        except Exception:
            last = '(no existe)'
        sent_count = 0
        try:
            if os.path.exists('sent.txt'):
                with open('sent.txt','r') as s:
                    sent_count = sum(1 for _ in s)
        except Exception:
            sent_count = '(no accesible)'
        await query.message.reply_text(f".lastID -> {last}\nsent.txt -> {sent_count}")


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.pop("state", None)
    text = update.message.text.strip() if update.message and update.message.text else ""
    if not state:
        await update.message.reply_text("No hay acciones pendientes. Usa /start para ver el menú.")
        return

    if state == "test_msg":
        await update.message.reply_text("Enviando mensaje de prueba a todos los chats configurados...")
        await mod.send_to_all_chats(text)
        await update.message.reply_text("Mensaje de prueba enviado.")
        return

    if state == "add_artist":
        if not text:
            await update.message.reply_text("Nombre vacío, cancelado.")
            return
        artists = mod.load_artists()
        if text.lower() in artists:
            await update.message.reply_text("El artista ya existe.")
            return
        with open('artists.txt', 'a', encoding='utf-8') as f:
            f.write(text + '\n')
        await update.message.reply_text(f"Artista '{text}' añadido.")
        return

    if state == "remove_artist":
        if not text:
            await update.message.reply_text("Nombre vacío, cancelado.")
            return
        artists = mod.load_artists()
        lowered = [a for a in artists if a != text.lower()]
        if len(lowered) == len(artists):
            await update.message.reply_text("No se encontró el artista.")
            return
        with open('artists.txt', 'w', encoding='utf-8') as f:
            for a in lowered:
                f.write(a + '\n')
        await update.message.reply_text(f"Artista '{text}' eliminado.")
        return


def run_bot():
    BOT_TOKEN = getattr(mod, "API_TOKEN", os.getenv("API_TOKEN") or os.getenv("BOT_TOKEN"))
    if not BOT_TOKEN:
        print("Error: API token not found in environment (API_TOKEN or BOT_TOKEN).")
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    print("Iniciando bot de Telegram (polling)...")
    app.run_polling()
