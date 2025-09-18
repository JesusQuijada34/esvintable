#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable - Script completo con actualizador + Explorador mejorado (v2)
# Autor: @JesusQuijada34 (base) - Mejoras por asistente
# NOTA: Se han añadido mejoras al explorador sin tocar las APIs externas ni eliminar el sistema de actualización.

import os
import sys
import platform
import subprocess
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from threading import Thread, Event
import cloudscraper
from mutagen.id3 import ID3, error as ID3error
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import json
import hashlib
import base64
import shutil

try:
    import readchar
    READCHAR_AVAILABLE = True
except Exception:
    READCHAR_AVAILABLE = False

# ===== CONFIGURACIÓN =====
ACOUSTID_KEY = "87NqIfCkj8"
SPOTIFY_CLIENT_ID = "7edce1fd97734d2e9588c975e57f5e87"
SPOTIFY_CLIENT_SECRET = "51c9fcff27154bb499064ce38ae7e8dc"
SOUNDCLOUD_CLIENT_ID = ""
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOiJhcGlfZXN2aW50YWJsZSJ9.VM4mKjhrUguvQ0l6wHgFfW6v6m8yF_8jO3wT6jLxQwo"
# =========================

SPOTIFY_CLIENT_ID = SPOTIFY_CLIENT_ID or os.environ.get('SPOTIFY_CLIENT_ID','')
SPOTIFY_CLIENT_SECRET = SPOTIFY_CLIENT_SECRET or os.environ.get('SPOTIFY_CLIENT_SECRET','')
ACOUSTID_KEY = ACOUSTID_KEY or os.environ.get('ACOUSTID_KEY','')
SOUNDCLOUD_CLIENT_ID = SOUNDCLOUD_CLIENT_ID or os.environ.get('SOUNDCLOUD_CLIENT_ID','')
TOKEN = TOKEN or os.environ.get('ESVINTABLE_TOKEN','')

REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
LOCAL_XML_FILE = "details.xml"
UPDATE_INTERVAL = 30
FORCE_UPDATER_NAME = "esvintable_force_update.py"

PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"
IS_TERMUX = "com.termux" in os.environ.get('PREFIX', '')
IS_PYDROID = "ru.iiec.pydroid3" in os.environ.get('PREFIX', '')
PLATFORM_LABEL = (
    "Windows" if IS_WINDOWS else
    "macOS" if IS_MAC else
    "Linux-Termux" if IS_TERMUX else
    "Linux-Pydroid" if IS_PYDROID else
    "Linux" if IS_LINUX else
    "Desconocida"
)

SUPPORTED_AUDIO = ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma')

# VERSION DEL EXPLORADOR (no tocar si vas a extender)
EXPLORADOR_VERSION = "2.0"

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'
    BRIGHT_RED = '\033[38;5;196m'
    BRIGHT_GREEN = '\033[38;5;46m'
    BRIGHT_YELLOW = '\033[38;5;226m'
    BRIGHT_BLUE = '\033[38;5;21m'
    BRIGHT_CYAN = '\033[38;5;87m'
    INVERT = '\033[7m'  # fondo invertido

def color(text, color_code):
    return f"{color_code}{text}{Colors.END}"

def clear():
    os.system('cls' if IS_WINDOWS else 'clear')

# ==============================================================
#             SISTEMA DE ACTUALIZACIÓN (sin cambios)
# ==============================================================

def get_remote_details():
    try:
        r = requests.get(DETAILS_XML_URL, timeout=10)
        if r.status_code == 200:
            return r.text
    except Exception:
        return None
    return None

def parse_version_from_details(xml_text):
    try:
        root = ET.fromstring(xml_text)
        return root.find("version").text.strip()
    except Exception:
        return None

def get_local_version():
    if not os.path.exists(LOCAL_XML_FILE):
        return "0.0.0"
    try:
        tree = ET.parse(LOCAL_XML_FILE)
        root = tree.getroot()
        return root.find("version").text.strip()
    except Exception:
        return "0.0.0"

def save_local_details(xml_text):
    with open(LOCAL_XML_FILE, "w", encoding="utf-8") as f:
        f.write(xml_text)

def update_script():
    try:
        script_url = REPO_RAW_URL + SCRIPT_FILENAME
        r = requests.get(script_url, timeout=15)
        if r.status_code == 200:
            with open(SCRIPT_FILENAME, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(color("[✓] Script actualizado correctamente.", Colors.GREEN))
            return True
    except Exception as e:
        print(color(f"[!] Error actualizando: {e}", Colors.RED))
    return False

def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))

