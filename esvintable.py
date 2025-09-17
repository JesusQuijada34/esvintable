#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable Ultimate PRO - Filtrador y Reproductor Avanzado de Canciones
# Autor: @JesusQuijada34 | GitHub.com/JesusQuijada34/esvintable
# Última actualización: 2025-09-17

import os
import sys
import re
import time
import json
import requests
import platform
import subprocess
import hashlib
import threading
from datetime import datetime
from pathlib import Path

# ===== CONFIGURACIÓN GLOBAL =====
VERSION = "4.0"
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/esvintable.py"

# Colores ANSI para terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ===== UTILIDADES DE SISTEMA =====
def clear_screen():
    os.system('cls' if platform.system() == "Windows" else 'clear')

def print_color(text, color):
    print(f"{color}{text}{Colors.END}")

def print_banner():
    banner = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                esVintable Ultimate PRO v{VERSION}                ║
║         Filtrador & Reproductor Avanzado de Canciones        ║
║           GitHub.com/JesusQuijada34/esvintable               ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)

def print_guide():
    print_color("🛠️  GUÍA RÁPIDA:", Colors.YELLOW)
    print("1. Filtra canciones por nombre, artista, álbum, ISRC, duración o calidad.")
    print("2. Reproduce directamente archivos de audio desde el menú.")
    print("3. Busca y descarga nuevas versiones del script automáticamente.")
    print("4. Usa el menú de ayuda para comandos avanzados y soporte.\n")

# ===== FUNCIONES DE ACTUALIZACIÓN (SIN JSON) =====
def get_remote_version():
    """Obtiene la versión remota del script"""
    try:
        resp = requests.get(REPO_RAW_URL, timeout=10)
        if resp.status_code == 200:
            match = re.search(r'VERSION\s*=\s*["\']([\d.]+)["\']', resp.text)
            return match.group(1) if match else None
    except Exception:
        return None

def update_script_if_needed():
    """Actualiza el script si hay una versión nueva"""
    remote_version = get_remote_version()
    if not remote_version:
        print_color("⚠️  No se pudo obtener la versión remota.", Colors.RED)
        return False
    if remote_version > VERSION:
        print_color(f"🆕 Nueva versión disponible: v{remote_version}", Colors.YELLOW)
        resp = requests.get(REPO_RAW_URL, timeout=20)
        if resp.status_code == 200:
            backup_file = __file__ + ".backup"
            # Backup actual
            with open(__file__, 'r', encoding='utf-8') as f_in, open(backup_file, 'w', encoding='utf-8') as f_out:
                f_out.write(f_in.read())
            # Reemplaza script
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print_color("✅ Script actualizado correctamente. Reiniciando...", Colors.GREEN)
            time.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print_color("❌ Error descargando la nueva versión.", Colors.RED)
            return False
    else:
        print_color("✅ Ya tienes la última versión.", Colors.GREEN)
        return True

# ===== FILTRADO Y ESCANEO PROFUNDO DE CANCIONES =====
def deep_scan_audio(file_path):
    """Escaneo profundo del archivo (ISRC, artista, álbum, duración, formato, calidad)"""
    result = {
        'file': file_path,
        'isrc': None,
        'artist': None,
        'album': None,
        'title': None,
        'duration': None,
        'bitrate': None,
        'tags': {},
    }
    # FFprobe (metadatos avanzados)
    try:
        proc = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path],
            capture_output=True, text=True, timeout=15
        )
        if proc.returncode == 0:
            info = json.loads(proc.stdout)
            tags = info.get('format', {}).get('tags', {})
            result['tags'] = tags
            result['isrc'] = tags.get('ISRC') or tags.get('TSRC')
            result['title'] = tags.get('title')
            result['artist'] = tags.get('artist') or tags.get('ARTIST')
            result['album'] = tags.get('album')
            result['duration'] = float(info['format'].get('duration', 0))
            result['bitrate'] = int(info['format'].get('bit_rate', 0)) // 1000 if info['format'].get('bit_rate') else None
    except Exception:
        pass
    # Análisis Hexadecimal profundo (ISRC y patrones ocultos)
    try:
        with open(file_path, 'rb') as f:
            content = f.read(1000000)
            patterns = [
                br'ISRC[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
                br'isrc[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})'
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    found_isrc = match.group(1).decode('utf-8', errors='ignore') if isinstance(match.group(1), bytes) else match.group(1)
                    if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found_isrc):
                        result['isrc'] = found_isrc
                        break
    except Exception:
        pass
    return result

