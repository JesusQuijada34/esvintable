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
# Versión inicial - será actualizada desde XML
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
    # Colores adicionales para mejor experiencia
    ORANGE = '\033[38;5;208m'
    PURPLE = '\033[38;5;129m'
    PINK = '\033[38;5;199m'
    LIGHT_BLUE = '\033[38;5;45m'

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
        self.remote_version = None
        self.update_info = {}
        
    def get_remote_info_from_xml(self):
        """Obtiene información completa desde el archivo XML"""
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                # Extraer información del XML
                info = {}
                info['version'] = root.find('version').text.strip() if root.find('version') is not None else VERSION
                info['changelog'] = root.find('changelog').text.strip() if root.find('changelog') is not None else ""
                info['release_date'] = root.find('release_date').text.strip() if root.find('release_date') is not None else ""
                info['critical'] = root.find('critical').text.strip().lower() == 'true' if root.find('critical') is not None else False
                
                return info
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
            self.update_info = self.get_remote_info_from_xml()
            if self.update_info and 'version' in self.update_info:
                self.remote_version = self.update_info['version']
                if self.compare_versions(VERSION, self.remote_version):
                    self.update_available = True
                    self.new_version = self.remote_version
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
                            if self.update_info.get('critical', False):
                                print(color("🚨 ACTUALIZACIÓN CRÍTICA: Se recomienda actualizar inmediatamente", Colors.RED))
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
            print(color("❌ Error instalando dependencias", Colors.RED))
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

# ===== NAVEGADOR DE ARCHIVOS =====
def file_browser(start_path="."):
    """Navegador interactivo de archivos"""
    current_path = os.path.abspath(start_path)
    
    while True:
        clear()
        print(color(f"📁 Navegando: {current_path}", Colors.BLUE))
        print(color("=" * 60, Colors.CYAN))
        
        # Obtener contenido del directorio
        try:
            items = os.listdir(current_path)
        except PermissionError:
            print(color("❌ Permiso denegado para acceder a este directorio", Colors.RED))
            time.sleep(2)
            return None
        
        directories = []
        files = []
        audio_files = []
        
        for item in items:
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                directories.append(item)
            elif os.path.isfile(item_path):
                files.append(item)
                if item.lower().endswith(SUPPORTED_AUDIO):
                    audio_files.append(item)
        
        # Mostrar directorios
        print(color("\n📂 DIRECTORIOS:", Colors.BOLD))
        for i, dir_name in enumerate(directories, 1):
            print(color(f"  {i:2d}. {dir_name}/", Colors.BLUE))
        
        # Mostrar archivos de audio
        print(color("\n🎵 ARCHIVOS DE AUDIO:", Colors.BOLD))
        for i, file_name in enumerate(audio_files, 1):
            print(color(f"  {i + len(directories):2d}. {file_name}", Colors.GREEN))
        
        # Mostrar otros archivos
        other_files = [f for f in files if not f.lower().endswith(SUPPORTED_AUDIO)]
        if other_files:
            print(color("\n📄 OTROS ARCHIVOS:", Colors.BOLD))
            for i, file_name in enumerate(other_files, 1 + len(directories) + len(audio_files)):
                print(color(f"  {i:2d}. {file_name}", Colors.WHITE))
        
        print(color("\n" + "=" * 60, Colors.CYAN))
        print("0. Volver al directorio anterior")
        print("00. Seleccionar este directorio para buscar")
        print("000. Seleccionar archivo de audio para analizar")
        print("0000. Volver al menú principal")
        
        try:
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == "0":
                # Volver al directorio anterior
                current_path = os.path.dirname(current_path)
            elif choice == "00":
                # Seleccionar este directorio para buscar
                return current_path
            elif choice == "000":
                # Seleccionar archivo de audio para analizar
                file_choice = input("Introduce el número del archivo: ").strip()
                if file_choice.isdigit():
                    idx = int(file_choice) - 1
                    if 0 <= idx < len(audio_files):
                        return os.path.join(current_path, audio_files[idx])
                    else:
                        print(color("❌ Número de archivo inválido", Colors.RED))
                        time.sleep(1)
            elif choice == "0000":
                # Volver al menú principal
                return None
            elif choice.isdigit():
                # Navegar a un directorio
                idx = int(choice) - 1
                if 0 <= idx < len(directories):
                    current_path = os.path.join(current_path, directories[idx])
                else:
                    print(color("❌ Opción inválida", Colors.RED))
                    time.sleep(1)
            else:
                print(color("❌ Opción inválida", Colors.RED))
                time.sleep(1)
                
        except KeyboardInterrupt:
            return None

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
            elif response.status_code == 404:
                print(color(f"   ❌ No encontrado en {provider}", Colors.RED))
            else:
                print(color(f"   ⚠️  Error {response.status_code} en {provider}", Colors.YELLOW))
                
        except requests.exceptions.Timeout:
            print(color(f"   ⏰ Timeout con {provider}", Colors.YELLOW))
        except requests.exceptions.ConnectionError:
            print(color(f"   🔌 Error de conexión con {provider}", Colors.YELLOW))
        except Exception as e:
            print(color(f"   ⚠️  Error con {provider}: {str(e)}", Colors.YELLOW))
            continue
    
    return False, None