def check_for_update(interactive=True):
    remote_xml = get_remote_details()
    if not remote_xml:
        if interactive:
            print(color("[!] No se pudo obtener detalles remotos.", Colors.RED))
        return
    remote_version = parse_version_from_details(remote_xml)
    if not remote_version:
        if interactive:
            print(color("[!] No se pudo parsear la versión remota.", Colors.RED))
        return
    local_version = get_local_version()
    if version_tuple(remote_version) > version_tuple(local_version):
        print(color(f"[↑] Nueva versión disponible: {remote_version} (local {local_version})", Colors.YELLOW))
        if interactive:
            choice = input("¿Actualizar ahora? (s/n): ").strip().lower()
            if choice == "s":
                if update_script():
                    save_local_details(remote_xml)
                    print(color("Reinicia el script para aplicar la actualización.", Colors.CYAN))
    else:
        if interactive:
            print(color(f"[✓] Estás en la última versión: {local_version}", Colors.GREEN))

stop_event = Event()
def auto_updater():
    while not stop_event.is_set():
        try:
            check_for_update(interactive=False)
        except Exception:
            pass
        stop_event.wait(UPDATE_INTERVAL)

# ==============================================================
#     FUNCIONES AUXILIARES: METADATOS Y BÚSQUEDA
# ==============================================================

def discover_soundcloud_client_id():
    global SOUNDCLOUD_CLIENT_ID
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get("https://soundcloud.com")
        text = resp.text
        # ✅ Arreglo regex conflictiva
        script_urls = re.findall(r'''<script[^>]+src=["\']([^"\']+)["\']''', text)
        for url in script_urls:
            if not url.startswith("http"):
                continue
            js = scraper.get(url).text
            m = re.search(r'client_id\\\":\\\"([a-zA-Z0-9-_]+)', js)
            if m:
                SOUNDCLOUD_CLIENT_ID = m.group(1)
                print(color(f"[✓] Client-ID SoundCloud detectado: {SOUNDCLOUD_CLIENT_ID}", Colors.GREEN))
                return SOUNDCLOUD_CLIENT_ID
    except Exception as e:
        print(color(f"[!] Error detectando client_id: {e}", Colors.RED))
    return None

def extract_metadata(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    metadata = {}
    try:
        if ext == ".mp3":
            audio = EasyID3(file_path)
            metadata["title"] = audio.get("title", [""])[0]
            metadata["artist"] = audio.get("artist", [""])[0]
        elif ext == ".flac":
            audio = FLAC(file_path)
            metadata["title"] = audio.get("title", [""])[0]
            metadata["artist"] = audio.get("artist", [""])[0]
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(file_path)
            metadata["title"] = audio.get("\xa9nam", [""])[0]
            metadata["artist"] = audio.get("\xa9ART", [""])[0]
    except Exception:
        pass
    return metadata

# ==============================================================
#         EXTRACCIÓN DE ISRC, FINGERPRINT Y BÚSQUEDAS
# ==============================================================

def extract_isrc(file_path):
    """
    Extrae ISRC desde metadatos (mutagen) o escaneando binario del archivo.
    Devuelve diccionario con keys: file, filename, isrc, artist, title, method (si aplica), error (si aplica)
    """
    result = {'file': file_path, 'filename': os.path.basename(file_path), 'isrc': None, 'artist': None, 'title': None}
    try:
        audiofile = None
        fp = file_path.lower()
        if fp.endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                try:
                    audiofile = ID3(file_path)
                except Exception:
                    audiofile = None
        elif fp.endswith('.flac'):
            audiofile = FLAC(file_path)
        elif fp.endswith(('.m4a', '.mp4', '.aac')):
            audiofile = MP4(file_path)

        if audiofile:
            # ISRC en campos comunes
            for key in ('isrc', 'TSRC'):
                try:
                    if key in audiofile:
                        val = audiofile[key]
                        if isinstance(val, list):
                            val = val[0]
                        result['isrc'] = str(val).strip().upper()
                        result['method'] = f'metadata:{key}'
                        break
                except Exception:
                    continue

            # artista
            for art in ('artist','ARTIST','©ART'):
                try:
                    if art in audiofile:
                        val = audiofile[art]
                        result['artist'] = val[0] if isinstance(val, list) else str(val)
                        break
                except Exception:
                    pass

            # título
            for tit in ('title','TITLE','©nam'):
                try:
                    if tit in audiofile:
                        val = audiofile[tit]
                        result['title'] = val[0] if isinstance(val, list) else str(val)
                        break
                except Exception:
                    pass

    except Exception as e:
        result['error'] = str(e)

    # Si no encontramos ISRC en metadatos, scan binario
    if not result.get('isrc'):
        try:
            with open(file_path, 'rb') as f:
                data = f.read(150000)  # suficiente para encontrar metadata incrustada
                m = re.search(rb'([A-Z]{2}[A-Z0-9]{3}\d{5})', data)
                if m:
                    found = m.group(1).decode('utf-8', errors='ignore')
                    if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found):
                        result['isrc'] = found
                        result['method'] = 'binary-scan'
        except Exception:
            pass

    return result

