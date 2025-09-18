#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esVintable Lite - Corregido y mejorado
Autor original: @JesusQuijada34
Adaptado y corregido por: ChatGPT (GPT-5 Thinking mini)
DescripciÃ³n:
 - Script para extraer ISRC de archivos de audio y descargar por ISRC desde proveedores.
 - AÃ±ade un pequeÃ±o servidor HTTP (Flask) para uso desde Android/Termux.
Instrucciones:
 - Ejecuta: python3 /path/to/esvintable_fixed.py
 - Desde Android puedes llamar a: http://<IP>:5000/extract_isrc?path=/ruta/al/archivo.mp3
 - AsegÃºrate de tener Python 3.8+ y permisos de lectura/escritura en los directorios.
"""

import os
import sys
import platform
import subprocess
import re
import time
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from threading import Thread, Event
import cloudscraper

# Dependencias de metadatos
try:
    import mutagen
    from mutagen.id3 import ID3, error as ID3error
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
except Exception:
    # will be handled by check_dependencies
    pass

# Intentar importar Flask (opcional, la app puede instalarlo)
FLASK_AVAILABLE = False
try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

# ===== CONFIGURACIÃ“N GLOBAL =====
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable_lite.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
LOCAL_XML_FILE = "details.xml"
UPDATE_INTERVAL = 10  # segundos
# El token original estaba truncado; reemplÃ¡zalo por uno vÃ¡lido si lo tienes
TOKEN = "eyjhbgcioijiuzi1niisinr5cci6ikpxvcj9.eyj1c2vyswqioiixodkyndq0mdeilcjkzxzpy2vjzci6ije1ndaynjiymcisinryyw5zywn0aw9uid"

# Proveedores de mÃºsica para bÃºsqueda ISRC
PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia',
    'Empire', 'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

# ===== DETECCIÃ“N DE PLATAFORMA =====
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

# Formatos de audio soportados
SUPPORTED_AUDIO = ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma')

# ===== COLORES PARA TERMINAL =====
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    BRIGHT_RED = '\033[38;5;196m'
    BRIGHT_GREEN = '\033[38;5;46m'
    BRIGHT_YELLOW = '\033[38;5;226m'
    BRIGHT_BLUE = '\033[38;5;21m'
    BRIGHT_CYAN = '\033[38;5;87m'
    BG_BLUE = '\033[44m'
    BG_RED = '\033[41m'

def color(text, color_code):
    try:
        return f"{color_code}{text}{Colors.END}"
    except Exception:
        return text

def clear():
    os.system('cls' if IS_WINDOWS else 'clear')

# ===== SISTEMA DE ACTUALIZACIÃ“N =====
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

    def get_remote_info_from_xml(self):
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                info = {}
                info['version'] = root.find('version').text.strip() if root.find('version') is not None else self.local_version
                info['changelog'] = root.find('changelog').text.strip() if root.find('changelog') is not None else ""
                info['release_date'] = root.find('release_date').text.strip() if root.find('release_date') is not None else ""
                info['critical'] = (root.find('critical').text.strip().lower() == 'true') if root.find('critical') is not None else False
                info['message'] = root.find('message').text.strip() if root.find('message') is not None else ""
                return info
        except Exception:
            return None

    def download_xml_update(self):
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                with open(LOCAL_XML_FILE, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception:
            return False

    def compare_versions(self, local_ver, remote_ver):
        try:
            def norm(v):
                return tuple(map(int, (v.split("."))))
            return norm(remote_ver) > norm(local_ver)
        except Exception:
            return remote_ver > local_ver

    def check_for_updates(self, silent=False):
        try:
            self.update_info = self.get_remote_info_from_xml()
            if self.update_info and 'version' in self.update_info:
                self.remote_version = self.update_info['version']
                if self.compare_versions(self.local_version, self.remote_version):
                    if self.download_xml_update():
                        self.local_version = self.remote_version
                    self.update_available = True
                    self.new_version = self.remote_version
                    if not silent and not self.notification_shown:
                        self.show_update_notification()
                        self.notification_shown = True
                    return True
        except Exception as e:
            if not silent:
                print(color(f"âŒ Error al verificar actualizaciones: {e}", Colors.RED))
        return False

    def show_update_notification(self):
        clear()
        print(color("â•”" + "â•" * 62 + "â•—", Colors.BRIGHT_BLUE))
        print(color("â•‘", Colors.BRIGHT_BLUE) + color("   ðŸŽ‰ ACTUALIZACIÃ“N DISPONIBLE   ", Colors.BG_BLUE + Colors.BRIGHT_YELLOW).center(62) + color("â•‘", Colors.BRIGHT_BLUE))
        print(color("â• " + "â•" * 62 + "â•£", Colors.BRIGHT_BLUE))
        print(color("â•‘", Colors.BRIGHT_BLUE) + color(f"   VersiÃ³n actual: {self.local_version:<10}", Colors.WHITE).ljust(62) + color("â•‘", Colors.BRIGHT_BLUE))
        print(color("â•‘", Colors.BRIGHT_BLUE) + color(f"   Nueva versiÃ³n:  {self.new_version:<10}", Colors.BRIGHT_GREEN).ljust(62) + color("â•‘", Colors.BRIGHT_BLUE))
        print(color("â•š" + "â•" * 62 + "â•", Colors.BRIGHT_BLUE))
        confirm = input("Â¿Deseas actualizar ahora? (s/n): ").strip().lower()
        if confirm == 's':
            self.download_script_update()

    def download_script_update(self):
        try:
            script_url = f"{REPO_RAW_URL}{SCRIPT_FILENAME}"
            response = requests.get(script_url, timeout=20)
            if response.status_code == 200:
                script_path = Path(__file__).resolve()
                backup_file = script_path.with_suffix('.backup.py')
                try:
                    with open(script_path, 'r', encoding='utf-8') as original:
                        original_text = original.read()
                except Exception:
                    original_text = ''
                with open(backup_file, 'w', encoding='utf-8') as b:
                    b.write(original_text)
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(color("âœ… Â¡ActualizaciÃ³n completada! Reiniciando...", Colors.BRIGHT_GREEN))
                time.sleep(2)
                os.execv(sys.executable, [sys.executable] + sys.argv)
                return True
        except Exception as e:
            print(color(f"âŒ Error descargando actualizaciÃ³n: {e}", Colors.RED))
        return False

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

# Instancia global
updater = UpdateChecker()

# ===== DEPENDENCIAS =====
def check_dependencies():
    """Verifica e instala dependencias automÃ¡ticamente"""
    required = ["requests", "cloudscraper", "mutagen", "flask"]
    missing = []
    for dep in required:
        try:
            __import__(dep)
        except Exception:
            missing.append(dep)
    if missing:
        print(color("âš ï¸  Instalando dependencias faltantes: " + ", ".join(missing), Colors.YELLOW))
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True, timeout=600)
            print(color("âœ… Dependencias instaladas correctamente", Colors.BRIGHT_GREEN))
            return True
        except subprocess.TimeoutExpired:
            print(color("âŒ Tiempo agotado instalando dependencias", Colors.RED))
            return False
        except Exception as e:
            print(color(f"âŒ Error instalando dependencias: {e}", Colors.RED))
            return False
    return True

# ===== EXTRACCIÃ“N DE ISRC =====
def extract_isrc(file_path):
    """Extrae ISRC y metadatos bÃ¡sicos de un archivo de audio"""
    result = {
        'file': file_path,
        'filename': os.path.basename(file_path),
        'isrc': None,
        'artist': None,
        'title': None,
        'method': None,
        'error': None
    }
    try:
        audiofile = None
        lower = file_path.lower()
        if lower.endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                try:
                    audiofile = ID3(file_path)
                except Exception:
                    audiofile = None
        elif lower.endswith('.flac'):
            audiofile = FLAC(file_path)
        elif lower.endswith(('.m4a', '.mp4')):
            audiofile = MP4(file_path)

        if audiofile:
            # Buscar campos ISRC (varÃ­a por formato)
            candidates = ['isrc', 'ISRC', 'TSRC']
            for field in candidates:
                try:
                    if field in audiofile:
                        val = audiofile[field]
                        if isinstance(val, list):
                            val = val[0]
                        result['isrc'] = str(val).strip().upper()
                        result['method'] = f"metadata:{field}"
                        break
                except Exception:
                    continue

            # Artista/tÃ­tulo
            try:
                if 'artist' in audiofile:
                    a = audiofile.get('artist')
                    if isinstance(a, (list, tuple)):
                        result['artist'] = a[0]
                    else:
                        result['artist'] = str(a)
            except Exception:
                pass
            try:
                if 'title' in audiofile:
                    t = audiofile.get('title')
                    if isinstance(t, (list, tuple)):
                        result['title'] = t[0]
                    else:
                        result['title'] = str(t)
            except Exception:
                pass
    except Exception as e:
        result['error'] = f"Mutagen error: {e}"

    # Si no se encuentra ISRC en metadatos, buscar en binary (hex)
    if not result['isrc']:
        try:
            with open(file_path, 'rb') as f:
                # Leer bloques (principio y final)
                head = f.read(200000)
                try:
                    f.seek(-200000, os.SEEK_END)
                    tail = f.read(200000)
                except Exception:
                    tail = b''
                content = head + tail
                patterns = [
                    br'ISRC[=:]\s*([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'isrc[=:]\s*([A-Z]{2}[A-Z0-9]{3}\d{5})'
                ]
                for i, pat in enumerate(patterns):
                    m = re.search(pat, content, re.IGNORECASE)
                    if m:
                        found = m.group(1) if m.lastindex else m.group(0)
                        if isinstance(found, bytes):
                            found = found.decode('utf-8', errors='ignore')
                        found = found.strip().upper()
                        if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found):
                            result['isrc'] = found
                            result['method'] = f"hex_match_{i+1}"
                            break
        except Exception as e:
            if not result.get('error'):
                result['error'] = f"Hex scan error: {e}"

    return result

def display_file_info(info):
    isrc_color = Colors.BRIGHT_GREEN if info.get('isrc') else Colors.BRIGHT_RED
    isrc_text = info.get('isrc') or 'No encontrado'
    print(color(f"ðŸ“ Archivo: {info['filename']}", Colors.BRIGHT_BLUE))
    print(f"   ðŸŽµ {color('TÃ­tulo:', Colors.BOLD)} {info.get('title', 'Desconocido')}")
    print(f"   ðŸŽ¤ {color('Artista:', Colors.BOLD)} {info.get('artist', 'Desconocido')}")
    print(f"   ðŸ·ï¸  {color('ISRC:', Colors.BOLD)} {color(isrc_text, isrc_color)}")
    if info.get('method'):
        print(f"   ðŸ” {color('MÃ©todo:', Colors.BOLD)} {info['method']}")
    if info.get('error'):
        print(f"   âš ï¸  {color('Error:', Colors.BRIGHT_RED)} {info['error']}")

# ===== BÃšSQUEDA Y DESCARGA POR ISRC =====
def download_by_isrc(isrc, output_dir="descargas_isrc"):
    """Descarga una canciÃ³n por su cÃ³digo ISRC desde los proveedores conocidos"""
    scraper = cloudscraper.create_scraper()
    print(color(f"ðŸ” Buscando ISRC: {isrc}", Colors.BRIGHT_CYAN))
    for provider in PROVIDERS:
        try:
            url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
            headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
            print(color(f"   Probando {provider}...", Colors.BRIGHT_YELLOW))
            response = scraper.get(url, headers=headers, timeout=20)
            if response.status_code == 200 and response.content:
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.join(output_dir, f"{isrc}_{provider}.m4a")
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(color(f"âœ… Descargado: {filename}", Colors.BRIGHT_GREEN))
                return True, filename
            elif response.status_code == 404:
                print(color(f"   âŒ No encontrado en {provider}", Colors.BRIGHT_RED))
            else:
                print(color(f"   âš ï¸  CÃ³digo {response.status_code} en {provider}", Colors.BRIGHT_YELLOW))
        except Exception as e:
            print(color(f"   âš ï¸  Error con {provider}: {e}", Colors.BRIGHT_YELLOW))
            continue
    return False, None

def search_isrc_in_directory(directory):
    print(color(f"ðŸ” Buscando ISRC en: {directory}", Colors.BRIGHT_CYAN))
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    if not audio_files:
        print(color("âŒ No se encontraron archivos de audio", Colors.RED))
        time.sleep(1)
        return []
    found = []
    total = len(audio_files)
    for i, fp in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(fp)[:40]}...", Colors.BRIGHT_YELLOW), end="\r")
        info = extract_isrc(fp)
        if info.get('isrc'):
            found.append(info)
    print()
    return found

def search_specific_isrc_interactive():
    clear()
    print(color("ðŸ” BÃºsqueda de ISRC EspecÃ­fico", Colors.BOLD))
    isrc_code = input("Introduce el cÃ³digo ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
        print(color("âŒ Formato ISRC invÃ¡lido", Colors.RED))
        time.sleep(1)
        return
    directory = input("Directorio donde buscar (Enter para actual): ").strip() or "."
    if not os.path.isdir(directory):
        print(color("âŒ Directorio no encontrado", Colors.RED))
        time.sleep(1)
        return
    found = []
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    total = len(audio_files)
    for i, fp in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(fp)[:30]}...", Colors.BRIGHT_YELLOW), end="\r")
        info = extract_isrc(fp)
        if info.get('isrc') and info['isrc'].upper() == isrc_code:
            found.append(info)
    print()
    if found:
        print(color(f"âœ… Se encontraron {len(found)} archivos con ISRC {isrc_code}:", Colors.BRIGHT_GREEN))
        for info in found:
            display_file_info(info)
            print()
    else:
        print(color(f"âŒ No se encontraron archivos con ISRC {isrc_code}", Colors.BRIGHT_RED))
    input("\nPresiona Enter para continuar...")

# ===== API PARA ANDROID (FLASK) =====
api_thread = None
api_app = None

def start_api(host='0.0.0.0', port=5000):
    """Inicia la API Flask en un hilo separado. Retorna True si se lanza o estaba disponible."""
    global api_thread, api_app, FLASK_AVAILABLE
    if not FLASK_AVAILABLE:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True, timeout=300)
            # re-import
            from importlib import reload
            import flask
            from flask import Flask, request, jsonify
            FLASK_AVAILABLE = True
        except Exception as e:
            print(color(f"âŒ No se pudo instalar Flask: {e}", Colors.RED))
            return False

    if api_thread and api_thread.is_alive():
        print(color("âœ… API ya en ejecuciÃ³n", Colors.BRIGHT_GREEN))
        return True

    from flask import Flask, request, jsonify
    app = Flask("esvintable_api")

    @app.route("/extract_isrc", methods=["GET"])
    def api_extract_isrc():
        path = request.args.get("path") or request.json and request.json.get("path")
        if not path:
            return jsonify({"error": "ParÃ¡metro 'path' requerido"}), 400
        if not os.path.isfile(path):
            return jsonify({"error": "Archivo no encontrado", "path": path}), 404
        info = extract_isrc(path)
        return jsonify(info)

    @app.route("/search_dir", methods=["GET"])
    def api_search_dir():
        directory = request.args.get("dir") or request.json and request.json.get("dir") or "."
        if not os.path.isdir(directory):
            return jsonify({"error": "Directorio no encontrado", "dir": directory}), 404
        found = search_isrc_in_directory(directory)
        return jsonify({"count": len(found), "results": found})

    @app.route("/download", methods=["POST", "GET"])
    def api_download():
        isrc = request.args.get("isrc") or (request.json and request.json.get("isrc"))
        out = request.args.get("out") or (request.json and request.json.get("out")) or "descargas_isrc"
        if not isrc:
            return jsonify({"error": "ParÃ¡metro 'isrc' requerido"}), 400
        ok, filename = download_by_isrc(isrc, out)
        if ok:
            return jsonify({"ok": True, "file": filename})
        return jsonify({"ok": False, "file": None}), 404

    def run_app():
        try:
            app.run(host=host, port=int(port), threaded=True)
        except Exception as e:
            print(color(f"âŒ Error en API: {e}", Colors.RED))

    api_app = app
    api_thread = Thread(target=run_app, daemon=True)
    api_thread.start()
    time.sleep(0.5)
    print(color(f"âœ… API iniciada en http://{host}:{port}", Colors.BRIGHT_GREEN))
    return True

# ===== MENÃš PRINCIPAL =====
def print_banner():
    banner = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘{Colors.MAGENTA}                   ESVINTABLE LITE v{updater.local_version:<8}               {Colors.BRIGHT_CYAN}â•‘
â•‘{Colors.GREEN}       BÃºsqueda y Descarga por ISRC - Multiplataforma        {Colors.BRIGHT_CYAN}â•‘
â•‘{Colors.YELLOW}         GitHub.com/JesusQuijada34/esvintable              {Colors.BRIGHT_CYAN}â•‘
â•‘{Colors.WHITE}                Plataforma: {PLATFORM_LABEL:<20}             {Colors.BRIGHT_CYAN}â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{Colors.END}"""
    print(banner)

