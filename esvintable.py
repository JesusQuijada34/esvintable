#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable - Versión completa con actualizador mejorado
# Autor original: @JesusQuijada34 (modificado por ti)
# NOTA: Rellena el bloque de configuración más abajo antes de usar.

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

# Intentar importar readchar para navegación con teclas; si no está, usaremos input numérico
try:
    import readchar
    READCHAR_AVAILABLE = True
except Exception:
    READCHAR_AVAILABLE = False

# ===== BLOQUE DE CONFIGURACIÓN (edítalo aquí) =====
ACOUSTID_KEY = ""              # Ej: "ABCD-1234-..." (recomendado para fingerprinting)
SPOTIFY_CLIENT_ID = ""         # Opcional (para búsquedas Spotify)
SPOTIFY_CLIENT_SECRET = ""     # Opcional (para búsquedas Spotify)
SOUNDCLOUD_CLIENT_ID = ""      # Si lo dejas vacío el script intentará autodescubrirlo
TOKEN = ""                     # Tu token privado para descargas por ISRC (si lo tienes)
# ====================================================

# Compatibilidad: si quieres aún leer variables de entorno, las respetamos si no están en el script
SPOTIFY_CLIENT_ID = SPOTIFY_CLIENT_ID or os.environ.get('SPOTIFY_CLIENT_ID','')
SPOTIFY_CLIENT_SECRET = SPOTIFY_CLIENT_SECRET or os.environ.get('SPOTIFY_CLIENT_SECRET','')
ACOUSTID_KEY = ACOUSTID_KEY or os.environ.get('ACOUSTID_KEY','')
SOUNDCLOUD_CLIENT_ID = SOUNDCLOUD_CLIENT_ID or os.environ.get('SOUNDCLOUD_CLIENT_ID','')
TOKEN = TOKEN or os.environ.get('ESVINTABLE_TOKEN','')

# ===== CONFIG GLOBAL =====
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
LOCAL_XML_FILE = "details.xml"
UPDATE_INTERVAL = 30  # segundos entre chequeos automáticos
FORCE_UPDATER_NAME = "esvintable_force_update.py"

PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

# ===== DETECCIÓN DE PLATAFORMA =====
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

# ===== COLORES =====
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

def color(text, color_code):
    return f"{color_code}{text}{Colors.END}"

def clear():
    os.system('cls' if IS_WINDOWS else 'clear')