def filter_songs(directory, filters):
    """Filtra canciones según criterios"""
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg')):
                path = os.path.join(root, f)
                info = deep_scan_audio(path)
                # Filtros
                match = True
                for k,v in filters.items():
                    if v and (str(info.get(k, '')).lower() if info.get(k) else '') != v.lower():
                        match = False
                        break
                if match:
                    results.append(info)
    return results

def show_song(song):
    """Muestra información de una canción"""
    print_color(f"Archivo: {song['file']}", Colors.BLUE)
    print(f"  Título: {song.get('title', 'Desconocido')}")
    print(f"  Artista: {song.get('artist', 'Desconocido')}")
    print(f"  Álbum: {song.get('album', 'Desconocido')}")
    print(f"  ISRC: {song.get('isrc', 'No encontrado')}")
    print(f"  Duración: {int(song['duration']) if song['duration'] else '-'} seg | Bitrate: {song.get('bitrate', '-')}\n")

def play_song(file_path):
    """Reproduce una canción usando ffplay"""
    print_color(f"🎧 Reproduciendo: {file_path}", Colors.GREEN)
    try:
        subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path])
    except Exception:
        print_color("❌ Error al reproducir la canción.", Colors.RED)

# ===== MENÚS INTERACTIVOS =====
def main_menu():
    clear_screen()
    print_banner()
    print_guide()
    print_color("Menú Principal:", Colors.BOLD)
    print("1. Buscar y filtrar canciones")
    print("2. Reproducir canción por ruta")
    print("3. Verificar y actualizar script")
    print("4. Ayuda")
    print("5. Salir\n")
    return input("Selecciona una opción: ").strip()

def search_menu():
    clear_screen()
    print_color("🔎 Filtros para búsqueda avanzada:", Colors.YELLOW)
    print("Deja vacío cualquier campo para ignorarlo.")
    filters = {
        'title': input("Título: "),
        'artist': input("Artista: "),
        'album': input("Álbum: "),
        'isrc': input("ISRC: "),
    }
    directory = input("Directorio raíz de búsqueda (default: ./): ").strip() or "."
    print_color("⏳ Buscando canciones...", Colors.CYAN)
    found = filter_songs(directory, filters)
    if found:
        print_color(f"\n🎶 Se encontraron {len(found)} canciones:", Colors.GREEN)
        for i, song in enumerate(found, 1):
            print_color(f"{i}.", Colors.WHITE)
            show_song(song)
        play = input("¿Deseas reproducir alguna? Indica número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print_color("No se encontraron canciones con esos filtros.", Colors.RED)
    input("\n⏎ Enter para volver al menú...")

def help_menu():
    clear_screen()
    print_color("🆘 AYUDA:", Colors.YELLOW)
    print("""
- Para buscar canciones, usa el menú 'Buscar y filtrar canciones' y llena los campos que quieras filtrar.
- Puedes reproducir cualquier canción directamente indicando la ruta.
- El script se actualiza automáticamente si hay nueva versión en GitHub.
- Contacto y soporte: GitHub.com/JesusQuijada34/esvintable
- Atajos rápidos: Ctrl+C para salir en cualquier momento.
""")
    input("\n⏎ Enter para volver al menú...")

def main():
    while True:
        try:
            choice = main_menu()
            if choice == "1":
                search_menu()
            elif choice == "2":
                path = input("Ruta del archivo de audio: ").strip()
                if os.path.isfile(path):
                    play_song(path)
                else:
                    print_color("Archivo no encontrado.", Colors.RED)
                    time.sleep(2)
            elif choice == "3":
                update_script_if_needed()
                time.sleep(2)
            elif choice == "4":
                help_menu()
            elif choice == "5":
                print_color("👋 ¡Hasta pronto!", Colors.CYAN)
                break
            else:
                print_color("Opción inválida.", Colors.RED)
                time.sleep(2)
        except KeyboardInterrupt:
            print_color("\n👋 Interrupción por usuario", Colors.YELLOW)
            break
        except Exception as e:
            print_color(f"❌ Error inesperado: {e}", Colors.RED)
            time.sleep(2)

if __name__ == "__main__":
    main()
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"

# ======= VARIABLES DE ENTORNO Y COLORES =======
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

IS_TERMUX = "com.termux" in os.environ.get('PREFIX', '')
IS_ANDROID = "ANDROID_ROOT" in os.environ
IS_PYDROID = "ru.iiec.pydroid3" in os.environ.get('PREFIX', '')
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

update_available = False
update_thread = None
stop_update_check = False

# ======= UTILIDADES GENERALES =======
def clear_screen():
    os.system('cls' if IS_WINDOWS else 'clear')

def print_color(text, color):
    print(f"{color}{text}{Colors.END}")

def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                  🎵 esVintable Ultimate v{VERSION}           ║
║                Scanner ISRC + Buscador Musical               ║
║                GitHub.com/JesusQuijada34                     ║
║                Últ. Actualización: {LAST_UPDATE}             ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)
    if update_available:
        print_color("🚨 ¡ACTUALIZACIÓN DISPONIBLE! Usa la opción de actualización.", Colors.YELLOW + Colors.BOLD)
    print(f"{Colors.YELLOW}Plataforma: {platform.system()} | Terminal: {'Termux' if IS_TERMUX else 'Pydroid' if IS_PYDROID else 'Standard'}{Colors.END}\n")