def main_menu():
    clear()
    print_banner()
    if updater.update_available and not updater.notification_shown:
        print(color(f"ðŸ”” Â¡ActualizaciÃ³n disponible! v{updater.new_version} - Ejecuta opciÃ³n 5", Colors.BRIGHT_GREEN))
    print(color("ðŸ› ï¸  OPCIONES DISPONIBLES:", Colors.BRIGHT_YELLOW))
    print("1. ðŸ” Buscar ISRC en archivo individual")
    print("2. ðŸ“ Buscar ISRC en directorio")
    print("3. ðŸ·ï¸  Buscar ISRC especÃ­fico")
    print("4. ðŸ“¥ Descargar por ISRC")
    print("5. ðŸ”„ Verificar actualizaciones")
    print("6. ðŸ“‚ Explorador de archivos (UI)")
    print("7. ðŸŒ Iniciar API para Android (Flask)")
    print("8. âŒ Salir\n")
    return input("Selecciona una opciÃ³n: ").strip()

def file_browser(start_path="."):
    current_path = os.path.abspath(start_path)
    selected_file = None
    while True:
        clear()
        print(color(f"ðŸ“ Navegando: {current_path}", Colors.BRIGHT_BLUE))
        print(color("=" * 60, Colors.BRIGHT_CYAN))
        try:
            items = os.listdir(current_path)
        except PermissionError:
            print(color("âŒ Permiso denegado para acceder a este directorio", Colors.RED))
            time.sleep(1)
            return None
        directories = []
        audio_files = []
        others = []
        for item in sorted(items):
            p = os.path.join(current_path, item)
            if os.path.isdir(p):
                directories.append(item)
            elif os.path.isfile(p):
                if item.lower().endswith(SUPPORTED_AUDIO):
                    audio_files.append(item)
                else:
                    others.append(item)
        idx = 1
        for d in directories:
            print(color(f"{idx:3d}. {d}/", Colors.BRIGHT_BLUE))
            idx += 1
        for f in audio_files:
            print(color(f"{idx:3d}. {f}", Colors.BRIGHT_GREEN))
            idx += 1
        print("\n0. Volver")
        print("99. Seleccionar este directorio")
        print("100. Extraer ISRC del archivo seleccionado")
        print("101. Buscar ISRC en este directorio")
        print("102. Volver al menÃº principal")
        if selected_file:
            print(color("\nArchivo seleccionado: " + selected_file, Colors.BRIGHT_CYAN))
        choice = input("\nSelecciona una opciÃ³n: ").strip()
        if choice == "0":
            if current_path != os.path.abspath(start_path):
                current_path = os.path.dirname(current_path)
            selected_file = None
        elif choice == "99":
            return current_path
        elif choice == "100":
            if selected_file and os.path.isfile(selected_file):
                info = extract_isrc(selected_file)
                clear()
                display_file_info(info)
                input("\nPresiona Enter para continuar...")
            else:
                print(color("âŒ No hay archivo seleccionado", Colors.RED))
                time.sleep(1)
        elif choice == "101":
            search_isrc_in_directory(current_path)
            input("\nPresiona Enter para continuar...")
        elif choice == "102":
            return None
        else:
            try:
                n = int(choice) - 1
                if n < len(directories):
                    current_path = os.path.join(current_path, directories[n])
                    selected_file = None
                elif n < len(directories) + len(audio_files):
                    file_index = n - len(directories)
                    selected_file = os.path.join(current_path, audio_files[file_index])
                else:
                    print(color("âŒ OpciÃ³n invÃ¡lida", Colors.RED))
                    time.sleep(1)
            except Exception:
                print(color("âŒ OpciÃ³n invÃ¡lida", Colors.RED))
                time.sleep(1)

