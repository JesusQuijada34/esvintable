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
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from threading import Thread, Event
import cloudscraper

# ===== CONFIGURACIÓN GLOBAL =====
VERSION = "4.5"
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
UPDATE_INTERVAL = 60  # Segundos entre verificaciones de actualización
CONFIG_FILE = "esvintable_config.json"

# Proveedores de música para búsqueda ISRC
PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"

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

def color(text, color_code):
    return f"{color_code}{text}{Colors.END}"

def clear():
    os.system('cls' if IS_WINDOWS else 'clear')

# ===== SISTEMA DE ACTUALIZACIÓN CON XML =====
class UpdateChecker:
    def __init__(self):
        self.last_check = datetime.now()
        self.update_available = False
        self.new_version = ""
        self.update_event = Event()
        self.running = True
        
    def get_remote_version_from_xml(self):
        """Obtiene la versión desde el archivo XML"""
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                version_element = root.find('version')
                if version_element is not None:
                    return version_element.text.strip()
        except Exception as e:
            print(color(f"❌ Error leyendo XML: {e}", Colors.RED))
        return None
    
    def compare_versions(self, local_ver, remote_ver):
        """Compara versiones en formato vX-XX.XX-XX.XX-XXXXXXX"""
        try:
            # Extraer partes numéricas de las versiones
            local_parts = re.findall(r'\d+', local_ver)
            remote_parts = re.findall(r'\d+', remote_ver)
            
            # Comparar cada parte numérica
            for i in range(min(len(local_parts), len(remote_parts))):
                if int(remote_parts[i]) > int(local_parts[i]):
                    return True
                elif int(remote_parts[i]) < int(local_parts[i]):
                    return False
            # Si todas las partes son iguales, la más larga es más nueva
            return len(remote_parts) > len(local_parts)
        except:
            return remote_ver > local_ver
    
    def check_for_updates(self):
        """Verifica si hay actualizaciones disponibles"""
        try:
            remote_version = self.get_remote_version_from_xml()
            if remote_version and self.compare_versions(VERSION, remote_version):
                self.update_available = True
                self.new_version = remote_version
                return True
        except Exception as e:
            print(color(f"❌ Error verificando actualizaciones: {e}", Colors.RED))
        return False
    
    def download_update(self):
        """Descarga la actualización desde el repo"""
        try:
            script_url = f"{REPO_RAW_URL}{SCRIPT_FILENAME}"
            response = requests.get(script_url, timeout=20)
            
            if response.status_code == 200:
                # Crear backup
                backup_file = f"{__file__}.backup"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    with open(__file__, 'r', encoding='utf-8') as original:
                        f.write(original.read())
                
                # Escribir nueva versión
                with open(__file__, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                return True
        except Exception as e:
            print(color(f"❌ Error descargando actualización: {e}", Colors.RED))
        return False
    
    def start_update_checker(self):
        """Inicia el verificador de actualizaciones en segundo plano"""
        def checker_thread():
            while self.running:
                try:
                    current_time = datetime.now()
                    if (current_time - self.last_check).total_seconds() >= UPDATE_INTERVAL:
                        if self.check_for_updates():
                            print(color(f"\n🎉 ¡Nueva versión disponible! v{VERSION} → v{self.new_version}", Colors.GREEN))
                        self.last_check = current_time
                    time.sleep(10)  # Verificar cada 10 segundos
                except Exception:
                    time.sleep(30)  # Esperar más en caso de error
        
        Thread(target=checker_thread, daemon=True).start()
    
    def stop_update_checker(self):
        """Detiene el verificador de actualizaciones"""
        self.running = False

# Instancia global del verificador de actualizaciones
updater = UpdateChecker()

# ===== DEPENDENCIAS =====
def check_dependencies():
    """Verifica e instala dependencias automáticamente"""
    missing_deps = []
    
    for dep in ["requests", "cloudscraper"]:
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)
    
    if missing_deps:
        print(color("⚠️  Instalando dependencias faltantes...", Colors.YELLOW))
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing_deps, 
                         check=True, capture_output=True, timeout=300)
            print(color("✅ Dependencias instaladas correctamente", Colors.GREEN))
            return True
        except subprocess.TimeoutExpired:
            print(color("❌ Tiempo de espera agotado instalando dependencias", Colors.RED))
            return False
        except:
            print_color("❌ Error instalando dependencias", Colors.RED)
            return False
    
    return True

