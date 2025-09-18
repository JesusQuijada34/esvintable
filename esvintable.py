#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable Lite - Multiplataforma
# Autor: @JesusQuijada34 | GitHub.com/JesusQuijada34/esvintable

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
from urllib.parse import urlparse
from threading import Thread, Event
import cloudscraper
import mutagen
from mutagen.id3 import ID3, error as ID3error
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

# ===== CONFIGURACIÓN GLOBAL =====
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable_lite.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
LOCAL_XML_FILE = "details.xml"
UPDATE_INTERVAL = 10  # Verificar cada 10 segundos
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uId"  # Token truncado por seguridad

# Proveedores de música para búsqueda ISRC
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
        
        # Cargar versión local desde XML
        self.load_local_version()
        
    def load_local_version(self):
        """Carga la versión desde el XML local"""
        try:
            if os.path.exists(LOCAL_XML_FILE):
                tree = ET.parse(LOCAL_XML_FILE)
                root = tree.getroot()
                version_element = root.find('version')
                if version_element is not None:
                    self.local_version = version_element.text.strip()
                    return True
        except Exception as e:
            print(color(f"❌ Error leyendo XML local: {e}", Colors.RED))
        
        # Si no hay XML local, usar versión por defecto
        self.local_version = "0.0"
        return False
    
    def get_remote_info_from_xml(self):
        """Obtiene información completa desde el archivo XML remoto"""
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                # Extraer información del XML
                info = {}
                info['version'] = root.find('version').text.strip() if root.find('version') is not None else self.local_version
                info['changelog'] = root.find('changelog').text.strip() if root.find('changelog') is not None else ""
                info['release_date'] = root.find('release_date').text.strip() if root.find('release_date') is not None else ""
                info['critical'] = root.find('critical').text.strip().lower() == 'true' if root.find('critical') is not None else False
                info['message'] = root.find('message').text.strip() if root.find('message') is not None else ""
                
                return info
        except Exception:
            return None
    
    def download_xml_update(self):
        """Descarga la última versión del XML"""
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                with open(LOCAL_XML_FILE, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception:
            return False
    
    def compare_versions(self, local_ver, remote_ver):
        """Compara versiones en formato semántico (X.Y.Z)"""
        try:
            # Convertir versiones a tuplas numéricas para comparación
            local_parts = tuple(map(int, local_ver.split('.')))
            remote_parts = tuple(map(int, remote_ver.split('.')))
            
            # Comparar cada parte (major, minor, patch)
            return remote_parts > local_parts
        except:
            # Fallback: comparación lexicográfica
            return remote_ver > local_ver
    
    def check_for_updates(self, silent=False):
        """Verifica si hay actualizaciones disponibles comparando solo la versión"""
        try:
            # Obtener información completa del XML remoto
            self.update_info = self.get_remote_info_from_xml()
            
            if self.update_info and 'version' in self.update_info:
                self.remote_version = self.update_info['version']
                
                # Comparar versiones
                if self.compare_versions(self.local_version, self.remote_version):
                    # Actualizar XML local
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
                print(color(f"❌ Error al verificar actualizaciones: {e}", Colors.RED))
        return False
    
    def show_update_notification(self):
        """Muestra una notificación de actualización atractiva"""
        clear()
        print(color("╔══════════════════════════════════════════════════════════════╗", Colors.BRIGHT_BLUE))
        print(color("║", Colors.BRIGHT_BLUE) + color("                   🎉 ACTUALIZACIÓN DISPONIBLE                   ", Colors.BG_BLUE + Colors.BRIGHT_YELLOW) + color("║", Colors.BRIGHT_BLUE))
        print(color("╠══════════════════════════════════════════════════════════════╣", Colors.BRIGHT_BLUE))
        print(color("║", Colors.BRIGHT_BLUE) + color(f"   Versión actual: {self.local_version:<15}                     ", Colors.BRIGHT_WHITE) + color("║", Colors.BRIGHT_BLUE))
        print(color("║", Colors.BRIGHT_BLUE) + color(f"   Nueva versión:  {self.new_version:<15}                     ", Colors.BRIGHT_GREEN) + color("║", Colors.BRIGHT_BLUE))
        print(color("╠══════════════════════════════════════════════════════════════╣", Colors.BRIGHT_BLUE))
        
        if self.update_info.get('critical', False):
            print(color("║", Colors.BRIGHT_BLUE) + color("   🚨 ACTUALIZACIÓN CRÍTICA: Actualización recomendada       ", Colors.BG_RED + Colors.BRIGHT_WHITE) + color("║", Colors.BRIGHT_BLUE))
        
        if self.update_info.get('message'):
            msg = self.update_info['message']
            if len(msg) > 50:
                msg = msg[:47] + "..."
            print(color("║", Colors.BRIGHT_BLUE) + color(f"   💬 {msg:<50}", Colors.BRIGHT_CYAN) + color("║", Colors.BRIGHT_BLUE))
        
        print(color("╠══════════════════════════════════════════════════════════════╣", Colors.BRIGHT_BLUE))
        print(color("║", Colors.BRIGHT_BLUE) + color("   ¿Deseas actualizar ahora? (s/n):                          ", Colors.BRIGHT_WHITE) + color("║", Colors.BRIGHT_BLUE))
        print(color("╚══════════════════════════════════════════════════════════════╝", Colors.BRIGHT_BLUE))
        
        confirm = input("   ").strip().lower()
        if confirm == 's':
            self.download_script_update()
    
    def download_script_update(self):
        """Descarga la actualización del script desde el repo"""
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
                
                print(color("✅ ¡Actualización completada! Reiniciando...", Colors.BRIGHT_GREEN))
                time.sleep(2)
                os.execv(sys.executable, [sys.executable] + sys.argv)
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
                        self.check_for_updates(silent=True)
                        self.last_check = current_time
                    time.sleep(2)
                except Exception:
                    time.sleep(10)
        
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
    
    for dep in ["requests", "cloudscraper", "mutagen"]:
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

# ===== EXTRACCIÓN DE ISRC =====
def extract_isrc(file_path):
    """Extrae ISRC de un archivo de audio"""
    result = {
        'file': file_path, 
        'filename': os.path.basename(file_path),
        'isrc': None, 
        'artist': None, 
        'title': None,
        'method': None
    }
    
    # Método 1: Usar mutagen para metadatos
    try:
        audiofile = None
        if file_path.lower().endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                audiofile = None
                
            if audiofile is None:
                try:
                    audiofile = ID3(file_path)
                except:
                    audiofile = None
                    
        elif file_path.lower().endswith('.flac'):
            audiofile = FLAC(file_path)
        elif file_path.lower().endswith(('.m4a', '.mp4')):
            audiofile = MP4(file_path)
        
        if audiofile:
            # Extraer ISRC
            isrc_fields = ['isrc', 'TSRC']
            for field in isrc_fields:
                try:
                    if field in audiofile:
                        value = audiofile[field]
                        if isinstance(value, list):
                            value = value[0]
                        result['isrc'] = str(value).strip().upper()
                        result['method'] = f"Metadata ({field})"
                        break
                except:
                    continue
            
            # Extraer artista y título
            if 'artist' in audiofile:
                result['artist'] = audiofile['artist'][0] if isinstance(audiofile['artist'], list) else str(audiofile['artist'])
            if 'title' in audiofile:
                result['title'] = audiofile['title'][0] if isinstance(audiofile['title'], list) else str(audiofile['title'])
                    
    except Exception as e:
        result['error'] = f"Mutagen error: {str(e)}"
    
    # Método 2: Análisis hexadecimal si no se encontró ISRC
    if not result['isrc']:
        try:
            with open(file_path, 'rb') as f:
                # Leer partes del archivo donde suele estar el ISRC
                chunks = []
                chunks.append(f.read(100000))  # Inicio del archivo
                
                f.seek(-100000, 2)  # Final del archivo
                chunks.append(f.read(100000))
                
                content = b''.join(chunks)
                
                # Patrones para buscar ISRC
                patterns = [
                    br'ISRC[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'isrc[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                ]
                
                for i, pattern in enumerate(patterns):
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        found_isrc = match.group(1) if match.lastindex else match.group(0)
                        if isinstance(found_isrc, bytes):
                            found_isrc = found_isrc.decode('utf-8', errors='ignore')
                        if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found_isrc):
                            result['isrc'] = found_isrc.upper()
                            result['method'] = f"Hex Pattern {i+1}"
                            break
        except Exception as e:
            if 'error' not in result:
                result['error'] = f"Hex analysis error: {str(e)}"
    
    return result

def display_file_info(info):
    """Muestra información del archivo"""
    isrc_color = Colors.BRIGHT_GREEN if info.get('isrc') else Colors.BRIGHT_RED
    isrc_text = info.get('isrc', 'No encontrado')
    
    print(color(f"📁 Archivo: {info['filename']}", Colors.BRIGHT_BLUE))
    print(f"   🎵 {color('Título:', Colors.BOLD)} {info.get('title', 'Desconocido')}")
    print(f"   🎤 {color('Artista:', Colors.BOLD)} {info.get('artist', 'Desconocido')}")
    print(f"   🏷️  {color('ISRC:', Colors.BOLD)} {color(isrc_text, isrc_color)}")
    
    if info.get('method'):
        print(f"   🔍 {color('Método:', Colors.BOLD)} {info['method']}")
    
    if info.get('error'):
        print(f"   ⚠️  {color('Error:', Colors.BRIGHT_RED)} {info['error']}")

# ===== EXPLORADOR DE ARCHIVOS =====
def file_browser(start_path="."):
    """Navegador interactivo de archivos"""
    current_path = os.path.abspath(start_path)
    selected_file = None
    
    while True:
        clear()
        print(color(f"📁 Navegando: {current_path}", Colors.BRIGHT_BLUE))
        print(color("=" * 60, Colors.BRIGHT_CYAN))
        
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
        
        print(color("\n📂 DIRECTORIOS:", Colors.BOLD))
        for i, dir_name in enumerate(directories, 1):
            print(color(f"  {i:2d}. {dir_name}/", Colors.BRIGHT_BLUE))
        
        print(color("\n🎵 ARCHIVOS DE AUDIO:", Colors.BOLD))
        for i, file_name in enumerate(audio_files, 1):
            print(color(f"  {i + len(directories):2d}. {file_name}", Colors.BRIGHT_GREEN))
        
        if selected_file:
            print(color("\n" + "=" * 60, Colors.BRIGHT_CYAN))
            print(color("📋 METADATOS DEL ARCHIVO SELECCIONADO:", Colors.BOLD))
            info = extract_isrc(selected_file)
            display_file_info(info)
        
        print(color("\n" + "=" * 60, Colors.BRIGHT_CYAN))
        print("0. Volver al directorio anterior")
        print("00. Seleccionar este directorio")
        print("000. Extraer ISRC del archivo seleccionado")
        print("0000. Buscar ISRC en este directorio")
        print("00000. Volver al menú principal")
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == "0":
            # Volver al directorio anterior
            if current_path != os.path.abspath(start_path):
                current_path = os.path.dirname(current_path)
            selected_file = None
        elif choice == "00":
            # Seleccionar este directorio
            return current_path
        elif choice == "000" and selected_file:
            # Extraer ISRC del archivo seleccionado
            info = extract_isrc(selected_file)
            clear()
            display_file_info(info)
            if info['isrc']:
                download = input("¿Descargar versión de alta calidad? (s/n): ").lower()
                if download == 's':
                    download_by_isrc(info['isrc'], os.path.dirname(selected_file))
            input("\nPresiona Enter para continuar...")
        elif choice == "0000":
            # Buscar ISRC en este directorio
            search_isrc_in_directory(current_path)
        elif choice == "00000":
            # Volver al menú principal
            return None
        else:
            try:
                index = int(choice) - 1
                if index < len(directories):
                    # Navegar a directorio
                    selected_dir = directories[index]
                    current_path = os.path.join(current_path, selected_dir)
                    selected_file = None
                elif index < len(directories) + len(audio_files):
                    # Seleccionar archivo de audio
                    file_index = index - len(directories)
                    selected_file = os.path.join(current_path, audio_files[file_index])
                else:
                    print(color("❌ Opción inválida", Colors.RED))
                    time.sleep(1)
            except ValueError:
                print(color("❌ Opción inválida", Colors.RED))
                time.sleep(1)

# ===== BÚSQUEDA Y DESCARGA POR ISRC =====
def download_by_isrc(isrc, output_dir="descargas_isrc"):
    """Descarga una canción por su código ISRC"""
    scraper = cloudscraper.create_scraper()
    
    print(color(f"🔍 Buscando ISRC: {isrc}", Colors.BRIGHT_CYAN))
    
    for provider in PROVIDERS:
        try:
            url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            
            print(color(f"   Probando {provider}...", Colors.BRIGHT_YELLOW))
            response = scraper.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.join(output_dir, f"{isrc}_{provider}.m4a")
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print(color(f"✅ Descargado: {filename}", Colors.BRIGHT_GREEN))
                return True, filename
            elif response.status_code == 404:
                print(color(f"   ❌ No encontrado en {provider}", Colors.BRIGHT_RED))
            else:
                print(color(f"   ⚠️  Error {response.status_code} en {provider}", Colors.BRIGHT_YELLOW))
                
        except Exception as e:
            print(color(f"   ⚠️  Error con {provider}: {str(e)}", Colors.BRIGHT_YELLOW))
            continue
    
    return False, None

def search_isrc_in_directory(directory):
    """Busca ISRC en todos los archivos de un directorio"""
    print(color(f"🔍 Buscando ISRC en: {directory}", Colors.BRIGHT_CYAN))
    
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    if not audio_files:
        print(color("❌ No se encontraron archivos de audio", Colors.RED))
        time.sleep(2)
        return
    
    found_files = []
    total = len(audio_files)
    
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.BRIGHT_YELLOW), end="\r")
        info = extract_isrc(file_path)
        if info['isrc']:
            found_files.append(info)
    
    print()
    
    # Mostrar resultados
    clear()
    print(color("📊 RESULTADOS DE BÚSQUEDA DE ISRC:", Colors.BRIGHT_BLUE))
    print(color("=" * 80, Colors.BRIGHT_CYAN))
    
    if found_files:
        print(color(f"✅ Se encontraron {len(found_files)} archivos con ISRC:", Colors.BRIGHT_GREEN))
        for i, info in enumerate(found_files, 1):
            print(f"{i:2d}. {info['filename'][:40]:40} | "
                  f"ISRC: {color(info['isrc'], Colors.BRIGHT_GREEN):15} | "
                  f"Artista: {info.get('artist', '?')[:20]:20} | "
                  f"Título: {info.get('title', '?')[:20]:20}")
    else:
        print(color("❌ No se encontraron archivos con ISRC", Colors.BRIGHT_RED))
        print(color("💡 Solo el 30-40% de las canciones suelen tener ISRC", Colors.BRIGHT_YELLOW))
    
    input("\nPresiona Enter para continuar...")