# ===== SISTEMA DE ACTUALIZACIÓN MEJORADO =====
class UpdateChecker:
    def __init__(self):
        self.last_check = datetime.now()
        self.update_available = False
        self.new_version = ""
        self.update_event = Event()
        self.running = True
        self.remote_version = None
        self.local_version = None
        self.update_info = {}
        self.notification_shown = False
        self.load_local_version()

    def load_local_version(self):
        try:
            if os.path.exists(LOCAL_XML_FILE):
                tree = ET.parse(LOCAL_XML_FILE)
                root = tree.getroot()
                version_element = root.find('version')
                if version_element is not None:
                    self.local_version = version_element.text.strip()
                    return True
        except Exception:
            pass
        self.local_version = "0.0"
        return False

    def fetch_remote_xml(self):
        try:
            r = requests.get(DETAILS_XML_URL, timeout=15)
            if r.status_code == 200:
                return r.text
        except Exception:
            return None

    def parse_remote_info(self, xml_text):
        try:
            root = ET.fromstring(xml_text)
            info = {}
            info['version'] = root.find('version').text.strip() if root.find('version') is not None else self.local_version
            info['changelog'] = root.find('changelog').text.strip() if root.find('changelog') is not None else ""
            info['critical'] = (root.find('critical').text.strip().lower() == 'true') if root.find('critical') is not None else False
            info['message'] = root.find('message').text.strip() if root.find('message') is not None else ""
            return info
        except Exception:
            return None

    def safe_write_file(self, path, content, binary=False):
        tmp = path + '.tmp'
        mode = 'wb' if binary else 'w'
        enc = None if binary else 'utf-8'
        try:
            # Ensure parent dir exists
            parent = os.path.dirname(path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(tmp, mode, encoding=enc) as f:
                f.write(content)
            os.replace(tmp, path)
            return True
        except Exception as e:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            print(color(f'Error escribiendo {path}: {e}', Colors.RED))
            return False

    def download_script_and_xml(self):
        script_url = f"{REPO_RAW_URL}{SCRIPT_FILENAME}"
        xml_text = self.fetch_remote_xml()
        script_text = None
        try:
            r = requests.get(script_url, timeout=20)
            if r.status_code == 200:
                script_text = r.text
        except Exception as e:
            print(color(f'Error descargando script remoto: {e}', Colors.YELLOW))
        return script_text, xml_text

    def create_force_updater(self, script_text, xml_text):
        """Crea un script de respaldo que fuerza la escritura de files si el reemplazo normal falla."""
        try:
            force_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FORCE_UPDATER_NAME)
            payload = f"""#!/usr/bin/env python3
# Script force updater creado por esvintable
import os, sys, time
script_path = {repr(os.path.abspath(__file__))}
try:
    # Escribir details.xml
    xml = {repr(xml_text)}
    if xml:
        with open(os.path.join(os.path.dirname(script_path),'details.xml'), 'w', encoding='utf-8') as xf:
            xf.write(xml)
    # Escribir script
    code = {repr(script_text)}
    if code:
        with open(script_path, 'w', encoding='utf-8') as sf:
            sf.write(code)
    print('Force update aplicado.')
except Exception as e:
    print('Force update fallo:', e)
    sys.exit(2)
# Reiniciar
try:
    time.sleep(0.5)
    os.execv(sys.executable, [sys.executable, script_path])
except Exception:
    pass
"""
            with open(force_path, 'w', encoding='utf-8') as f:
                f.write(payload)
            try:
                os.chmod(force_path, 0o755)
            except Exception:
                pass
            return force_path
        except Exception as e:
            print(color(f'No se pudo crear force updater: {e}', Colors.YELLOW))
            return None

    def apply_update(self, script_text, xml_text):
        """Intenta aplicar actualización: escribe details.xml y el script remoto de forma atómica.
        Si falla, crea un script adicional para forzar el reemplazo.
        Luego intenta reiniciar el proceso.
        """
        script_path = os.path.abspath(__file__)
        # backups
        try:
            with open(script_path, 'r', encoding='utf-8') as orig:
                orig_code = orig.read()
        except Exception:
            orig_code = None
        try:
            if xml_text:
                if not self.safe_write_file(LOCAL_XML_FILE, xml_text, binary=False):
                    print(color('No se pudo escribir details.xml de forma segura.', Colors.YELLOW))
            if script_text:
                # intentar escribir script remoto
                if not self.safe_write_file(script_path, script_text, binary=False):
                    print(color('Escritura directa del script falló, creando force updater...', Colors.YELLOW))
                    force_path = self.create_force_updater(script_text, xml_text)
                    if force_path:
                        print(color(f'Run {force_path} to force the update.', Colors.BRIGHT_YELLOW))
                        try:
                            subprocess.Popen([sys.executable, force_path])
                        except Exception:
                            pass
                    return False
                else:
                    # escrito correctamente: reiniciar
                    print(color('Script actualizado correctamente. Reiniciando...', Colors.BRIGHT_GREEN))
                    time.sleep(0.8)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(color(f'Error applying update: {e}', Colors.RED))
            self.create_force_updater(script_text, xml_text)
            return False
        return True

    def check_for_updates(self, silent=False):
        try:
            xml_text = self.fetch_remote_xml()
            if not xml_text:
                return False
            info = self.parse_remote_info(xml_text)
            if not info:
                return False
            self.update_info = info
            self.remote_version = info.get('version')
            if self.compare_versions(self.local_version, self.remote_version):
                self.update_available = True
                self.new_version = self.remote_version
                if not silent and not self.notification_shown:
                    print(color(f"\n🔔 ¡Actualización disponible! v{self.new_version} — {self.update_info.get('message','')}", Colors.BRIGHT_GREEN))
                    self.notification_shown = True
                    # descargar script y xml
                    script_text, xml_text = self.download_script_and_xml()
                    # aplicar actualización
                    performed = self.apply_update(script_text, xml_text)
                    if not performed:
                        print(color('La actualización no pudo completarse automáticamente. Revisa el archivo force updater.', Colors.YELLOW))
                    return True
        except Exception as e:
            if not silent:
                print(color(f"Error actualizaciones: {e}", Colors.RED))
        return False

    def compare_versions(self, local_ver, remote_ver):
        try:
            local_parts = tuple(map(int, local_ver.split('.')))
            remote_parts = tuple(map(int, remote_ver.split('.')))
            return remote_parts > local_parts
        except Exception:
            return remote_ver > local_ver

    def start_update_checker(self):
        def checker_thread():
            while self.running:
                try:
                    current_time = datetime.now()
                    if (current_time - self.last_check).total_seconds() >= UPDATE_INTERVAL:
                        self.check_for_updates(silent=True)
                        self.last_check = current_time
                    time.sleep(2)
                except Exception:
                    time.sleep(10)
        Thread(target=checker_thread, daemon=True).start()

    def stop_update_checker(self):
        self.running = False