def search_isrc_in_directory(directory, isrc_code):
    """Busca un ISRC específico en todos los archivos de un directorio"""
    print(color(f"🔍 Buscando ISRC {isrc_code} en {directory}", Colors.CYAN))
    
    found_files = []
    audio_files = []
    
    # Primero, encontrar todos los archivos de audio
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    # Procesar con barra de progreso
    total = len(audio_files)
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Escaneando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.YELLOW), end="\r")
        audio_info = deep_scan_audio(file_path)
        if audio_info['isrc'] and audio_info['isrc'].upper() == isrc_code.upper():
            found_files.append(audio_info)
    
    print()  # Nueva línea después de la barra de progreso
    return found_files

# ===== BÚSQUEDA EN SERVICIOS DE MÚSICA ALTERNATIVOS =====
def search_music_services(query, service="all"):
    """Busca en múltiples servicios de música"""
    results = {}
    
    print(color(f"🔍 Buscando '{query}' en servicios de música...", Colors.CYAN))
    
    # Simulación de búsqueda en varios servicios
    services = ["Deezer", "SoundCloud", "Bandcamp", "Internet Archive"]
    
    for svc in services:
        print(color(f"   Buscando en {svc}...", Colors.YELLOW))
        time.sleep(0.5)  # Simular tiempo de búsqueda
        # En una implementación real, aquí se conectaría a las APIs de estos servicios
        results[svc.lower()] = [f"Resultado 1 de {svc}", f"Resultado 2 de {svc}"]
    
    return results

# ===== FILTRADO DE CANCIONES =====
def filter_songs(directory, filters):
    """Filtrado multiplataforma por metadatos"""
    results = []
    audio_files = []
    
    # Primero, encontrar todos los archivos de audio
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, f))
    
    # Procesar con barra de progreso
    total = len(audio_files)
    for i, path in enumerate(audio_files, 1):
        print(color(f"   Escaneando {i}/{total}: {os.path.basename(path)[:30]}...", Colors.YELLOW), end="\r")
        info = deep_scan_audio(path)
        match = True
        for k, v in filters.items():
            if v and (str(info.get(k, '')).lower().find(v.lower()) == -1):
                match = False
                break
        if match:
            results.append(info)
    
    print()  # Nueva línea después de la barra de progreso
    return results

def show_song(song):
    print(color(f"📁 Archivo: {song['file']}", Colors.BLUE))
    print(f"   🎵 {color('Título:', Colors.BOLD)} {song.get('title', 'Desconocido')}")
    print(f"   🎤 {color('Artista:', Colors.BOLD)} {song.get('artist', 'Desconocido')}")
    print(f"   💿 {color('Álbum:', Colors.BOLD)} {song.get('album', 'Desconocido')}")
    print(f"   🏷️  {color('ISRC:', Colors.BOLD)} {color(song.get('isrc', 'No encontrado'), Colors.CYAN if song.get('isrc') else Colors.RED)}")
    print(f"   ⏱️  {color('Duración:', Colors.BOLD)} {int(song['duration']) if song['duration'] else '-'}s")
    print(f"   📊 {color('Bitrate:', Colors.BOLD)} {song.get('bitrate', '-')} kbps")
    print(f"   📦 {color('Tamaño:', Colors.BOLD)} {song['size'] // 1024} KB\n")

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
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(color("❌ Error al reproducir la canción.", Colors.RED))