def search_specific_isrc():
    """Busca un ISRC específico en archivos"""
    clear()
    print(color("🔍 Búsqueda de ISRC Específico", Colors.BOLD))
    
    isrc_code = input("Introduce el código ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
        print(color("❌ Formato ISRC inválido", Colors.RED))
        time.sleep(2)
        return
    
    directory = input("Directorio donde buscar (Enter para actual): ").strip()
    if not directory:
        directory = "."
    
    if not os.path.isdir(directory):
        print(color("❌ Directorio no encontrado", Colors.RED))
        time.sleep(2)
        return
    
    print(color(f"🔍 Buscando ISRC {isrc_code} en {directory}", Colors.BRIGHT_CYAN))
    
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    found_files = []
    total = len(audio_files)
    
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.BRIGHT_YELLOW), end="\r")
        info = extract_isrc(file_path)
        if info['isrc'] and info['isrc'].upper() == isrc_code:
            found_files.append(info)
    
    print()
    
    # Mostrar resultados
    clear()
    if found_files:
        print(color(f"✅ Se encontraron {len(found_files)} archivos con ISRC {isrc_code}:", Colors.BRIGHT_GREEN))
        for i, info in enumerate(found_files, 1):
            print(f"{i:2d}. {info['filename']}")
            print(f"   Artista: {info.get('artist', 'Desconocido')}")
            print(f"   Título: {info.get('title', 'Desconocido')}")
            print()
    else:
        print(color(f"❌ No se encontraron archivos con ISRC {isrc_code}", Colors.BRIGHT_RED))
    
    input("\nPresiona Enter para continuar...")