updater = UpdateChecker()

# ===== DEPENDENCIAS =====
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

# ===== EXTRACCIÓN Y METADATOS =====
def extract_isrc(file_path):
    result = {'file': file_path, 'filename': os.path.basename(file_path), 'isrc': None, 'artist': None, 'title': None}
    try:
        audiofile = None
        if file_path.lower().endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                try:
                    audiofile = ID3(file_path)
                except Exception:
                    audiofile = None
        elif file_path.lower().endswith('.flac'):
            audiofile = FLAC(file_path)
        elif file_path.lower().endswith(('.m4a', '.mp4')):
            audiofile = MP4(file_path)
        if audiofile:
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
            for art in ('artist','ARTIST','©ART'):
                if art in audiofile:
                    try:
                        val = audiofile[art]
                        result['artist'] = val[0] if isinstance(val, list) else str(val)
                        break
                    except Exception:
                        pass
            for tit in ('title','TITLE','©nam'):
                if tit in audiofile:
                    try:
                        val = audiofile[tit]
                        result['title'] = val[0] if isinstance(val, list) else str(val)
                        break
                    except Exception:
                        pass
    except Exception as e:
        result['error'] = str(e)
    if not result.get('isrc'):
        try:
            with open(file_path, 'rb') as f:
                data = f.read(150000)
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
    result = {'source':'acoustid','matches':[], 'error':None}
    fp = None
    duration = None
    try:
        proc = subprocess.run(['fpcalc', '-json', file_path], capture_output=True, text=True, timeout=30)
        if proc.returncode == 0 and proc.stdout:
            import json as _json
            data = _json.loads(proc.stdout)
            fp = data.get('fingerprint')
            duration = int(data.get('duration', 0))
    except Exception:
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
        result['error'] = 'No ACOUSTID_KEY configurada (ponla en el script)'
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