def main():
    # Verificar dependencias
    if not check_dependencies():
        print(color("âŒ No se pudieron instalar las dependencias necesarias", Colors.RED))
        return
    # actualizar FLASK_AVAILABLE si se instalÃ³
    global FLASK_AVAILABLE
    try:
        from flask import Flask  # noqa: F401
        FLASK_AVAILABLE = True
    except Exception:
        FLASK_AVAILABLE = False

    updater.start_update_checker()
    updater.check_for_updates(silent=True)
    try:
        while True:
            choice = main_menu()
            if choice == "1":
                file_path = input("Introduce la ruta del archivo: ").strip()
                if os.path.isfile(file_path):
                    info = extract_isrc(file_path)
                    clear()
                    display_file_info(info)
                    if info.get('isrc'):
                        download = input("Â¿Descargar versiÃ³n de alta calidad? (s/n): ").strip().lower()
                        if download == 's':
                            download_by_isrc(info['isrc'], os.path.dirname(file_path))
                    input("\nPresiona Enter para continuar...")
                else:
                    print(color("âŒ Archivo no encontrado", Colors.RED))
                    time.sleep(1)
            elif choice == "2":
                directory = input("Introduce la ruta del directorio: ").strip()
                if os.path.isdir(directory):
                    found = search_isrc_in_directory(directory)
                    clear()
                    if found:
                        print(color(f"âœ… Se encontraron {len(found)} archivos con ISRC", Colors.BRIGHT_GREEN))
                        for info in found:
                            display_file_info(info)
                            print("-" * 40)
                    else:
                        print(color("âŒ No se encontraron archivos con ISRC", Colors.BRIGHT_RED))
                    input("\nPresiona Enter para continuar...")
                else:
                    print(color("âŒ Directorio no encontrado", Colors.RED))
                    time.sleep(1)
            elif choice == "3":
                search_specific_isrc_interactive()
            elif choice == "4":
                isrc_code = input("Introduce el cÃ³digo ISRC: ").strip().upper()
                if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
                    print(color("âŒ Formato ISRC invÃ¡lido", Colors.RED))
                    time.sleep(1)
                    continue
                output_dir = input("Directorio de descarga (Enter para 'descargas_isrc'): ").strip() or "descargas_isrc"
                success, filename = download_by_isrc(isrc_code, output_dir)
                if success:
                    print(color(f"âœ… Descarga completada: {filename}", Colors.BRIGHT_GREEN))
                else:
                    print(color("âŒ No se pudo descargar el archivo", Colors.BRIGHT_RED))
                input("\nPresiona Enter para continuar...")
            elif choice == "5":
                clear()
                print(color("ðŸ” Buscando actualizaciones...", Colors.YELLOW))
                updater.check_for_updates(silent=False)
                input("\nPresiona Enter para continuar...")
            elif choice == "6":
                start_dir = input("Directorio inicial (Enter para actual): ").strip() or "."
                file_browser(start_dir)
            elif choice == "7":
                host = input("Host para la API (Enter para 0.0.0.0): ").strip() or "0.0.0.0"
                port = input("Puerto para la API (Enter para 5000): ").strip() or "5000"
                start_api(host, port)
                input("\nPresiona Enter para continuar...")
            elif choice == "8":
                print(color("ðŸ‘‹ Â¡Hasta pronto!", Colors.BRIGHT_GREEN))
                updater.stop_update_checker()
                break
            else:
                print(color("âŒ OpciÃ³n no vÃ¡lida", Colors.RED))
                time.sleep(1)
    except KeyboardInterrupt:
        print(color("\nðŸ‘‹ Â¡Hasta pronto!", Colors.BRIGHT_GREEN))
        updater.stop_update_checker()

if __name__ == "__main__":
    main()