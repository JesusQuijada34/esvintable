#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable Ultimate PRO - Multiplataforma
# Autor: @JesusQuijada34 | GitHub.com/JesusQuijada34/esvintable
# Última actualización: 2025-09-17

import os
import sys
import platform
import subprocess
import re
import time
import json
import requests
import hashlib

# ===== CONFIGURACIÓN GLOBAL =====
VERSION = "4.2"
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/esvintable.py"
SUPPORTED_AUDIO = ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg')

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

# ===== COLORES PARA TERMINAL =====
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def color(text, color_code):
    return f"{color_code}{text}{Colors.END}"

def clear():
    os.system('cls' if IS_WINDOWS else 'clear')

# ===== DEPENDENCIAS =====
def check_ffprobe():
    """Verifica si ffprobe está disponible"""
    try:
        subprocess.run(['ffprobe', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def check_ffplay():
    """Verifica si ffplay está disponible (para reproducción)"""
    try:
        subprocess.run(['ffplay', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

# ===== ACTUALIZACIÓN AUTOMÁTICA =====
def get_remote_version():
    try:
        resp = requests.get(REPO_RAW_URL, timeout=10)
        if resp.status_code == 200:
            match = re.search(r'VERSION\s*=\s*["\']([\d.]+)["\']', resp.text)
            return match.group(1) if match else None
    except Exception:
        return None

def update_script_if_needed():
    remote_version = get_remote_version()
    if not remote_version:
        print(color("⚠️  No se pudo obtener la versión remota.", Colors.RED))
        return False
    if remote_version > VERSION:
        print(color(f"🆕 Nueva versión disponible: v{remote_version}", Colors.YELLOW))
        resp = requests.get(REPO_RAW_URL, timeout=20)
        if resp.status_code == 200:
            backup_file = __file__ + ".backup"
            with open(__file__, 'r', encoding='utf-8') as f_in, open(backup_file, 'w', encoding='utf-8') as f_out:
                f_out.write(f_in.read())
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print(color("✅ Script actualizado correctamente. Reiniciando...", Colors.GREEN))
            time.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print(color("❌ Error descargando la nueva versión.", Colors.RED))
            return False
    else:
        print(color("✅ Ya tienes la última versión.", Colors.GREEN))
        return True

# ===== ESCANEO Y FILTRADO DE CANCIONES =====
def deep_scan_audio(file_path):
    """Escaneo multiplataforma y robusto de metadatos"""
    result = {'file': file_path, 'isrc': None, 'artist': None, 'album': None, 'title': None, 'duration': None, 'bitrate': None, 'tags': {}}
    # FFprobe (si está disponible)
    if check_ffprobe():
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
    # Hexadecimal (extra seguridad para ISRC)
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
    """Filtrado multiplataforma por metadatos"""
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(SUPPORTED_AUDIO):
                path = os.path.join(root, f)
                info = deep_scan_audio(path)
                match = True
                for k, v in filters.items():
                    if v and (str(info.get(k, '')).lower() if info.get(k) else '') != v.lower():
                        match = False
                        break
                if match:
                    results.append(info)
    return results

def show_song(song):
    print(color(f"Archivo: {song['file']}", Colors.BLUE))
    print(f"  Título: {song.get('title', 'Desconocido')}")
    print(f"  Artista: {song.get('artist', 'Desconocido')}")
    print(f"  Álbum: {song.get('album', 'Desconocido')}")
    print(f"  ISRC: {song.get('isrc', 'No encontrado')}")
    print(f"  Duración: {int(song['duration']) if song['duration'] else '-'} seg | Bitrate: {song.get('bitrate', '-')}\n")

def play_song(file_path):
    """Reproduce multiplataforma con ffplay si está disponible"""
    if not check_ffplay():
        print(color("⚠️  ffplay no está instalado. No se puede reproducir aquí.", Colors.RED))
        return
    print(color(f"🎧 Reproduciendo: {file_path}", Colors.GREEN))
    try:
        subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path])
    except Exception:
        print(color("❌ Error al reproducir la canción.", Colors.RED))

# ===== MENÚS INTERACTIVOS =====
def print_banner():
    banner = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                esVintable Ultimate PRO v{VERSION}                ║
║         Filtrador & Reproductor Avanzado de Canciones        ║
║           GitHub.com/JesusQuijada34/esvintable               ║
║           Plataforma detectada: {PLATFORM_LABEL:<20}         ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)

def print_guide():
    print(color("🛠️  GUÍA RÁPIDA:", Colors.YELLOW))
    print("1. Filtra canciones por nombre, artista, álbum, ISRC, duración o calidad.")
    print("2. Reproduce archivos de audio desde el menú (ffplay requerido).")
    print("3. Actualiza el script automáticamente si hay nueva versión.")
    print("4. Menú de ayuda para comandos avanzados y soporte.\n")

def main_menu():
    clear()
    print_banner()
    print_guide()
    print(color("Menú Principal:", Colors.BOLD))
    print("1. Buscar y filtrar canciones")
    print("2. Reproducir canción por ruta")
    print("3. Verificar y actualizar script")
    print("4. Ayuda")
    print("5. Salir\n")
    return input("Selecciona una opción: ").strip()

def search_menu():
    clear()
    print(color("🔎 Filtros para búsqueda avanzada:", Colors.YELLOW))
    print("Deja vacío cualquier campo para ignorarlo.")
    filters = {
        'title': input("Título: "),
        'artist': input("Artista: "),
        'album': input("Álbum: "),
        'isrc': input("ISRC: "),
    }
    directory = input("Directorio raíz de búsqueda (default: ./): ").strip() or "."
    print(color("⏳ Buscando canciones...", Colors.CYAN))
    found = filter_songs(directory, filters)
    if found:
        print(color(f"\n🎶 Se encontraron {len(found)} canciones:", Colors.GREEN))
        for i, song in enumerate(found, 1):
            print(color(f"{i}.", Colors.WHITE))
            show_song(song)
        play = input("¿Deseas reproducir alguna? Indica número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print(color("No se encontraron canciones con esos filtros.", Colors.RED))
    input("\n⏎ Enter para volver al menú...")

def help_menu():
    clear()
    print(color("🆘 AYUDA:", Colors.YELLOW))
    print("""
- Busca canciones usando filtrado por metadatos.
- Reproduce archivos con ffplay (instala ffmpeg si no lo tienes).
- El script se actualiza automáticamente desde GitHub si hay nueva versión.
- Contacto: GitHub.com/JesusQuijada34/esvintable
- Atajo: Ctrl+C para salir en cualquier momento.
""")
    input("\n⏎ Enter para volver al menú...")

# ===== MAIN LOOP =====
def main():
    # Dependencia principal: requests
    try:
        import requests
    except ImportError:
        print(color("❌ Debes instalar la librería 'requests' para usar este script.", Colors.RED))
        print("Instala con: pip install requests")
        sys.exit(1)
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
                    print(color("Archivo no encontrado.", Colors.RED))
                    time.sleep(2)
            elif choice == "3":
                update_script_if_needed()
                time.sleep(2)
            elif choice == "4":
                help_menu()
            elif choice == "5":
                print(color("👋 ¡Hasta pronto!", Colors.CYAN))
                break
            else:
                print(color("Opción inválida.", Colors.RED))
                time.sleep(2)
        except KeyboardInterrupt:
            print(color("\n👋 Interrupción por usuario", Colors.YELLOW))
            break
        except Exception as e:
            print(color(f"❌ Error inesperado: {e}", Colors.RED))
            time.sleep(2)

if __name__ == "__main__":
    main()