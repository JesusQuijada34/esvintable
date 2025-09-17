#!/usr/bin/env python3
#Mejorable
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
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ===== CONFIGURACIÓN GLOBAL =====
VERSION = "5.0"
REPO_URL = "https://github.com/JesusQuijada34/esvintable"
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
DETAILS_XML_URL = REPO_RAW_URL + "details.xml"
UPDATE_CHECK_INTERVAL = 60  # segundos
LAST_UPDATE_CHECK = 0
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

# ===== CONFIGURACIÓN DE API =====
SPOTIFY_CLIENT_ID = None
SPOTIFY_CLIENT_SECRET = None
SPOTIFY_ACCESS_TOKEN = None
SPOTIFY_TOKEN_EXPIRE = 0

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

# ===== GESTIÓN DE ACTUALIZACIONES =====
def get_remote_version_from_xml():
    """Obtiene la versión remota desde el archivo XML"""
    try:
        response = requests.get(DETAILS_XML_URL, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            version_element = root.find('version')
            if version_element is not None:
                return version_element.text
    except Exception as e:
        print(color(f"Error al obtener versión desde XML: {e}", Colors.RED))
    return None

def check_for_updates(force=False):
    """Verifica si hay actualizaciones disponibles"""
    global LAST_UPDATE_CHECK
    
    current_time = time.time()
    if not force and current_time - LAST_UPDATE_CHECK < UPDATE_CHECK_INTERVAL:
        return None
    
    LAST_UPDATE_CHECK = current_time
    print(color("🔍 Buscando actualizaciones...", Colors.CYAN))
    
    remote_version = get_remote_version_from_xml()
    if not remote_version:
        print(color("⚠️ No se pudo obtener la versión remota.", Colors.YELLOW))
        return None
    
    # Comparar versiones
    if remote_version != VERSION:
        print(color(f"🆕 Nueva versión disponible: {remote_version}", Colors.YELLOW))
        return remote_version
    else:
        print(color("✅ Ya tienes la última versión.", Colors.GREEN))
        return None

def update_script():
    """Actualiza el script desde el repositorio"""
    try:
        script_url = REPO_RAW_URL + "esvintable.py"
        response = requests.get(script_url, timeout=20)
        if response.status_code == 200:
            # Crear backup
            backup_file = __file__ + ".backup"
            with open(__file__, 'r', encoding='utf-8') as f_in, open(backup_file, 'w', encoding='utf-8') as f_out:
                f_out.write(f_in.read())
            
            # Escribir nueva versión
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(color("✅ Script actualizado correctamente. Reiniciando...", Colors.GREEN))
            time.sleep(2)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print(color("❌ Error descargando la nueva versión.", Colors.RED))
    except Exception as e:
        print(color(f"❌ Error durante la actualización: {e}", Colors.RED))

# ===== GESTIÓN DE API DE SPOTIFY =====
def setup_spotify_api():
    """Configura las credenciales de la API de Spotify"""
    global SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    
    print(color("🔧 Configuración de API de Spotify", Colors.YELLOW))
    print("Necesitas obtener Client ID y Client Secret desde https://developer.spotify.com/dashboard")
    
    if not SPOTIFY_CLIENT_ID:
        SPOTIFY_CLIENT_ID = input("Introduce tu Spotify Client ID: ").strip()
    
    if not SPOTIFY_CLIENT_SECRET:
        SPOTIFY_CLIENT_SECRET = input("Introduce tu Spotify Client Secret: ").strip()
    
    # Guardar configuración
    config = {
        'spotify_client_id': SPOTIFY_CLIENT_ID,
        'spotify_client_secret': SPOTIFY_CLIENT_SECRET
    }
    
    with open('esvintable_config.json', 'w') as f:
        json.dump(config, f)
    
    print(color("✅ Configuración de Spotify guardada.", Colors.GREEN))
    return get_spotify_token()

def get_spotify_token():
    """Obtiene token de acceso de Spotify"""
    global SPOTIFY_ACCESS_TOKEN, SPOTIFY_TOKEN_EXPIRE
    
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return False
    
    # Verificar si el token actual sigue siendo válido
    if SPOTIFY_ACCESS_TOKEN and time.time() < SPOTIFY_TOKEN_EXPIRE:
        return True
    
    try:
        auth_url = 'https://accounts.spotify.com/api/token'
        auth_response = requests.post(auth_url, {
            'grant_type': 'client_credentials',
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }, timeout=10)
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            SPOTIFY_ACCESS_TOKEN = auth_data['access_token']
            SPOTIFY_TOKEN_EXPIRE = time.time() + auth_data['expires_in'] - 60  # Margen de 60 segundos
            return True
        else:
            print(color("❌ Error al obtener token de Spotify. Verifica tus credenciales.", Colors.RED))
            return False
    except Exception as e:
        print(color(f"❌ Error de conexión con Spotify: {e}", Colors.RED))
        return False

def search_spotify(isrc=None, title=None, artist=None):
    """Busca canciones en Spotify por ISRC, título o artista"""
    if not get_spotify_token():
        if not setup_spotify_api():
            return None
    
    try:
        headers = {'Authorization': f'Bearer {SPOTIFY_ACCESS_TOKEN}'}
        query_parts = []
        
        if isrc:
            query_parts.append(f'isrc:{isrc}')
        if title:
            query_parts.append(f'track:"{title}"')
        if artist:
            query_parts.append(f'artist:"{artist}"')
        
        query = ' '.join(query_parts)
        search_url = f'https://api.spotify.com/v1/search?q={query}&type=track&limit=10'
        
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(color(f"❌ Error en búsqueda de Spotify: {response.status_code}", Colors.RED))
            return None
    except Exception as e:
        print(color(f"❌ Error al buscar en Spotify: {e}", Colors.RED))
        return None

def show_spotify_results(spotify_data):
    """Muestra los resultados de búsqueda de Spotify"""
    if not spotify_data or 'tracks' not in spotify_data or 'items' not in spotify_data['tracks']:
        print(color("No se encontraron resultados en Spotify.", Colors.YELLOW))
        return
    
    tracks = spotify_data['tracks']['items']
    print(color(f"🎵 Resultados en Spotify ({len(tracks)} encontrados):", Colors.GREEN))
    
    for i, track in enumerate(tracks, 1):
        print(f"{i}. {track['name']} - {', '.join([a['name'] for a in track['artists']])}")
        print(f"   Álbum: {track['album']['name']}")
        print(f"   ISRC: {track.get('external_ids', {}).get('isrc', 'No disponible')}")
        print(f"   Duración: {timedelta(seconds=track['duration_ms']//1000)}")
        print(f"   Enlace: {track['external_urls']['spotify']}\n")

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
    
    # Búsqueda hexadecimal profunda de ISRC
    if not result['isrc']:
        try:
            with open(file_path, 'rb') as f:
                # Leer en bloques para archivos grandes
                chunk_size = 8192
                max_chunks = 100  # Limitar a ~800KB para no sobrecargar
                
                for i in range(max_chunks):
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Buscar patrones ISRC
                    patterns = [
                        br'ISRC[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                        br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
                        br'isrc[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, chunk, re.IGNORECASE)
                        if match:
                            found_isrc = match.group(1).decode('utf-8', errors='ignore') if isinstance(match.group(1), bytes) else match.group(1)
                            if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found_isrc):
                                result['isrc'] = found_isrc
                                break
                    
                    if result['isrc']:
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
                    if v and k in info and info[k]:
                        # Búsqueda parcial para texto, exacta para ISRC
                        if k == 'isrc':
                            if str(info[k]).lower() != v.lower():
                                match = False
                                break
                        else:
                            if v.lower() not in str(info[k]).lower():
                                match = False
                                break
                
                if match:
                    results.append(info)
    
    return results

def show_song(song, index=None):
    if index is not None:
        print(color(f"{index}.", Colors.WHITE), end=" ")
    print(color(f"Archivo: {song['file']}", Colors.BLUE))
    print(f"  Título: {song.get('title', 'Desconocido')}")
    print(f"  Artista: {song.get('artist', 'Desconocido')}")
    print(f"  Álbum: {song.get('album', 'Desconocido')}")
    print(f"  ISRC: {song.get('isrc', 'No encontrado')}")
    print(f"  Duración: {int(song['duration']) if song['duration'] else '-'} seg | Bitrate: {song.get('bitrate', '-')} kbps\n")

def play_song(file_path):
    """Reproduce multiplataforma con ffplay si está disponible"""
    if not check_ffplay():
        print(color("⚠️  ffplay no está instalado. No se puede reproducir aquí.", Colors.RED))
        return
    
    print(color(f"🎧 Reproduciendo: {file_path}", Colors.GREEN))
    try:
        if IS_WINDOWS:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path])
    except Exception as e:
        print(color(f"❌ Error al reproducir la canción: {e}", Colors.RED))