# ===== FINGERPRINT (AcoustID / Chromaprint) =====
def fingerprint_and_lookup(file_path, acoustid_key=None):
    """
    Genera fingerprint usando fpcalc (/fpcalc disponible) o pyacoustid y consulta AcoustID para buscar coincidencias.
    Devuelve {'source':'acoustid','matches':[...], 'error':None}
    """
    result = {'source':'acoustid','matches':[], 'error':None}
    fp = None
    duration = None

    # Intentar fpcalc primero (más común)
    try:
        proc = subprocess.run(['fpcalc', '-json', file_path], capture_output=True, text=True, timeout=30)
        if proc.returncode == 0 and proc.stdout:
            import json as _json
            data = _json.loads(proc.stdout)
            fp = data.get('fingerprint')
            duration = int(data.get('duration', 0))
    except Exception:
        pass

    # Si fpcalc no dio resultado, probar pyacoustid
    if not fp:
        try:
            import acoustid as _ac
            fp, duration = _ac.fingerprint_file(file_path)
        except Exception:
            pass

    if not fp or not duration:
        result['error'] = 'No se pudo generar huella acústica (instala fpcalc o pyacoustid)'
        return result

    acoustid_key = acoustid_key or ACOUSTID_KEY
    if not acoustid_key:
        result['error'] = 'No ACOUSTID_KEY configurada (ponla en el script o variable de entorno)'
        return result

    try:
        params = {
            'client': acoustid_key,
            'fingerprint': fp,
            'duration': duration,
            'meta': 'recordings+releases+releasegroups+isrcs'
        }
        r = requests.get('https://api.acoustid.org/v2/lookup', params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for score_item in data.get('results', []):
                for rec in score_item.get('recordings', []):
                    entry = {
                        'score': score_item.get('score'),
                        'title': rec.get('title'),
                        'artists': [a.get('name') for a in rec.get('artists', [])],
                        'isrcs': rec.get('isrcs', []) if rec.get('isrcs') else []
                    }
                    mbid = rec.get('id')
                    if not entry['isrcs'] and mbid:
                        try:
                            mbr = requests.get(f'https://musicbrainz.org/ws/2/recording/{mbid}', params={'inc':'isrcs','fmt':'json'}, timeout=10, headers={'User-Agent':'esvintable/1.0'})
                            if mbr.status_code == 200:
                                mr = mbr.json()
                                isrcs = mr.get('isrcs', [])
                                entry['isrcs'] = isrcs
                        except Exception:
                            pass
                    result['matches'].append(entry)
        else:
            result['error'] = f'AcoustID lookup failed: {r.status_code}'
    except Exception as e:
        result['error'] = str(e)

    return result

# ==============================================================
#                   BÚSQUEDAS ONLINE (APIs)
# ==============================================================

def spotify_search(query, limit=5):
    client_id = SPOTIFY_CLIENT_ID
    client_secret = SPOTIFY_CLIENT_SECRET
    if not client_id or not client_secret:
        print(color("⚠️ Spotify: configura SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en el script para búsquedas.", Colors.YELLOW))
        return []
    try:
        data = {'grant_type':'client_credentials'}
        r = requests.post('https://accounts.spotify.com/api/token', data=data, auth=(client_id, client_secret), timeout=10)
        if r.status_code != 200:
            print(color(f"Spotify auth error: {r.status_code}", Colors.RED))
            return []
        token = r.json().get('access_token')
        headers = {'Authorization': f'Bearer {token}'}
        params = {'q': query, 'type':'track,artist', 'limit':limit}
        r = requests.get('https://api.spotify.com/v1/search', headers=headers, params=params, timeout=10)
        results = []
        if r.status_code == 200:
            data = r.json()
            for t in data.get('tracks', {}).get('items', []):
                results.append({'source':'spotify','type':'track','name':t.get('name'),'artist':', '.join([a['name'] for a in t.get('artists',[])])})
        return results
    except Exception:
        return []

def qobuz_search(query, limit=8):
    try:
        scraper = cloudscraper.create_scraper()
        url = f"https://www.qobuz.com/search/{requests.utils.quote(query)}"
        r = scraper.get(url, timeout=10)
        if r.status_code == 200:
            html = r.text
            matches = re.findall(r'"trackTitle"\s*:\s*"([^"]+)"', html)
            results = []
            for m in matches[:limit]:
                results.append({'source':'qobuz','type':'track','name':m})
            return results
    except Exception:
        pass
    # si falla, regresar vacío
    return []

def itunes_search(query, limit=8):
    try:
        params = {'term': query, 'limit': limit}
        r = requests.get('https://itunes.apple.com/search', params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            results = []
            for it in data.get('results', []):
                results.append({'source':'itunes','type':it.get('kind','track'),'name':it.get('trackName') or it.get('collectionName'),'artist':it.get('artistName')})
            return results
    except Exception:
        pass
    return []

def deezer_search(query, limit=8):
    try:
        r = requests.get('https://api.deezer.com/search', params={'q':query,'limit':limit}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            results = []
            for d in data.get('data', []):
                results.append({'source':'deezer','type':'track','name':d.get('title'),'artist':d.get('artist',{}).get('name')})
            return results
    except Exception:
        pass
    return []

def soundcloud_search(query, limit=8):
    global SOUNDCLOUD_CLIENT_ID
    client = SOUNDCLOUD_CLIENT_ID
    if not client:
        cid = discover_soundcloud_client_id()
        if cid:
            client = cid
    if not client:
        print(color('⚠️ SoundCloud: no se tiene client_id (intenta descubrirlo o configúralo en el script).', Colors.YELLOW))
        return []
    try:
        url = 'https://api-v2.soundcloud.com/search/tracks'
        params = {'q': query, 'limit': limit, 'client_id': client}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            results = []
            for t in data.get('collection', [])[:limit]:
                results.append({'source':'soundcloud','type':'track','name':t.get('title'),'artist':t.get('user',{}).get('username')})
            return results
    except Exception:
        pass
    return []

def unified_search(query):
    print(color(f"🔎 Buscando: {query}", Colors.BRIGHT_CYAN))
    results = []
    # Spotify si configurado
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        results.extend(spotify_search(query))
    # Otros
    results.extend(qobuz_search(query))
    results.extend(itunes_search(query))
    results.extend(deezer_search(query))
    results.extend(soundcloud_search(query))
    # Filtrar duplicados
    seen = set()
    unique = []
    for r in results:
        key = (r.get('source'), r.get('name'), r.get('artist'))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

# ==============================================================
#                  DESCARGA POR ISRC (PROVIDERS)
# ==============================================================

def download_by_isrc(isrc, output_dir="descargas_isrc"):
    scraper = cloudscraper.create_scraper()
    print(color(f"🔍 Buscando ISRC: {isrc}", Colors.BRIGHT_CYAN))
    os.makedirs(output_dir, exist_ok=True)
    for provider in PROVIDERS:
        try:
            url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
            headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
            response = scraper.get(url, headers=headers, timeout=20)
            if response.status_code == 200 and len(response.content) > 1000:
                filename = os.path.join(output_dir, f"{isrc}_{provider}.m4a")
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(color(f"✅ Descargado: {filename}", Colors.BRIGHT_GREEN))
                return True, filename
            elif response.status_code == 404:
                print(color(f"   ❌ No en {provider}", Colors.BRIGHT_RED))
            else:
                print(color(f"   ⚠️ {provider} -> {response.status_code}", Colors.BRIGHT_YELLOW))
        except Exception as e:
            print(color(f"   ⚠️ Error con {provider}: {e}", Colors.BRIGHT_YELLOW))
    return False, None

# ==============================================================
#                         UTILIDADES
# ==============================================================

def list_audio_files(directory):
    out = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                out.append(os.path.join(root, file))
    return out

def display_file_info(info):
    isrc_text = info.get('isrc', 'No encontrado')
    isrc_color = Colors.BRIGHT_GREEN if info.get('isrc') else Colors.BRIGHT_RED
    print(color(f"Archivo: {info.get('filename')}", Colors.CYAN))
    print(f"   ISRC: {color(isrc_text, isrc_color)}")
    print(f"   Artista: {info.get('artist', 'Desconocido')}")
    print(f"   Título: {info.get('title', 'Desconocido')}")
    if 'method' in info:
        print(f"   Método: {info['method']}")

def human_size(n):
    try:
        n = int(n)
    except Exception:
        return str(n)
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024:
            return f"{n}{unit}"
        n //= 1024
    return f"{n}PB"

def format_mtime(path):
    try:
        t = os.path.getmtime(path)
        return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"

# ==============================================================
#                EXPLORADOR DE ARCHIVOS INTERACTIVO (MEJORADO)
# ==============================================================

def ffplay_available():
    """Detecta si ffplay está disponible en PATH (usado para previsualizar)."""
    try:
        # Windows puede requerir ffplay.exe
        return shutil.which('ffplay') is not None
    except Exception:
        return False

def preview_audio(path, seconds=10):
    """Previsualiza un fragmento de audio usando ffplay si está disponible."""
    if not ffplay_available():
        print(color("[!] Previsualización no disponible (ffplay no está instalado).", Colors.YELLOW))
        return
    try:
        # -nodisp evitar ventana, -autoexit salir al terminar -t tiempo en segundos -loglevel quiet para menos salida
        cmd = ['ffplay', '-nodisp', '-autoexit', '-t', str(seconds), '-loglevel', 'quiet', path]
        subprocess.run(cmd)
    except Exception as e:
        print(color(f"[!] Error previsualizando: {e}", Colors.RED))

def file_explorer(start_path='.'):
    """
    Explorador mejorado:
    - iconos para carpetas/archivos
    - orden inteligente: dirs primero
    - historial (h)
    - búsqueda con /
    - múltiple selección con m
    - modo lista detallada l
    - previsualizar 10s con p
    - exportar selección a JSON con x
    - ver metadatos rápidos al seleccionar (panel lateral)
    """
    current = os.path.abspath(start_path)

    def list_dir(path, filter_text=None):
        try:
            items = os.listdir(path)
        except Exception:
            return []
        entries = []
        for name in sorted(items, key=lambda s: s.lower()):
            full = os.path.join(path, name)
            if os.path.isdir(full):
                entries.append({'type':'dir','name':name,'path':full})
            elif os.path.isfile(full) and name.lower().endswith(SUPPORTED_AUDIO):
                entries.append({'type':'file','name':name,'path':full})
        # Orden: dirs primero
        entries.sort(key=lambda e: (0 if e['type']=='dir' else 1, e['name'].lower()))
        if filter_text:
            ft = filter_text.lower()
            entries = [e for e in entries if ft in e['name'].lower()]
        return entries

    index = 0
    stack = [current]
    history = []
    marked = set()  # indices marked for multiple selection (store absolute path)
    filter_text = None
    detailed_mode = False

    while True:
        clear()
        current = stack[-1]
        entries = list_dir(current, filter_text=filter_text)
        total_dirs = sum(1 for e in entries if e['type']=='dir')
        total_files = sum(1 for e in entries if e['type']=='file')

        # HEADER
        width = shutil.get_terminal_size((80,20)).columns
        print(color("╔" + "═"*(min(76, width-2)) + "╗", Colors.BRIGHT_BLUE))
        title = f" 🎵 EXPLORADOR (v{EXPLORADOR_VERSION}) - {PLATFORM_LABEL} "
        print(color("║ " + title.ljust(min(76, width-4)) + "║", Colors.BRIGHT_BLUE))
        print(color("╟" + "─"*(min(76, width-2)) + "╢", Colors.BRIGHT_BLUE))

        # RUTA
        print(color(f"📁 {current}", Colors.BRIGHT_CYAN))
        print(color("(↑↓ navegar · Enter abrir/seleccionar · Backspace subir · / buscar · m marcar · p previsualizar · l lista detallada · x exportar · h historial · q salir)", Colors.YELLOW))
        print("")

        if not entries:
            print(color("  -- vacío --", Colors.BRIGHT_RED))
        for i, e in enumerate(entries):
            is_sel = (i == index)
            icon = "📁" if e['type']=='dir' else "🎵"
            mark = "*" if e['path'] in marked else " "
            display_name = f"{icon} {e['name']}{'/' if e['type']=='dir' else ''}"
            # si modo detallado, añadir tamaño y fecha
            if detailed_mode and e['type']=='file':
                try:
                    size = human_size(os.path.getsize(e['path']))
                except Exception:
                    size = "-"
                mtime = format_mtime(e['path'])
                display_name = f"{display_name:50.50} {size:8} {mtime}"
            prefix = '▶' if is_sel else ' '
            if is_sel:
                # mostrar invertido
                print(color(f"{prefix} {mark} {display_name}", Colors.INVERT + Colors.BRIGHT_GREEN))
            else:
                # color por tipo
                col = Colors.BRIGHT_BLUE if e['type']=='dir' else Colors.BRIGHT_GREEN
                print(f"{prefix} {mark} {color(display_name, col)}")

        # PANEL LATERAL / INFO RÁPIDA
        print("\n" + "-"*min(76, width-2))
        sel_info = None
        if entries:
            sel = entries[index]
            if sel['type'] == 'file':
                md = extract_metadata(sel['path'])
                isrc_info = extract_isrc(sel['path'])
                sel_info = {"path": sel['path'], "name": sel['name'], "meta": md, "isrc": isrc_info.get('isrc')}
                print(color(f"Archivo seleccionado: {sel['name']}", Colors.CYAN))
                print(f"  Artista: {md.get('artist','-')}   Título: {md.get('title','-')}")
                print(f"  ISRC: {isrc_info.get('isrc','-')}")
                print(f"  Tamaño: {human_size(os.path.getsize(sel['path']))}   Modificado: {format_mtime(sel['path'])}")
            else:
                print(color(f"Carpeta seleccionada: {sel['name']}/", Colors.BRIGHT_BLUE))
                print(f"  Contiene: {len(os.listdir(sel['path']))} entradas (visibles)")

        # Barra de estado inferior
        print(color("-"*min(76, width-2), Colors.BRIGHT_BLUE))
        status = f"Ruta: {current}  |  Directorios: {total_dirs}  Archivos: {total_files}  Marcados: {len(marked)}"
        print(color(status, Colors.BRIGHT_CYAN))
        print(color("Atajos: ↑↓ navegar · Enter abrir/seleccionar · Backspace subir · / buscar · m marcar · p previsualizar · l lista detallada · x exportar · h historial · q salir", Colors.YELLOW))

        # INPUT: lectora por readchar o por input
        if READCHAR_AVAILABLE:
            k = readchar.readkey()
            if k == readchar.key.UP:
                index = (index - 1) % max(1, len(entries))
            elif k == readchar.key.DOWN:
                index = (index + 1) % max(1, len(entries))
            elif k == readchar.key.ENTER:
                if not entries:
                    continue
                sel = entries[index]
                if sel['type'] == 'dir':
                    history.append(current)
                    stack.append(sel['path'])
                    index = 0
                    filter_text = None
                else:
                    # seleccionar archivo único (devolver path)
                    return sel['path']
            elif k == readchar.key.BACKSPACE:
                if len(stack) > 1:
                    stack.pop()
                    index = 0
                else:
                    # nada
                    pass
            elif k.lower() == 'q':
                return None
            elif k == '/':
                # buscar: pedir texto
                try:
                    # no blocking readchar: usar input
                    term = input("Buscar (filtro en nombres, Enter para cancelar): ").strip()
                    filter_text = term or None
                    index = 0
                except Exception:
                    filter_text = None
            elif k.lower() == 'm':
                # marcar/desmarcar el actual
                if entries:
                    sel = entries[index]
                    p = sel['path']
                    if p in marked:
                        marked.remove(p)
                    else:
                        marked.add(p)
            elif k.lower() == 'h':
                # historial
                if history:
                    print("Historial de rutas:")
                    for i_h, h in enumerate(reversed(history[-10:]), 1):
                        print(f"{i_h}. {h}")
                    try:
                        selh = input("Ir a número (Enter cancelar): ").strip()
                        if selh:
                            idx = int(selh)-1
                            target = list(reversed(history[-10:]))[idx]
                            stack.append(target)
                            index = 0
                    except Exception:
                        pass
                else:
                    print(color("Historial vacío.", Colors.YELLOW))
                    time.sleep(0.8)
            elif k.lower() == 'p':
                # previsualizar si archivo
                if entries:
                    sel = entries[index]
                    if sel['type'] == 'file':
                        print(color("Previsualizando 10s...", Colors.BRIGHT_YELLOW))
                        preview_audio(sel['path'], seconds=10)
                        input("Enter para continuar...")
            elif k.lower() == 'l':
                detailed_mode = not detailed_mode
            elif k.lower() == 'x':
                # exportar marcados o actual si no hay marcados
                to_export = list(marked) if marked else ([entries[index]['path']] if entries else [])
                if not to_export:
                    print(color("Nada para exportar.", Colors.YELLOW))
                    time.sleep(0.8)
                else:
                    out_name = input("Nombre archivo JSON (Enter para export_selection.json): ").strip() or "export_selection.json"
                    exlist = []
                    for p in to_export:
                        meta = extract_metadata(p)
                        isrc = extract_isrc(p)
                        exlist.append({'path': p, 'filename': os.path.basename(p), 'title': meta.get('title'), 'artist': meta.get('artist'), 'isrc': isrc.get('isrc')})
                    try:
                        with open(out_name, 'w', encoding='utf-8') as ef:
                            json.dump({'exported': exlist, 'created_at': datetime.now().isoformat(), 'explorer_version': EXPLORADOR_VERSION}, ef, indent=2, ensure_ascii=False)
                        print(color(f"Exportado {len(exlist)} entradas a {out_name}", Colors.BRIGHT_GREEN))
                    except Exception as e:
                        print(color(f"Error exportando: {e}", Colors.RED))
                    time.sleep(0.8)
            else:
                # otras teclas ignoradas
                pass
        else:
            # fallback sin readchar: mostrar menú numerado y permitir comandos
            print("\nListado:")
            for i, e in enumerate(entries, 1):
                print(f"{i}. {e['name']}{'/' if e['type']=='dir' else ''}")
            cmd = input("Selecciona número (número, b=volver, /=buscar, m=marcar, p=preview, l=lista, x=export, h=hist, q=salir): ").strip().lower()
            if cmd == 'q':
                return None
            elif cmd == 'b':
                if len(stack) > 1:
                    stack.pop()
                continue
            elif cmd == '/':
                term = input("Buscar: ").strip()
                filter_text = term or None
                index = 0
                continue
            elif cmd == 'm':
                try:
                    idx = int(input("Número a marcar/desmarcar: ").strip()) - 1
                    if 0 <= idx < len(entries):
                        p = entries[idx]['path']
                        if p in marked:
                            marked.remove(p)
                        else:
                            marked.add(p)
                except Exception:
                    pass
                continue
            elif cmd == 'p':
                try:
                    idx = int(input("Número archivo a previsualizar: ").strip()) - 1
                    if 0 <= idx < len(entries) and entries[idx]['type']=='file':
                        preview_audio(entries[idx]['path'], seconds=10)
                except Exception:
                    pass
                continue
            elif cmd == 'l':
                detailed_mode = not detailed_mode
                continue
            elif cmd == 'x':
                to_export = list(marked) if marked else ([entries[index]['path']] if entries else [])
                if not to_export:
                    print(color("Nada para exportar.", Colors.YELLOW))
                    time.sleep(0.8)
                else:
                    out_name = input("Nombre archivo JSON (Enter para export_selection.json): ").strip() or "export_selection.json"
                    exlist = []
                    for p in to_export:
                        meta = extract_metadata(p)
                        isrc = extract_isrc(p)
                        exlist.append({'path': p, 'filename': os.path.basename(p), 'title': meta.get('title'), 'artist': meta.get('artist'), 'isrc': isrc.get('isrc')})
                    try:
                        with open(out_name, 'w', encoding='utf-8') as ef:
                            json.dump({'exported': exlist, 'created_at': datetime.now().isoformat(), 'explorer_version': EXPLORADOR_VERSION}, ef, indent=2, ensure_ascii=False)
                        print(color(f"Exportado {len(exlist)} entradas a {out_name}", Colors.BRIGHT_GREEN))
                    except Exception as e:
                        print(color(f"Error exportando: {e}", Colors.RED))
                    time.sleep(0.8)
                continue
            else:
                try:
                    idx = int(cmd) - 1
                    if 0 <= idx < len(entries):
                        sel = entries[idx]
                        if sel['type'] == 'dir':
                            history.append(current)
                            stack.append(sel['path'])
                            index = 0
                        else:
                            return sel['path']
                except Exception:
                    continue

# ==============================================================
#                     MENÚ / DISPATCH
# ==============================================================

MAIN_MENU = [
    {'key':'1','label':'🔍 Extraer ISRC (metadatos + fingerprint)','fn':'search_isrc_file'},
    {'key':'2','label':'📁 Explorador interactivo (mejorado)','fn':'explorer'},
    {'key':'3','label':'🌐 Búsqueda online (Spotify/Qobuz/iTunes/Deezer/SoundCloud)','fn':'online_search'},
    {'key':'4','label':'⬇️ Descargar por ISRC','fn':'download_isrc'},
    {'key':'5','label':'📂 Listar archivos de audio en directorio','fn':'list_dir'},
    {'key':'6','label':'🔔 Verificar actualizaciones (forzable)','fn':'check_updates'},
    {'key':'7','label':'⚙️ Forzar redescubrimiento SoundCloud client_id','fn':'discover_sc'},
    {'key':'8','label':'❌ Salir','fn':'exit'}
]

def print_banner():
    print(color("============================================", Colors.BRIGHT_BLUE))
    print(color(f" 🎵 ESVINTABLE - {PLATFORM_LABEL}", Colors.BRIGHT_GREEN))
    print(color(f" Mejorado por: @MkelCT | @JesusQuijada34", Colors.BRIGHT_GREEN))
    print(color("============================================", Colors.BRIGHT_BLUE))

def print_menu(selected_index=0):
    for i, item in enumerate(MAIN_MENU):
        prefix = '▶' if i == selected_index else ' '
        print(prefix, item['key'] + '.', item['label'])

def dispatch_base(name):
    if name == 'explorer':
        path = file_explorer('.')
        if path:
            print(color(f"Seleccionado: {path}", Colors.BRIGHT_CYAN))
            info = extract_isrc(path)
            display_file_info(info)
        input('Enter para continuar...')
        return True
    elif name == 'online_search':
        q = input('Introduce búsqueda (artista/canción): ').strip()
        if not q:
            return True
        res = unified_search(q)
        if not res:
            print(color('No se encontraron resultados.', Colors.RED))
        else:
            for i, r in enumerate(res, 1):
                print(f"{i:2d}. {r.get('name')} — {r.get('artist','-')} ({r.get('source')})")
        input('Enter para continuar...')
        return True
    elif name == 'download_isrc':
        isrc = input('Código ISRC: ').strip().upper()
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc):
            print(color('Formato ISRC inválido.', Colors.RED))
            time.sleep(1)
            return True
        out = input('Directorio de descarga (Enter para descargas_isrc): ').strip() or 'descargas_isrc'
        success, filename = download_by_isrc(isrc, out)
        if success:
            print(color(f'✅ Descarga completa: {filename}', Colors.BRIGHT_GREEN))
        else:
            print(color('❌ No se pudo descargar.', Colors.BRIGHT_RED))
        input('Enter para continuar...')
        return True
    elif name == 'list_dir':
        d = input('Directorio: ').strip() or '.'
        if not os.path.isdir(d):
            print(color('Directorio no válido.', Colors.RED))
        else:
            files = list_audio_files(d)
            if not files:
                print(color('No se encontraron archivos de audio.', Colors.YELLOW))
            else:
                for f in files:
                    print(f)
        input('Enter para continuar.')
        return True
    elif name == 'check_updates':
        check_for_update(interactive=True)
        input('Enter para continuar.')
        return True
    elif name == 'discover_sc':
        print(color("Forzando autodescubrimiento SoundCloud client_id.", Colors.BRIGHT_YELLOW))
        cid = discover_soundcloud_client_id()
        if cid:
            print(color(f"client_id descubierto: {cid}", Colors.BRIGHT_GREEN))
            try:
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'esvintable_config.json')
                cfg = {}
                try:
                    if os.path.exists(cfg_path):
                        with open(cfg_path, 'r', encoding='utf-8') as cf:
                            cfg = json.load(cf)
                except Exception:
                    cfg = {}
                cfg['soundcloud_client_id'] = cid
                with open(cfg_path, 'w', encoding='utf-8') as cf:
                    json.dump(cfg, cf, indent=2)
                print(color(f"Guardado en {cfg_path}", Colors.BRIGHT_CYAN))
            except Exception:
                pass
        else:
            print(color("No se pudo descubrir client_id.", Colors.RED))
        input('Enter para continuar...')
        return True
    elif name == 'exit':
        return False
    return True

def dispatch(name):
    if name == 'search_isrc_file':
        path = file_explorer('.')
        if path:
            info = extract_isrc(path)
            display_file_info(info)
            if not info.get('isrc'):
                print(color('🔊 Intentando identificación por huella acústica...', Colors.BRIGHT_YELLOW))
                res = fingerprint_and_lookup(path, acoustid_key=ACOUSTID_KEY)
                if res.get('matches'):
                    for m in res['matches']:
                        print(color(f"Score: {m.get('score')} - {m.get('title')} — {', '.join(m.get('artists',[]))}", Colors.BRIGHT_CYAN))
                        if m.get('isrcs'):
                            print(color('ISRCs encontradas: ' + ', '.join(m.get('isrcs')), Colors.BRIGHT_GREEN))
                else:
                    print(color('No se encontró coincidencia acústica.', Colors.RED))
            if info.get('isrc'):
                d = input('🔄 Descargar por ISRC? (s/n): ').strip().lower()
                if d == 's':
                    download_by_isrc(info['isrc'], os.path.dirname(path))
        input('Enter para continuar...')
        return True
    else:
        return dispatch_base(name)

# ==============================================================
#              DEPENDENCIAS Y ARRANQUE PRINCIPAL
# ==============================================================

def ensure_dependencies():
    missing = []
    for dep in ["requests", "cloudscraper", "mutagen"]:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if READCHAR_AVAILABLE is False:
        missing.append('readchar')
    try:
        import acoustid  # type: ignore
    except Exception:
        missing.append('pyacoustid')
    if missing:
        print(color("Instalando dependencias faltantes... (esto puede tardar)", Colors.YELLOW))
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True)
            print(color("✅ Dependencias instaladas.", Colors.BRIGHT_GREEN))
        except Exception as e:
            print(color(f"Error instalando dependencias: {e}", Colors.RED))
            return False
    return True