# ===== INTERFAZ DE USUARIO MEJORADA =====
def print_banner():
    # Verificar actualizaciones al inicio
    if updater.check_for_updates():
        version_info = color(f"v{VERSION} → v{updater.new_version}", Colors.GREEN)
    else:
        version_info = color(f"v{VERSION} (Actualizado)", Colors.GREEN)
    
    banner = f"""{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                esVintable Ultimate PRO {version_info:<20} ║
║         Búsqueda Avanzada & Descarga por ISRC                ║
║           GitHub.com/JesusQuijada34/esvintable               ║
║           Plataforma: {color(PLATFORM_LABEL, Colors.YELLOW):<20}                   ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)
    
    # Mostrar estado de actualizaciones
    if updater.update_available:
        print(color(f"🔄 Actualización disponible: v{updater.new_version}", Colors.GREEN))
        if updater.update_info.get('critical', False):
            print(color("🚨 ACTUALIZACIÓN CRÍTICA: Se recomienda actualizar inmediatamente", Colors.RED))

def print_guide():
    print(color("🛠️  GUÍA RÁPIDA:", Colors.YELLOW))
    print("1. 🔍 Buscar canciones por metadatos (título, artista, álbum, ISRC)")
    print("2. 🏷️  Buscar ISRC específico en directorios")
    print("3. 📥 Descargar canciones por código ISRC")
    print("4. 🎧 Reproducir archivos de audio")
    print("5. 🌐 Búsqueda en servicios de música")
    print("6. 📁 Navegador de archivos")
    print("7. 🔄 Verificar actualizaciones")
    print("8. ⚙️  Instalar herramientas")
    print("9. ❌ Salir\n")

def main_menu():
    clear()
    print_banner()
    print_guide()
    
    options = [
        "🔍 Buscar canciones por metadatos",
        "🏷️ Buscar por ISRC específico",
        "📥 Descargar por ISRC",
        "🎧 Reproducir canción",
        "🌐 Buscar en servicios de música",
        "📁 Navegador de archivos",
        "🔄 Verificar actualizaciones",
        "⚙️ Instalar herramientas",
        "❌ Salir"
    ]
    
    for i, option in enumerate(options, 1):
        print(color(f"{i}. {option}", Colors.BOLD))
    
    print()
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
    
    # Usar navegador de archivos para seleccionar directorio
    print("\nSelecciona el directorio a buscar:")
    directory = file_browser()
    if directory is None:
        return
    
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
    
    # Usar navegador de archivos para seleccionar directorio
    print("\nSelecciona el directorio a buscar:")
    directory = file_browser()
    if directory is None:
        return
    
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
    
    # Usar navegador de archivos para seleccionar directorio de descarga
    print("\nSelecciona el directorio de descarga:")
    output_dir = file_browser()
    if output_dir is None:
        output_dir = "descargas_isrc"
    
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
    
    # Usar navegador de archivos para seleccionar archivo
    print("Selecciona el archivo de audio:")
    path = file_browser()
    if path is None or not os.path.isfile(path):
        print(color("❌ Archivo no válido.", Colors.RED))
        time.sleep(2)
        return
    
    if not path.lower().endswith(SUPPORTED_AUDIO):
        print(color("❌ Formato de audio no soportado.", Colors.RED))
        time.sleep(2)
        return
    
    # Mostrar metadatos antes de reproducir
    print(color("\n📋 Metadatos del archivo:", Colors.CYAN))
    info = deep_scan_audio(path)
    show_song(info)
    
    play_song(path)
    input("\n⏎ Enter para continuar...")

def external_search_menu():
    clear()
    print(color("🌐 Búsqueda en Servicios de Música", Colors.BOLD))
    
    query = input("Término de búsqueda: ").strip()
    if not query:
        print(color("❌ Debes introducir un término de búsqueda.", Colors.RED))
        time.sleep(2)
        return
    
    service = input("Servicio (deezer/soundcloud/bandcamp/archive/all): ").strip().lower() or "all"
    
    results = search_music_services(query, service)
    
    if results:
        for service_name, service_results in results.items():
            print(color(f"🎵 Resultados de {service_name.capitalize()} ({len(service_results)}):", Colors.GREEN))
            for i, result in enumerate(service_results[:5], 1):
                print(f"   {i}. {result}")
            print()
    else:
        print(color("❌ No se encontraron resultados.", Colors.RED))
    
    input("\n⏎ Enter para continuar...")

def file_browser_menu():
    clear()
    print(color("📁 Navegador de Archivos", Colors.BOLD))
    
    selected = file_browser()
    if selected:
        if os.path.isfile(selected):
            print(color(f"\n📄 Archivo seleccionado: {selected}", Colors.GREEN))
            # Mostrar metadatos
            info = deep_scan_audio(selected)
            show_song(info)
            
            # Opciones para archivos de audio
            if selected.lower().endswith(SUPPORTED_AUDIO):
                play = input("¿Reproducir? (s/n): ").lower()
                if play == 's':
                    play_song(selected)
        else:
            print(color(f"\n📂 Directorio seleccionado: {selected}", Colors.GREEN))
        
        input("\n⏎ Enter para continuar...")

def update_menu():
    clear()
    print(color("🔄 Sistema de Actualizaciones", Colors.BOLD))
    
    if updater.check_for_updates():
        print(color(f"🎉 ¡Nueva versión disponible! v{VERSION} → v{updater.new_version}", Colors.GREEN))
        print(color(f"📅 Fecha de lanzamiento: {updater.update_info.get('release_date', 'Desconocida')}", Colors.CYAN))
        print(color(f"📋 Cambios:\n{updater.update_info.get('changelog', 'No disponible')}", Colors.WHITE))
        
        if updater.update_info.get('critical', False):
            print(color("🚨 ACTUALIZACIÓN CRÍTICA: Se recomienda actualizar inmediatamente", Colors.RED))
        
        confirm = input("\n¿Actualizar ahora? (s/n): ").lower()
        if confirm == 's':
            print(color("⏳ Descargando actualización...", Colors.YELLOW))
            if updater.download_update():
                print(color("✅ ¡Actualización completada!", Colors.GREEN))
                print(color("🔄 Reiniciando aplicación...", Colors.CYAN))
                time.sleep(2)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print(color("❌ Error al descargar la actualización.", Colors.RED))
    else:
        print(color("✅ Ya tienes la última versión.", Colors.GREEN))
    
    input("\n⏎ Enter para continuar...")

def tools_menu():
    clear()
    print(color("⚙️ Herramientas del Sistema", Colors.BOLD))
    
    print("1. Verificar/Instalar dependencias")
    print("2. Verificar/Instalar FFmpeg (ffprobe, ffplay)")
    print("3. Verificar conexión a internet")
    print("4. Volver")
    
    choice = input("\nSelecciona una opción: ").strip()
    
    if choice == "1":
        print(color("🔍 Verificando dependencias...", Colors.YELLOW))
        check_dependencies()
        input("\n⏎ Enter para continuar...")
    elif choice == "2":
        print(color("🔍 Verificando FFmpeg...", Colors.YELLOW))
        if check_ffprobe() and check_ffplay():
            print(color("✅ FFmpeg ya está instalado.", Colors.GREEN))
        else:
            install_ffmpeg_tools()
        input("\n⏎ Enter para continuar...")
    elif choice == "3":
        print(color("🌐 Verificando conexión a internet...", Colors.YELLOW))
        try:
            requests.get("https://www.google.com", timeout=5)
            print(color("✅ Conexión a internet funcionando.", Colors.GREEN))
        except:
            print(color("❌ Sin conexión a internet.", Colors.RED))
        input("\n⏎ Enter para continuar...")

# ===== MAIN =====
def main():
    # Verificar dependencias al inicio
    if not check_dependencies():
        print(color("❌ No se pudieron instalar las dependencias necesarias.", Colors.RED))
        input("Presiona Enter para salir...")
        return
    
    # Iniciar verificador de actualizaciones en segundo plano
    updater.start_update_checker()
    
    # Bucle principal
    while True:
        try:
            option = main_menu()
            
            if option == "1":
                search_by_metadata_menu()
            elif option == "2":
                search_by_isrc_menu()
            elif option == "3":
                download_by_isrc_menu()
            elif option == "4":
                play_song_menu()
            elif option == "5":
                external_search_menu()
            elif option == "6":
                file_browser_menu()
            elif option == "7":
                update_menu()
            elif option == "8":
                tools_menu()
            elif option == "9":
                print(color("👋 ¡Hasta pronto!", Colors.CYAN))
                updater.stop_update_checker()
                break
            else:
                print(color("❌ Opción inválida.", Colors.RED))
                time.sleep(1)
        except KeyboardInterrupt:
            print(color("\n👋 ¡Hasta pronto!", Colors.CYAN))
            updater.stop_update_checker()
            break
        except Exception as e:
            print(color(f"❌ Error inesperado: {e}", Colors.RED))
            time.sleep(2)

if __name__ == "__main__":
    main()