# ===== BÚSQUEDA POR ISRC =====
def search_by_isrc():
    """Búsqueda especializada por código ISRC"""
    clear()
    print(color("🔍 BÚSQUEDA POR CÓDIGO ISRC", Colors.CYAN))
    print("=" * 50)
    
    isrc_code = input("Introduce el código ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
        print(color("❌ Formato de ISRC inválido. Debe ser: AABBB1234567", Colors.RED))
        time.sleep(2)
        return
    
    directory = input("Directorio raíz de búsqueda (default: ./): ").strip() or "."
    
    print(color("⏳ Buscando canciones con ISRC...", Colors.CYAN))
    found = filter_songs(directory, {'isrc': isrc_code})
    
    if found:
        print(color(f"\n🎶 Se encontraron {len(found)} canciones con ISRC {isrc_code}:", Colors.GREEN))
        for i, song in enumerate(found, 1):
            show_song(song, i)
        
        # Buscar en Spotify
        print(color("🌐 Buscando información online...", Colors.CYAN))
        spotify_results = search_spotify(isrc=isrc_code)
        if spotify_results:
            show_spotify_results(spotify_results)
        
        # Opciones de reproducción
        play = input("¿Deseas reproducir alguna? Indica número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print(color(f"No se encontraron canciones con ISRC {isrc_code}.", Colors.RED))
        
        # Buscar en Spotify aunque no se encontró localmente
        print(color("🌐 Buscando información online...", Colors.CYAN))
        spotify_results = search_spotify(isrc=isrc_code)
        if spotify_results:
            show_spotify_results(spotify_results)
    
    input("\n⏎ Enter para volver al menú...")

# ===== BÚSQUEDA EN SPOTIFY =====
def search_online():
    """Búsqueda online de canciones"""
    clear()
    print(color("🌐 BÚSQUEDA ONLINE", Colors.CYAN))
    print("=" * 50)
    
    title = input("Título de la canción (opcional): ").strip()
    artist = input("Artista (opcional): ").strip()
    isrc = input("ISRC (opcional): ").strip().upper()
    
    if not any([title, artist, isrc]):
        print(color("❌ Debes introducir al menos un criterio de búsqueda.", Colors.RED))
        time.sleep(2)
        return
    
    print(color("⏳ Buscando en Spotify...", Colors.CYAN))
    spotify_results = search_spotify(isrc=isrc, title=title, artist=artist)
    
    if spotify_results:
        show_spotify_results(spotify_results)
        
        # Preguntar si quiere buscar localmente
        local_search = input("¿Deseas buscar estas canciones localmente? (s/N): ").strip().lower()
        if local_search == 's':
            directory = input("Directorio raíz de búsqueda (default: ./): ").strip() or "."
            filters = {}
            
            if isrc:
                filters['isrc'] = isrc
            if title:
                filters['title'] = title
            if artist:
                filters['artist'] = artist
            
            print(color("⏳ Buscando canciones locales...", Colors.CYAN))
            found = filter_songs(directory, filters)
            
            if found:
                print(color(f"\n🎶 Se encontraron {len(found)} canciones locales:", Colors.GREEN))
                for i, song in enumerate(found, 1):
                    show_song(song, i)
                
                play = input("¿Deseas reproducir alguna? Indica número o Enter para omitir: ").strip()
                if play.isdigit() and 1 <= int(play) <= len(found):
                    play_song(found[int(play)-1]['file'])
            else:
                print(color("No se encontraron canciones locales con esos filtros.", Colors.RED))
    else:
        print(color("No se encontraron resultados online.", Colors.YELLOW))
    
    input("\n⏎ Enter para volver al menú...")

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
    print("2. Búsqueda especializada por código ISRC.")
    print("3. Búsqueda online en Spotify y otras plataformas.")
    print("4. Reproduce archivos de audio desde el menú (ffplay requerido).")
    print("5. Actualiza el script automáticamente si hay nueva versión.")
    print("6. Menú de ayuda para comandos avanzados y soporte.\n")

def main_menu():
    clear()
    print_banner()
    print_guide()
    print(color("Menú Principal:", Colors.BOLD))
    print("1. Buscar y filtrar canciones")
    print("2. Búsqueda por ISRC")
    print("3. Búsqueda online (Spotify)")
    print("4. Reproducir canción por ruta")
    print("5. Configurar API de Spotify")
    print("6. Verificar y actualizar script")
    print("7. Ayuda")
    print("8. Salir\n")
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
            show_song(song, i)
        
        # Buscar en Spotify si hay ISRC
        has_isrc = any(song.get('isrc') for song in found)
        if has_isrc:
            online = input("¿Deseas buscar información online? (s/N): ").strip().lower()
            if online == 's':
                for song in found:
                    if song.get('isrc'):
                        print(color(f"🌐 Buscando información para ISRC: {song['isrc']}", Colors.CYAN))
                        spotify_results = search_spotify(isrc=song['isrc'])
                        if spotify_results:
                            show_spotify_results(spotify_results)
        
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
- Búsqueda especializada por código ISRC.
- Integración con Spotify API para búsquedas online.
- Reproduce archivos con ffplay (instala ffmpeg si no lo tienes).
- El script se actualiza automáticamente desde GitHub si hay nueva versión.
- Configura tus credenciales de Spotify API para búsquedas online.
- Contacto: GitHub.com/JesusQuijada34/esvintable
- Atajo: Ctrl+C para salir en cualquier momento.

📋 FORMATO ISRC:
El código ISRC (International Standard Recording Code) tiene el formato:
- 2 caracteres de país (ej: ES)
- 3 caracteres alfanuméricos del registrante
- 2 dígitos del año
- 5 dígitos de secuencia
Ejemplo: USRC17607839

🔧 CONFIGURACIÓN SPOTIFY:
1. Ve a https://developer.spotify.com/dashboard
2. Inicia sesión o crea una cuenta
3. Crea una nueva app
4. Obtén tu Client ID y Client Secret
5. Configúralos en el menú principal
""")
    input("\n⏎ Enter para volver al menú...")

# ===== CARGA DE CONFIGURACIÓN =====
def load_config():
    """Carga la configuración guardada"""
    global SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
    
    try:
        if os.path.exists('esvintable_config.json'):
            with open('esvintable_config.json', 'r') as f:
                config = json.load(f)
                SPOTIFY_CLIENT_ID = config.get('spotify_client_id')
                SPOTIFY_CLIENT_SECRET = config.get('spotify_client_secret')
                return True
    except Exception:
        pass
    
    return False

# ===== MAIN LOOP =====
def main():
    # Verificar dependencias
    try:
        import requests
    except ImportError:
        print(color("❌ Debes instalar la librería 'requests' para usar este script.", Colors.RED))
        print("Instala con: pip install requests")
        sys.exit(1)
    
    # Cargar configuración
    load_config()
    
    # Verificar actualizaciones al inicio
    check_for_updates(force=True)
    
    while True:
        try:
            choice = main_menu()
            if choice == "1":
                search_menu()
            elif choice == "2":
                search_by_isrc()
            elif choice == "3":
                search_online()
            elif choice == "4":
                path = input("Ruta del archivo de audio: ").strip()
                if os.path.isfile(path):
                    play_song(path)
                else:
                    print(color("Archivo no encontrado.", Colors.RED))
                    time.sleep(2)
            elif choice == "5":
                setup_spotify_api()
            elif choice == "6":
                new_version = check_for_updates(force=True)
                if new_version:
                    update = input(f"¿Deseas actualizar a la versión {new_version}? (s/N): ").strip().lower()
                    if update == 's':
                        update_script()
                time.sleep(2)
            elif choice == "7":
                help_menu()
            elif choice == "8":
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