def check_ffprobe():
    """Verifica si ffprobe está disponible"""
    try:
        subprocess.run(['ffprobe', '-version'], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return True
    except Exception:
        return False

def check_ffplay():
    """Verifica si ffplay está disponible (para reproducción)"""
    try:
        subprocess.run(['ffplay', '-version'], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return True
    except Exception:
        return False

def install_ffmpeg_tools():
    """Instala ffmpeg/ffprobe/ffplay según la plataforma"""
    print(color("🔧 Instalando herramientas FFmpeg...", Colors.YELLOW))
    
    try:
        if IS_TERMUX or IS_PYDROID:
            subprocess.run(['pkg', 'install', 'ffmpeg', '-y'], 
                          check=True, capture_output=True, timeout=300)
        elif IS_LINUX:
            if subprocess.run(['which', 'apt-get'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'apt-get', 'install', 'ffmpeg', '-y'], 
                              check=True, timeout=300)
            elif subprocess.run(['which', 'yum'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'yum', 'install', 'ffmpeg', '-y'], 
                              check=True, timeout=300)
        elif IS_MAC:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True, timeout=300)
        elif IS_WINDOWS:
            print(color("📥 Descarga FFmpeg para Windows desde: https://ffmpeg.org/download.html", Colors.YELLOW))
            return False
        
        print(color("✅ Herramientas FFmpeg instaladas correctamente", Colors.GREEN))
        return True
    except subprocess.TimeoutExpired:
        print(color("❌ Tiempo de espera agotado instalando FFmpeg", Colors.RED))
        return False
    except:
        print(color("❌ Error instalando FFmpeg", Colors.RED))
        return False

# ===== ESCANEO PROFUNDO DE AUDIO =====
def deep_scan_audio(file_path):
    """Escaneo multiplataforma y robusto de metadatos"""
    result = {
        'file': file_path, 
        'isrc': None, 
        'artist': None, 
        'album': None, 
        'title': None, 
        'duration': None, 
        'bitrate': None,
        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        'tags': {}
    }
    
    # Método 1: FFprobe (metadatos estándar)
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
                result['isrc'] = tags.get('ISRC') or tags.get('TSRC') or tags.get('isrc')
                result['title'] = tags.get('title') or tags.get('TITLE')
                result['artist'] = tags.get('artist') or tags.get('ARTIST') or tags.get('composer')
                result['album'] = tags.get('album') or tags.get('ALBUM')
                result['duration'] = float(info['format'].get('duration', 0))
                result['bitrate'] = int(info['format'].get('bit_rate', 0)) // 1000 if info['format'].get('bit_rate') else None
        except Exception:
            pass
    
    # Método 2: Análisis hexadecimal (búsqueda profunda de ISRC)
    try:
        with open(file_path, 'rb') as f:
            content = f.read(1000000)  # Leer primeros MB
            
            # Patrones comunes de ISRC
            patterns = [
                br'ISRC[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
                br'isrc[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    found_isrc = match.group(1)
                    if isinstance(found_isrc, bytes):
                        found_isrc = found_isrc.decode('utf-8', errors='ignore')
                    # Validar formato ISRC
                    if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found_isrc):
                        result['isrc'] = found_isrc
                        break
    except Exception:
        pass
    
    return result

# ===== BÚSQUEDA Y DESCARGA POR ISRC =====
def download_by_isrc(isrc, output_dir="descargas_isrc"):
    """Descarga una canción por su código ISRC"""
    scraper = cloudscraper.create_scraper()
    
    print(color(f"🔍 Buscando ISRC: {isrc}", Colors.CYAN))
    
    for provider in PROVIDERS:
        try:
            url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            
            print(color(f"   Probando {provider}...", Colors.YELLOW))
            response = scraper.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.join(output_dir, f"{isrc}.m4a")
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print(color(f"✅ Descargado: {filename}", Colors.GREEN))
                return True, filename
                
        except Exception as e:
            continue
    
    return False, None

def search_isrc_in_directory(directory, isrc_code):
    """Busca un ISRC específico en todos los archivos de un directorio"""
    print(color(f"🔍 Buscando ISRC {isrc_code} en {directory}", Colors.CYAN))
    
    found_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                file_path = os.path.join(root, file)
                audio_info = deep_scan_audio(file_path)
                if audio_info['isrc'] and audio_info['isrc'].upper() == isrc_code.upper():
                    found_files.append(audio_info)
    
    return found_files

# ===== BÚSQUEDA EN SERVICIOS EXTERNOS =====
def search_spotify(query, search_type="track"):
    """Busca en Spotify (requiere API key)"""
    print(color("🎵 Buscando en Spotify...", Colors.CYAN))
    # Aquí iría la implementación real con la API de Spotify
    print(color("⚠️  Integración con Spotify requiere configuración de API", Colors.YELLOW))
    return []

def search_external_services(query, service="all"):
    """Busca en múltiples servicios de música"""
    results = {}
    
    if service in ["all", "spotify"]:
        results['spotify'] = search_spotify(query)
    
    # Se pueden agregar más servicios aquí: Apple Music, YouTube Music, etc.
    
    return results

# ===== FILTRADO DE CANCIONES =====
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
                    if v and (str(info.get(k, '')).lower() != v.lower()):
                        match = False
                        break
                if match:
                    results.append(info)
    return results

def show_song(song):
    print(color(f"📁 Archivo: {song['file']}", Colors.BLUE))
    print(f"   🎵 Título: {song.get('title', 'Desconocido')}")
    print(f"   🎤 Artista: {song.get('artist', 'Desconocido')}")
    print(f"   💿 Álbum: {song.get('album', 'Desconocido')}")
    print(f"   🏷️  ISRC: {song.get('isrc', 'No encontrado')}")
    print(f"   ⏱️  Duración: {int(song['duration']) if song['duration'] else '-'}s")
    print(f"   📊 Bitrate: {song.get('bitrate', '-')} kbps")
    print(f"   📦 Tamaño: {song['size'] // 1024} KB\n")

# ===== REPRODUCCIÓN =====
def play_song(file_path):
    """Reproduce multiplataforma con ffplay si está disponible"""
    if not check_ffplay():
        print(color("⚠️  ffplay no está instalado.", Colors.RED))
        install = input("¿Instalar FFmpeg? (s/n): ").lower()
        if install == 's':
            if install_ffmpeg_tools():
                return play_song(file_path)
        return
    
    print(color(f"🎧 Reproduciendo: {os.path.basename(file_path)}", Colors.GREEN))
    try:
        if IS_WINDOWS:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path])
        else:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path])
    except Exception:
        print(color("❌ Error al reproducir la canción.", Colors.RED))