# ===== MENÚ PRINCIPAL =====
def print_banner():
    banner = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║{Colors.BRIGHT_MAGENTA}                   ESVINTABLE LITE v{updater.local_version:<10}               {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_GREEN}       Búsqueda y Descarga por ISRC - Multiplataforma        {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_YELLOW}         GitHub.com/JesusQuijada34/esvintable              {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_WHITE}                Plataforma: {PLATFORM_LABEL:<20}             {Colors.BRIGHT_CYAN}║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)

def main_menu():
    clear()
    print_banner()
    
    if updater.update_available and not updater.notification_shown:
        print(color(f"🔔 ¡Actualización disponible! v{updater.new_version} - Ejecuta opción 5", Colors.BRIGHT_GREEN))
    
    print(color("🛠️  OPCIONES DISPONIBLES:", Colors.BRIGHT_YELLOW))
    print("1. 🔍 Buscar ISRC en archivo individual")
    print("2. 📁 Buscar ISRC en directorio")
    print("3. 🏷️  Buscar ISRC específico")
    print("4. 📥 Descargar por ISRC")
    print("5. 🔄 Verificar actualizaciones")
    print("6. 📂 Explorador de archivos")
    print("7. ❌ Salir\n")
    
    return input("Selecciona una opción: ").strip()

