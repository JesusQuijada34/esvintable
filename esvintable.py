import os
import json
import time
import requests
import aiohttp
import asyncio
import cloudscraper
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Cargar variables de entorno
load_dotenv()
# Priorizar el token proporcionado por el usuario
API_TOKEN = "8425405985:AAHkYur42HpREARgHK8dqfqQ4wGW41p0bvg"
CHAT_IDS = [chat_id.strip() for chat_id in os.getenv("CHAT_IDS", "").split(",") if chat_id.strip()]
ERROR_LIMIT = int(os.getenv("ERROR_LIMIT", 50))
ERRORS = 0

# Configuración Trebel
providers = ['Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire', 'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize']

# --- Funciones de Utilidad ---

def format_duration(seconds):
    try:
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02}:{seconds:02}"
    except:
        return "00:00"

def load_artists():
    try:
        if os.path.exists("artists.txt"):
            with open("artists.txt", "r", encoding="utf-8") as f:
                return [line.strip().lower() for line in f if line.strip()]
        return []
    except Exception as e:
        print(f"Error reading search file: {e}")
        return []

def load_sent_ids():
    sent_file = "sent.txt"
    sent_ids = set()
    if os.path.exists(sent_file):
        try:
            with open(sent_file, "r") as f:
                for line in f:
                    sent_id = line.strip()
                    if sent_id:
                        sent_ids.add(sent_id)
        except Exception as e:
            print(f"Error loading sent IDs: {e}")
    return sent_ids

def save_sent_id(sent_id):
    try:
        with open("sent.txt", "a") as f:
            f.write(f"{sent_id}\n")
    except Exception as e:
        print(f"Error saving sent ID {sent_id}: {e}")

def checkExists(artist, artists):
    if not artist or not artists:
        return False
    artist = artist.lower()
    query_names = [name.strip() for name in artist.split(",")]
    return any(name in artists for name in query_names)

# --- Funciones de Qobuz ---

async def get_track_info(session, track_id):
    headers = {
        "authority": "www.qobuz.com",
        "accept": "*/*",
        "accept-language": "ru-RU,ru;q=0.7",
        "content-type": "text/plain;charset=UTF-8",
        "origin": "https://play.qobuz.com",
        "referer": "https://play.qobuz.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "x-app-id": "950096963",
        "x-user-auth-token": "tmMC4YHiqHc0mBDHHUIg_oS24u6kDT1mw0vRvGSSuO3MpOzdKGNH0FpTWIieWsx3xA8RzPMFs7fZBGJjdpDjew"
    }
    body = {"tracks_id": [track_id]}
    try:
        async with session.post("https://www.qobuz.com/api.json/0.2/track/getList", headers=headers, data=json.dumps(body)) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("tracks", {}).get("total", 0) > 0:
                    return data["tracks"]["items"][0]
            return None
    except Exception as e:
        print(f"[get_track_info] {track_id}: {e}")
        return None

async def send_to_all_chats(bot, text):
    if not CHAT_IDS:
        return
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending to {chat_id}: {e}")

# --- Funciones de Trebel ---

def getcIP():
    try:
        cIP = requests.get('https://ipinfo.io/json').json()
        return cIP.get('country')
    except:
        return None

async def dl_trebel(isrc):
    s = cloudscraper.create_scraper()
    t = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"
    
    if not os.path.exists("op"):
        os.makedirs("op")
        
    for provider in providers:
        ep = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
        h = {"Authorization": f"Bearer {t}"}
        try:
            r = s.get(ep, headers=h)
            if r.status_code == 200:
                fn = f"op/{isrc}.m4a"
                with open(fn, "wb") as o:
                    o.write(r.content)
                return fn
        except:
            continue
    return None

# --- Comandos del Bot ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot fusionado de Qobuz y Trebel.\n\nComandos:\n/trebel <ISRC> - Descargar de Trebel\n/status - Ver estado del monitor Qobuz")