# ===== FUNCIONALIDAD: descubrir SoundCloud client_id por scraping =====
def discover_soundcloud_client_id(timeout=10, max_scripts=30):
    """Intenta descubrir automáticamente un client_id válido de SoundCloud."""
    global SOUNDCLOUD_CLIENT_ID
    if SOUNDCLOUD_CLIENT_ID:
        return SOUNDCLOUD_CLIENT_ID

    scraper = cloudscraper.create_scraper()
    candidates = set()

    try:
        print(color('🔎 Intentando descubrir SoundCloud client_id (scraping)...', Colors.BRIGHT_YELLOW))
        r = scraper.get('https://soundcloud.com', timeout=timeout)
        text = r.text if r.status_code == 200 else ''

        # patrones simples
        patterns = [
            r'client_id\s*[:=]\s*"([a-zA-Z0-9_-]{8,})"',
            r'client_id=([a-zA-Z0-9_-]{8,})',
            r'client_id\\\":\\\"([a-zA-Z0-9_-]{8,})\\\"',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                candidates.add(m.group(1))

        # extraer scripts y comprobarlos
        script_urls = re.findall(r'<script[^>]+src=[\"\\']([^\"\\']+)[\"\\']', text)
        count = 0
        for s in script_urls:
            if count >= max_scripts:
                break
            if s.startswith('//'):
                s = 'https:' + s
            elif s.startswith('/'):
                s = 'https://soundcloud.com' + s
            try:
                sr = scraper.get(s, timeout=timeout)
                if sr.status_code == 200:
                    st = sr.text
                    for pat in patterns:
                        for m in re.finditer(pat, st):
                            candidates.add(m.group(1))
                count += 1
            except Exception:
                continue

        # validar candidates con una petición de prueba
        for cid in list(candidates):
            try:
                test = scraper.get('https://api-v2.soundcloud.com/tracks', params={'q':'test','limit':1,'client_id':cid}, timeout=8)
                if test.status_code == 200:
                    SOUNDCLOUD_CLIENT_ID = cid
                    print(color(f'✅ SoundCloud client_id descubierto: {cid}', Colors.BRIGHT_GREEN))
                    return cid
            except Exception:
                continue

    except Exception as e:
        print(color(f'⚠️ Error descubriendo client_id: {e}', Colors.YELLOW))

    print(color('❌ No se pudo descubrir un client_id válido automáticamente.', Colors.BRIGHT_RED))
    return None

# ===== EXPLORADOR DE ARCHIVOS INTERACTIVO =====
def file_explorer(start_path='.'):
    current = os.path.abspath(start_path)

    def list_dir(path):
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
        return entries

    index = 0
    stack = [current]
    while True:
        clear()
        current = stack[-1]
        entries = list_dir(current)
        print(color(f"📁 Explorador: {current}", Colors.BRIGHT_CYAN))
        print(color("(Usa ↑↓ para navegar, Enter para abrir/seleccionar, Backspace para subir, q para salir)", Colors.YELLOW))

        if not entries:
            print(color("  -- vacío --", Colors.BRIGHT_RED))
        for i, e in enumerate(entries):
            prefix = '▶' if i == index else ' '
            display = f"{prefix} {e['name']}{'/' if e['type']=='dir' else ''}"
            if i == index:
                print(color(display, Colors.BRIGHT_GREEN))
            else:
                print(display)

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
                    stack.append(sel['path'])
                    index = 0
                else:
                    return sel['path']
            elif k == readchar.key.BACKSPACE:
                if len(stack) > 1:
                    stack.pop()
                    index = 0
            elif k.lower() == 'q':
                return None
        else:
            print('\nListado:')
            for i, e in enumerate(entries, 1):
                print(f"{i}. {e['name']}{'/' if e['type']=='dir' else ''}")
            choice = input("Selecciona número (número, b=volver, q=salir): ").strip().lower()
            if choice == 'q':
                return None
            if choice == 'b':
                if len(stack) > 1:
                    stack.pop()
                continue
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(entries):
                    sel = entries[idx]
                    if sel['type'] == 'dir':
                        stack.append(sel['path'])
                        index = 0
                    else:
                        return sel['path']
            except Exception:
                continue

# ===== BÚSQUEDAS ONLINE =====
def spotify_search(query, limit=5):
    client_id = SPOTIFY_CLIENT_ID
    client_secret = SPOTIFY_CLIENT_SECRET
    if not client_id or not client_secret:
        print(color("⚠️ Spotify: configura SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en el script para búsquedas.", Colors.YELLOW))
        return []
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

def qobuz_search(query, limit=8):
    scraper = cloudscraper.create_scraper()
    url = f"https://www.qobuz.com/search/{requests.utils.quote(query)}"
    try:
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
    print(color("⚠️ Búsqueda Qobuz fallida o no disponible (anti-scraping).", Colors.YELLOW))
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
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        results.extend(spotify_search(query))
    results.extend(qobuz_search(query))
    results.extend(itunes_search(query))
    results.extend(deezer_search(query))
    results.extend(soundcloud_search(query))
    seen = set()
    unique = []
    for r in results:
        key = (r.get('source'), r.get('name'), r.get('artist'))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique

# ===== DESCARGA POR ISRC =====
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

# ===== UTILIDADES =====
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

# ===== MENÚ TUI / CLI =====
MAIN_MENU = [
    {'key':'1','label':'🔍 Extraer ISRC (metadatos + fingerprint)','fn':'search_isrc_file'},
    {'key':'2','label':'📁 Explorador interactivo','fn':'explorer'},
    {'key':'3','label':'🌐 Búsqueda online (Spotify/Qobuz/iTunes/Deezer/SoundCloud)','fn':'online_search'},
    {'key':'4','label':'⬇️ Descargar por ISRC','fn':'download_isrc'},
    {'key':'5','label':'📂 Listar archivos de audio en directorio','fn':'list_dir'},
    {'key':'6','label':'🔔 Verificar actualizaciones (forzar)','fn':'check_updates'},
    {'key':'7','label':'⚙️ Forzar redescubrimiento SoundCloud client_id','fn':'discover_sc'},
    {'key':'8','label':'❌ Salir','fn':'exit'}
]

def print_banner():
    print(color("============================================", Colors.BRIGHT_BLUE))
    print(color(f" 🎵 ESVINTABLE - {PLATFORM_LABEL}", Colors.BRIGHT_GREEN))
    print(color("============================================", Colors.BRIGHT_BLUE))

def print_menu(selected_index=0):
    for i, item in enumerate(MAIN_MENU):
        prefix = '▶' if i == selected_index else ' '
        print(prefix, item['key'] + '.', item['label'])

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

# Dispatcher: acciones del menú
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
        input('Enter para continuar...')
        return True
    elif name == 'check_updates':
        updater.check_for_updates(silent=False)
        input('Enter para continuar...')
        return True
    elif name == 'discover_sc':
        print(color("Forzando autodescubrimiento SoundCloud client_id...", Colors.BRIGHT_YELLOW))
        cid = discover_soundcloud_client_id()
        if cid:
            print(color(f"client_id descubierto: {cid}", Colors.BRIGHT_GREEN))
            try:
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'esvintable_config.json')
                # Guardar en config (opcional)
                import json
                cfg = {}
                if os.path.exists(cfg_path):
                    try:
                        with open(cfg_path, 'r', encoding='utf-8') as cf:
                            cfg = json.load(cf)
                    except Exception:
                        cfg = {}
                cfg['SOUNDCLOUD_CLIENT_ID'] = cid
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

# ===== PUNTO DE ENTRADA =====
def main():
    if not ensure_dependencies():
        print(color('No se pudieron instalar dependencias. Ejecuta manualmente pip install readchar requests cloudscraper mutagen pyacoustid', Colors.RED))
        return
    if not SOUNDCLOUD_CLIENT_ID:
        discover_soundcloud_client_id()
    updater.start_update_checker()
    updater.check_for_updates(silent=True)
    try:
        run_menu()
    except KeyboardInterrupt:
        print(color('\nHasta pronto!', Colors.BRIGHT_GREEN))
    finally:
        updater.stop_update_checker()

if __name__ == '__main__':
    main()