def main():
    """Función principal del programa"""
    # Verificar dependencias
    if not check_dependencies():
        print(color("❌ No se pudieron instalar las dependencias necesarias", Colors.RED))
        return
    
    # Iniciar verificador de actualizaciones en segundo plano
    updater.start_update_checker()
    
    # Verificar actualizaciones al inicio
    updater.check_for_updates(silent=True)
    
    try:
        while True:
            choice = main_menu()
            
            if choice == "1":
                # Buscar ISRC en archivo individual
                file_path = input("Introduce la ruta del archivo: ").strip()
                if os.path.isfile(file_path):
                    info = extract_isrc(file_path)
                    clear()
                    display_file_info(info)
                    if info['isrc']:
                        download = input("¿Descargar versión de alta calidad? (s/n): ").lower()
                        if download == 's':
                            download_by_isrc(info['isrc'], os.path.dirname(file_path))
                    input("\nPresiona Enter para continuar...")
                else:
                    print(color("❌ Archivo no encontrado", Colors.RED))
                    time.sleep(1)
            
            elif choice == "2":
                # Buscar ISRC en directorio
                directory = input("Introduce la ruta del directorio: ").strip()
                if os.path.isdir(directory):
                    search_isrc_in_directory(directory)
                else:
                    print(color("❌ Directorio no encontrado", Colors.RED))
                    time.sleep(1)
            
            elif choice == "3":
                # Buscar ISRC específico
                search_specific_isrc()
            
            elif choice == "4":
                # Descargar por ISRC
                isrc_code = input("Introduce el código ISRC: ").strip().upper()
                if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
                    print(color("❌ Formato ISRC inválido", Colors.RED))
                    time.sleep(2)
                    continue
                
                output_dir = input("Directorio de descarga (Enter para 'descargas_isrc'): ").strip()
                if not output_dir:
                    output_dir = "descargas_isrc"
                
                success, filename = download_by_isrc(isrc_code, output_dir)
                if success:
                    print(color(f"✅ Descarga completada: {filename}", Colors.BRIGHT_GREEN))
                else:
                    print(color("❌ No se pudo descargar el archivo", Colors.BRIGHT_RED))
                input("\nPresiona Enter para continuar...")
            
            elif choice == "5":
                # Verificar actualizaciones manualmente
                clear()
                print(color("🔍 Buscando actualizaciones...", Colors.YELLOW))
                if updater.check_for_updates(silent=False):
                    print(color("✅ ¡Estás al día!", Colors.GREEN))
                input("\nPresiona Enter para continuar...")
            
            elif choice == "6":
                # Explorador de archivos
                start_dir = input("Directorio inicial (Enter para actual): ").strip()
                if not start_dir:
                    start_dir = "."
                file_browser(start_dir)
            
            elif choice == "7":
                # Salir
                print(color("👋 ¡Hasta pronto!", Colors.BRIGHT_GREEN))
                updater.stop_update_checker()
                break
            
            else:
                print(color("❌ Opción no válida", Colors.RED))
                time.sleep(1)
    
    except KeyboardInterrupt:
        print(color("\n👋 ¡Hasta pronto!", Colors.BRIGHT_GREEN))
        updater.stop_update_checker()

if __name__ == "__main__":
    main()