async def trebel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /trebel <ISRC>")
        return
    
    isrc = context.args[0]
    await update.message.reply_text(f"Intentando descargar ISRC: {isrc}...")
    
    cip = getcIP()
    if cip != "US":
        await update.message.reply_text("Error: Se necesita VPN o Proxy en 'US' para Trebel.")
        return

    file_path = await dl_trebel(isrc)
    if file_path:
        with open(file_path, 'rb') as audio:
            await update.message.reply_audio(audio=audio, title=f"Trebel - {isrc}")
    else:
        await update.message.reply_text("No se pudo encontrar o descargar el archivo de Trebel.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_id_path = ".lastID"
    last_id = "0"
    if os.path.exists(last_id_path):
        with open(last_id_path, "r") as f:
            last_id = f.read().strip()
    
    await update.message.reply_text(f"Monitor Qobuz Activo\nÚltimo ID procesado: {last_id}")

# --- Lógica del Monitor Qobuz ---

async def qobuz_monitor(bot):
    global ERRORS
    last_id_path = ".lastID"
    log_path = "log.txt"
    
    if not os.path.exists(last_id_path):
        with open(last_id_path, "w") as f: f.write("0")
    
    while True:
        try:
            with open(last_id_path, "r") as f:
                content = f.read().strip()
                last_id = int(content) if content.isdigit() else 0
            
            artists = load_artists()
            sent_ids = load_sent_ids()
            today = int(time.time())
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                batch_size = 300
                start_id = last_id + 1
                end_id = start_id + batch_size
                
                tasks = [get_track_info(session, tid) for tid in range(start_id, end_id)]
                results = await asyncio.gather(*tasks)
                
                found_any = False
                for result in results:
                    if result:
                        found_any = True
                        ERRORS = 0
                        track_id = result.get("id", "")
                        if not track_id or track_id in sent_ids: continue
                        
                        with open(last_id_path, "w") as f: f.write(str(track_id))
                        
                        performer = result.get("performer", {}).get("name", "")
                        performers_list = result.get("performers", [])
                        
                        # CORRECCIÓN DE ERROR: Manejar si p es dict o str
                        names = []
                        if performers_list:
                            for p in performers_list:
                                if isinstance(p, dict):
                                    names.append(p.get("name", ""))
                                elif isinstance(p, str):
                                    names.append(p)
                        
                        all_performers_str = ", ".join([n for n in names if n]) if names else performer
                        
                        title = result.get("title", "")
                        version = result.get("version", "")
                        duration = format_duration(result.get("duration", 0))
                        isrc = result.get("isrc", "")
                        
                        album = result.get("album", {})
                        album_title = album.get("title", "")
                        upc = album.get("upc", "")
                        label = album.get("label", {}).get("name", "")
                        release_date_str = album.get("release_date_stream", "")
                        
                        formatted_date = "01.01.2000"
                        release_unix = 0
                        if release_date_str:
                            try:
                                release_date = datetime.strptime(release_date_str, "%Y-%m-%d")
                                release_unix = int(release_date.timestamp())
                                formatted_date = release_date.strftime("%d.%m.%Y")
                            except: pass
                        
                        cover = ""
                        if album.get("image", {}).get("large"):
                            cover = album["image"]["large"].replace("_600.jpg", "_max.jpg")
                        
                        with open(log_path, "a", encoding="utf-8") as log:
                            log.write(f"{track_id} ! {performer} - {title} ! {formatted_date} ! {isrc} ! {upc}\n")
                        
                        if release_unix > today and checkExists(performer, artists):
                            msg = (f"<b>!~ ID:</b> <code>{track_id}</code>\n"
                                   f"<b>!~ Artists:</b> <code>{all_performers_str}</code>\n"
                                   f"<b>!~ Name:</b> <code>{title}</code>\n"
                                   f"<b>!~ Version:</b> <code>{version}</code>\n"
                                   f"<b>!~ Duration:</b> <code>{duration}</code>\n"
                                   f"<b>!~ Album:</b> <code>{album_title}</code>\n"
                                   f"<b>!~ Label:</b> <code>{label}</code>\n"
                                   f"<b>!~ Release Date:</b> <code>{formatted_date}</code>\n"
                                   f"<b>!~ ISRC:</b> <code>{isrc}</code>\n"
                                   f"<b>!~ UPC:</b> <code>{upc}</code>\n"
                                   f"<a href='{cover}'>Cover</a>")
                            await send_to_all_chats(bot, msg)
                            save_sent_id(track_id)
                    else:
                        ERRORS += 1
                
                if not found_any and ERRORS >= ERROR_LIMIT:
                    await asyncio.sleep(60)
                    ERRORS = 0
                
                await asyncio.sleep(5)
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(10)

async def main():
    if not API_TOKEN:
        print("Error: API_TOKEN no configurado")
        return

    application = Application.builder().token(API_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("trebel", trebel_cmd))
    application.add_handler(CommandHandler("status", status))
    
    async with application:
        await application.initialize()
        await application.start()
        
        monitor_task = asyncio.create_task(qobuz_monitor(application.bot))
        
        await application.updater.start_polling()
        
        # Mantener el script vivo y manejar cancelación
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            monitor_task.cancel()
            await application.stop()
            await application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