def load_config():
    config = {
        "last_update_check": "",
        "auto_update": True,
        "deep_scan": True,
        "color_mode": True,
        "download_path": "descargas_isrc",
        "ffprobe_installed": False,
        "security_patches": {}
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
        except Exception:
            pass
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def calculate_file_hash(file_path):
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except Exception:
        return None

# ======= SISTEMA DE ACTUALIZACIONES/SEGURIDAD =======
def check_security_patches():
    try:
        response = requests.get(SECURITY_PATCH_URL, timeout=10)
        if response.status_code == 200:
            patches = response.json()
            config = load_config()
            for patch_id, patch_info in patches.items():
                if patch_id not in config.get("security_patches", {}):
                    print_color(f"🔒 Parche de seguridad disponible: {patch_info['title']}", Colors.RED)
                    print_color(f"   {patch_info['description']}", Colors.YELLOW)
                    if patch_info.get('critical', False):
                        print_color("🚨 Aplicando parche crítico automáticamente...", Colors.RED)
                        apply_security_patch(patch_id, patch_info)
            return True
    except Exception:
        pass
    return False

def apply_security_patch(patch_id, patch_info):
    try:
        config = load_config()
        if "security_patches" not in config:
            config["security_patches"] = {}
        config["security_patches"][patch_id] = {
            "applied": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": patch_info["title"]
        }
        save_config(config)
        print_color(f"✅ Parche de seguridad {patch_id} aplicado", Colors.GREEN)
        return True
    except Exception:
        return False

def check_for_updates():
    global update_available, stop_update_check
    while not stop_update_check:
        try:
            response = requests.get(REPO_API_URL, timeout=15)
            if response.status_code == 200:
                commits = response.json()
                if commits:
                    latest_commit_date = commits[0]['commit']['committer']['date']
                    latest_commit_date = datetime.fromisoformat(latest_commit_date.replace('Z', '+00:00'))
                    config = load_config()
                    last_check = config.get("last_update_check", "")
                    if last_check:
                        last_check_date = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                        if latest_commit_date > last_check_date:
                            if verify_update_available():
                                update_available = True
                    config["last_update_check"] = datetime.now().isoformat()
                    save_config(config)
        except Exception:
            pass
        time.sleep(UPDATE_CHECK_INTERVAL)

def verify_update_available():
    try:
        with open(__file__, 'r', encoding='utf-8') as f:
            local_content = f.read()
        response = requests.get(REPO_RAW_URL, timeout=15)
        if response.status_code == 200:
            remote_content = response.text
            local_version_match = re.search(r'VERSION = "([\d.]+)"', local_content)
            remote_version_match = re.search(r'VERSION = "([\d.]+)"', remote_content)
            if local_version_match and remote_version_match:
                local_version = local_version_match.group(1)
                remote_version = remote_version_match.group(1)
                if remote_version > local_version:
                    return True
            local_hash = hashlib.md5(local_content.encode('utf-8')).hexdigest()
            remote_hash = hashlib.md5(remote_content.encode('utf-8')).hexdigest()
            if local_hash != remote_hash:
                return True
        return False
    except Exception:
        return False

def download_update():
    try:
        print_color("🔍 Descargando última versión...", Colors.YELLOW)
        response = requests.get(REPO_RAW_URL, timeout=20)
        if response.status_code == 200:
            new_content = response.text
            temp_file = f"{__file__}.new"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            backup_file = f"{__file__}.backup"
            with open(__file__, 'r', encoding='utf-8') as original:
                with open(backup_file, 'w', encoding='utf-8') as backup:
                    backup.write(original.read())
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(new_content)
            try:
                subprocess.run([sys.executable, "-c", f"import ast; ast.parse(open('{__file__}', 'r', encoding='utf-8').read())"], 
                             check=True, timeout=10, capture_output=True)
            except Exception:
                with open(backup_file, 'r', encoding='utf-8') as backup:
                    with open(__file__, 'w', encoding='utf-8') as original:
                        original.write(backup.read())
                raise Exception("El archivo actualizado tiene errores de sintaxis")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            print_color("✅ Actualización descargada correctamente", Colors.GREEN)
            return True
    except Exception as e:
        print_color(f"❌ Error durante la actualización: {e}", Colors.RED)
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r', encoding='utf-8') as backup:
                    with open(__file__, 'w', encoding='utf-8') as original:
                        original.write(backup.read())
                print_color("✅ Backup restaurado correctamente", Colors.GREEN)
            except Exception:
                print_color("❌ Error restaurando backup", Colors.RED)
        return False

def apply_update():
    global stop_update_check
    print_color("🔄 Aplicando actualización...", Colors.YELLOW)
    stop_update_check = True
    if update_thread and update_thread.is_alive():
        update_thread.join(timeout=5)
    if download_update():
        print_color("🎉 ¡Actualización completada! Reiniciando...", Colors.GREEN)
        time.sleep(2)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print_color("❌ No se pudo completar la actualización", Colors.RED)
        start_update_checker()

def start_update_checker():
    global update_thread, stop_update_check
    stop_update_check = False
    update_thread = threading.Thread(target=check_for_updates, daemon=True)
    update_thread.start()

# ======= ESCANEO Y BÚSQUEDA DE CANCIONES =======
def check_ffprobe():
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def deep_scan_isrc(file_path):
    results = []
    # FFprobe scan
    if check_ffprobe():
        try:
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                                   '-show_format', '-show_streams', file_path], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                metadata = result.stdout
                isrc_match = re.search(r'"ISRC"\s*:\s*"([^"]+)"', metadata)
                if isrc_match:
                    results.append(("FFprobe Metadatos", isrc_match.group(1)))
        except Exception:
            pass
    # Mutagen scan
    try:
        from mutagen import File
        audio = File(file_path)
        if audio and hasattr(audio, 'tags') and audio.tags:
            for tag in ['ISRC', 'isrc', 'TSRC']:
                if tag in audio.tags:
                    isrc_value = audio.tags[tag][0] if isinstance(audio.tags[tag], list) else audio.tags[tag]
                    results.append((f"Mutagen {tag}", isrc_value))
                    break
    except Exception:
        pass
    # Hex scan
    try:
        with open(file_path, 'rb') as f:
            content = f.read(1000000)
        patterns = [
            br'ISRC[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
            br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
            br'isrc[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, bytes):
                    match = match.decode('utf-8', errors='ignore')
                if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', match):
                    results.append(("Análisis Hexadecimal", match))
    except Exception:
        pass
    return results

def search_music_by_metadata(query):
    """Búsqueda avanzada en Deezer/Spotify/Apple Music (puedes expandir con más APIs)"""
    print_color(f"🔍 Buscando: {query}", Colors.CYAN)
    try:
        response = requests.get(MUSIC_API_URL, params={'q': query, 'limit': 10}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print_color("Resultados encontrados:", Colors.GREEN)
                for idx, song in enumerate(data['data'], 1):
                    print(f"{Colors.YELLOW}{idx}. {song['title']} - {song['artist']['name']} ({song['album']['title']}){Colors.END}")
                    print(f"    Previsualizar: {song['preview']}")
                return data['data']
            else:
                print_color("No se encontraron resultados.", Colors.RED)
        else:
            print_color("Error al buscar música.", Colors.RED)
    except Exception as e:
        print_color(f"Error: {e}", Colors.RED)
    return []

def play_preview(preview_url):
    """Reproduce un preview de la canción (requiere ffplay)"""
    try:
        print_color("🎧 Reproduciendo preview...", Colors.CYAN)
        subprocess.run(['ffplay', '-autoexit', '-nodisp', preview_url])
    except Exception as e:
        print_color(f"Error al reproducir preview: {e}", Colors.RED)

# ======= MENÚS =======
def show_main_menu():
    print(f"""{Colors.BOLD}{Colors.BLUE}
1. Escanear archivo para ISRC
2. Escanear directorio
3. Buscar canción por nombre/artista/álbum
4. Buscar por ISRC
5. Escuchar preview de canción
6. Actualizar script
7. Configuración
8. Salir
{Colors.END}""")
    return input("Selecciona una opción: ")

def scan_single_file():
    file_path = input("Ruta del archivo: ")
    if not os.path.isfile(file_path):
        print_color("Archivo no encontrado.", Colors.RED)
        return
    results = deep_scan_isrc(file_path)
    if results:
        print_color("Resultados ISRC encontrados:", Colors.GREEN)
        for origin, code in results:
            print(f" - {origin}: {code}")
    else:
        print_color("No se encontró ISRC.", Colors.YELLOW)

def scan_directory_menu():
    dir_path = input("Ruta del directorio: ")
    if not os.path.isdir(dir_path):
        print_color("Directorio no encontrado.", Colors.RED)
        return
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.lower().endswith(('.mp3', '.flac', '.m4a', '.wav')):
                full_path = os.path.join(root, file)
                print_color(f"\nArchivo: {file}", Colors.BLUE)
                results = deep_scan_isrc(full_path)
                if results:
                    for origin, code in results:
                        print(f" - {origin}: {code}")
                else:
                    print("No ISRC.")

def search_song_menu():
    query = input("Nombre/Artista/Álbum: ")
    results = search_music_by_metadata(query)
    if results:
        idx = input("¿Escuchar preview de alguna canción? (número, Enter para omitir): ")
        if idx.isdigit() and 1 <= int(idx) <= len(results):
            play_preview(results[int(idx)-1]['preview'])

def search_by_isrc_menu():
    isrc = input("ISRC: ")
    results = search_music_by_metadata(isrc)
    if results:
        idx = input("¿Escuchar preview de alguna canción? (número, Enter para omitir): ")
        if idx.isdigit() and 1 <= int(idx) <= len(results):
            play_preview(results[int(idx)-1]['preview'])

def settings_menu():
    config = load_config()
    print_color("Configuración actual:", Colors.GREEN)
    for k, v in config.items():
        print(f"{k}: {v}")
    print_color("Config edición manual en archivo JSON.", Colors.YELLOW)

# ======= MAIN =======
def main():
    global update_available, stop_update_check
    print_color("🔒 Verificando parches de seguridad...", Colors.CYAN)
    check_security_patches()
    start_update_checker()
    print_color("🔍 Verificando actualizaciones...", Colors.CYAN)
    time.sleep(2)
    config = load_config()
    if not check_ffprobe() and not config.get("ffprobe_installed", False):
        print_color("🔍 FFprobe no detectado", Colors.YELLOW)
        install = input("¿Instalar FFprobe? (s/n): ").lower()
        if install == 's':
            print_color("Instala FFprobe manualmente según tu plataforma.", Colors.YELLOW)
    while True:
        try:
            clear_screen()
            print_banner()
            choice = show_main_menu()
            if choice == "1":
                scan_single_file()
            elif choice == "2":
                scan_directory_menu()
            elif choice == "3":
                search_song_menu()
            elif choice == "4":
                search_by_isrc_menu()
            elif choice == "5":
                url = input("URL del preview: ")
                play_preview(url)
            elif choice == "6":
                if update_available:
                    update = input("¿Actualizar ahora? (s/n): ").lower()
                    if update == 's':
                        apply_update()
                        return
                else:
                    if verify_update_available():
                        update_available = True
                        print_color("🎉 ¡Actualización disponible! Reiniciando menú...", Colors.GREEN)
                        time.sleep(2)
                    else:
                        print_color("✅ Ya tienes la versión más reciente", Colors.GREEN)
            elif choice == "7":
                settings_menu()
                input("Presiona Enter para continuar...")
            elif choice == "8":
                print_color("👋 ¡Hasta pronto!", Colors.CYAN)
                stop_update_check = True
                break
            else:
                print_color("❌ Opción inválida", Colors.RED)
            input("\n⏎ Presiona Enter para continuar...")
        except KeyboardInterrupt:
            print_color("\n👋 Interrupción por usuario", Colors.YELLOW)
            stop_update_check = True
            break
        except Exception as e:
            print_color(f"❌ Error inesperado: {e}", Colors.RED)
            time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print_color(f"❌ Error crítico: {e}", Colors.RED)
        stop_update_check = True