# ===== INTERFAZ DE USUARIO =====
def print_banner():
    banner = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                esVintable Ultimate PRO v{VERSION}                ║
║         Búsqueda Avanzada & Descarga por ISRC                ║
║           GitHub.com/JesusQuijada34/esvintable               ║
║           Plataforma: {PLATFORM_LABEL:<20}                   ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)
    
    # Mostrar estado de actualizaciones
    if updater.update_available:
        print(color(f"🔄 Actualización disponible: v{updater.new_version}", Colors.GREEN))

def print_guide():
    print(color("🛠️  GUÍA RÁPIDA:", Colors.YELLOW))
    print("1. Buscar canciones por metadatos (título, artista, álbum, ISRC)")
    print("2. Buscar ISRC específico en directorios")
    print("3. Descargar canciones por código ISRC")
    print("4. Reproducir archivos de audio")
    print("5. Actualizaciones automáticas desde GitHub")
    print("6. Búsqueda en servicios externos (Spotify, etc.)\n")

def main_menu():
    clear()
    print_banner()
    print_guide()
    print(color("Menú Principal:", Colors.BOLD))
    print("1. 🔍 Buscar canciones por metadatos")
    print("2. 🏷️  Buscar por ISRC específico")
    print("3. 📥 Descargar por ISRC")
    print("4. 🎧 Reproducir canción")
    print("5. 🌐 Buscar en servicios externos")
    print("6. 🔄 Verificar actualizaciones")
    print("7. ⚙️  Instalar herramientas")
    print("8. ❌ Salir\n")
    return input("Selecciona una opción: ").strip()