def run_menu():
    selected = 0
    while True:
        clear()
        print_banner()
        if READCHAR_AVAILABLE:
            print(color("Usa ↑/↓ para navegar, Enter para seleccionar, q para salir.", Colors.YELLOW))
            print_menu(selected)
            k = readchar.readkey()
            if k == readchar.key.UP:
                selected = (selected - 1) % len(MAIN_MENU)
            elif k == readchar.key.DOWN:
                selected = (selected + 1) % len(MAIN_MENU)
            elif k == readchar.key.ENTER:
                action = MAIN_MENU[selected]['fn']
                if not dispatch(action):
                    break
            elif k.lower() == 'q':
                break
        else:
            print_menu(selected)
            choice = input('Selecciona opción (número o q): ').strip().lower()
            if choice == 'q':
                break
            matched = next((i for i, it in enumerate(MAIN_MENU) if it['key'] == choice), None)
            if matched is not None:
                if not dispatch(MAIN_MENU[matched]['fn']):
                    break
            else:
                print(color('Opción inválida', Colors.RED))
                time.sleep(1)

def main():
    if not ensure_dependencies():
        print(color('No se pudieron instalar dependencias. Ejecuta manualmente pip install readchar requests cloudscraper mutagen pyacoustid', Colors.RED))
        return
    # intentar autodescubrir SoundCloud client_id si no hay
    if not SOUNDCLOUD_CLIENT_ID:
        discover_soundcloud_client_id()
    # arrancar updater background (no se elimina)
    updater_thread = Thread(target=auto_updater, daemon=True)
    updater_thread.start()
    try:
        run_menu()
    except KeyboardInterrupt:
        print(color('\nHasta pronto!', Colors.BRIGHT_GREEN))
    finally:
        stop_event.set()

if __name__ == '__main__':
    main()