def search_by_metadata_menu():
    clear()
    print(color("🔎 Búsqueda por Metadatos", Colors.BOLD))
    print("Deja vacío cualquier campo para ignorarlo.")
    
    filters = {
        'title': input("Título: ").strip(),
        'artist': input("Artista: ").strip(),
        'album': input("Álbum: ").strip(),
        'isrc': input("ISRC: ").strip(),
    }
    
    directory = input("Directorio a buscar (default: ./): ").strip() or "."
    
    if not os.path.isdir(directory):
        print(color("❌ El directorio no existe.", Colors.RED))
        time.sleep(2)
        return
    
    print(color("⏳ Buscando canciones...", Colors.CYAN))
    found = filter_songs(directory, filters)
    
    if found:
        print(color(f"\n🎶 Se encontraron {len(found)} canciones:", Colors.GREEN))
        for i, song in enumerate(found, 1):
            print(color(f"{i}.", Colors.WHITE))
            show_song(song)
        
        # Opción para reproducir
        play = input("¿Reproducir alguna? Número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print(color("❌ No se encontraron canciones con esos filtros.", Colors.RED))
    
    input("\n⏎ Enter para continuar...")

def search_by_isrc_menu():
    clear()
    print(color("🏷️ Búsqueda por ISRC", Colors.BOLD))
    
    isrc_code = input("Introduce el código ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
        print(color("❌ Formato ISRC inválido.", Colors.RED))
        time.sleep(2)
        return
    
    directory = input("Directorio a buscar (default: ./): ").strip() or "."
    
    if not os.path.isdir(directory):
        print(color("❌ El directorio no existe.", Colors.RED))
        time.sleep(2)
        return
    
    print(color("⏳ Buscando ISRC...", Colors.CYAN))
    found = search_isrc_in_directory(directory, isrc_code)
    
    if found:
        print(color(f"\n✅ Se encontraron {len(found)} archivos con ISRC {isrc_code}:", Colors.GREEN))
        for i, song in enumerate(found, 1):
            print(color(f"{i}.", Colors.WHITE))
            show_song(song)
        
        # Opción para reproducir
        play = input("¿Reproducir alguna? Número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print(color(f"❌ No se encontraron archivos con ISRC {isrc_code}", Colors.RED))
    
    input("\n⏎ Enter para continuar...")

def download_by_isrc_menu():
    clear()
    print(color("📥 Descargar por ISRC", Colors.BOLD))
    
    isrc_code = input("Introduce el código ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
        print(color("❌ Formato ISRC inválido.", Colors.RED))
        time.sleep(2)
        return
    
    output_dir = input("Directorio de descarga (default: descargas_isrc): ").strip() or "descargas_isrc"
    
    success, filename = download_by_isrc(isrc_code, output_dir)
    if success:
        print(color(f"✅ Descarga completada: {filename}", Colors.GREEN))
        
        # Preguntar si reproducir
        play = input("¿Reproducir descarga? (s/n): ").lower()
        if play == 's':
            play_song(filename)
    else:
        print(color("❌ No se pudo descargar el archivo.", Colors.RED))
    
    input("\n⏎ Enter para continuar...")

def play_song_menu():
    clear()
    print(color("🎧 Reproducir Canción", Colors.BOLD))
    
    path = input("Ruta del archivo de audio: ").strip()
    if not os.path.isfile(path):
        print(color("❌ Archivo no encontrado.", Colors.RED))
        time.sleep(2)
        return
    
    if not path.lower().endswith(SUPPORTED_AUDIO):
        print(color("❌ Formato de audio no soportado.", Colors.RED))
        time.sleep(2)
        return
    
    play_song(path)
    input("\n⏎ Enter para continuar...")

def external_search_menu():
    clear()
    print(color("🌐 Búsqueda en Servicios Externos", Colors.BOLD))
    
    query = input("Término de búsqueda: ").strip()
    if not query:
        print(color("❌ Debes introducir un término de búsqueda.", Colors.RED))
        time.sleep(2)
        return
    
    service = input("Servicio (spotify/all): ").strip().lower() or "all"
    
    results = search_external_services(query, service)
    
    if results.get('spotify'):
        print(color(f"🎵 Resultados de Spotify ({len(results['spotify'])}):", Colors.GREEN))
        for i, result in enumerate(results['spotify'][:5], 1):
            print(f"   {i}. {result}")
    else:
        print(color("❌ No se encontraron resultados.", Colors.RED))
    
    input("\n⏎ Enter para continuar...")

def update_menu():
    clear()
    print(color("🔄 Sistema de Actualización", Colors.BOLD))
    
    if updater.update_available:
        print(color(f"🎉 ¡Actualización disponible! v{VERSION} → v{updater.new_version}", Colors.GREEN))
        
        update = input("¿Actualizar ahora? (s/n): ").lower()
        if update == 's':
            if updater.download_update():
                print(color("✅ Actualización completada. Reiniciando...", Colors.GREEN))
                time.sleep(2)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print(color("❌ Error durante la actualización.", Colors.RED))
    else:
        print(color("🔍 Verificando actualizaciones...", Colors.CYAN))
        if updater.check_for_updates():
            print(color(f"🎉 ¡Nueva versión encontrada! v{updater.new_version}", Colors.GREEN))
        else:
            print(color("✅ Ya tienes la versión más reciente.", Colors.GREEN))
    
    input("\n⏎ Enter para continuar...")

def tools_menu():
    clear()
    print(color("⚙️  Herramientas y Utilidades", Colors.BOLD))
    
    print("1. Instalar FFmpeg/FFprobe/FFplay")
    print("2. Verificar dependencias")
    print("3. Volver al menú principal")
    
    choice = input("Selecciona opción: ").strip()
    
    if choice == "1":
        if install_ffmpeg_tools():
            print(color("✅ Herramientas instaladas correctamente.", Colors.GREEN))
        else:
            print(color("❌ Error instalando herramientas.", Colors.RED))
    elif choice == "2":
        if check_dependencies():
            print(color("✅ Dependencias verificadas correctamente.", Colors.GREEN))
        else:
            print(color("❌ Error con las dependencias.", Colors.RED))
    
    input("\n⏎ Enter para continuar...")

# ===== FUNCIÓN PRINCIPAL =====
def main():
    # Verificar dependencias
    if not check_dependencies():
        print(color("❌ Error con las dependencias. Saliendo...", Colors.RED))
        sys.exit(1)
    
    # Iniciar verificador de actualizaciones
    updater.start_update_checker()
    
    # Verificar herramientas FFmpeg
    if not check_ffprobe() or not check_ffplay():
        print(color("⚠️  Herramientas FFmpeg no detectadas.", Colors.YELLOW))
        print(color("   Algunas funciones estarán limitadas.", Colors.YELLOW))
        time.sleep(2)
    
    # Bucle principal
    while True:
        try:
            choice = main_menu()
            
            if choice == "1":
                search_by_metadata_menu()
            elif choice == "2":
                search_by_isrc_menu()
            elif choice == "3":
                download_by_isrc_menu()
            elif choice == "4":
                play_song_menu()
            elif choice == "5":
                external_search_menu()
            elif choice == "6":
                update_menu()
            elif choice == "7":
                tools_menu()
            elif choice == "8":
                print(color("👋 ¡Hasta pronto!", Colors.CYAN))
                updater.stop_update_checker()
                break
            else:
                print(color("❌ Opción inválida.", Colors.RED))
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(color("\n👋 Interrupción por usuario", Colors.YELLOW))
            updater.stop_update_checker()
            break
        except Exception as e:
            print(color(f"❌ Error inesperado: {e}", Colors.RED))
            time.sleep(2)

if __name__ == "__main__":
    main()