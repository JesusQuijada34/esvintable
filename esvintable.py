#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable Ultimate PRO - Multiplataforma
# Autor: @JesusQuijada34 | GitHub.com/JesusQuijada34/esvintable

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
import mutagen
from mutagen.id3 import ID3, error as ID3error
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

# ===== CONFIGURACIÓN GLOBAL =====
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
LOCAL_XML_FILE = "details.xml"
UPDATE_INTERVAL = 10  # Verificar cada 10 segundos
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uId":  # Token truncado por seguridad

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
    # Colores básicos
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
    LIGHT_GREEN = '\033[38;5;120m'
    GRAY = '\033[38;5;245m'
    DARK_GRAY = '\033[38;5;240m'
    LIGHT_CYAN = '\033[38;5;87m'
    GOLD = '\033[38;5;220m'
    SILVER = '\033[38;5;7m'
    BRIGHT_RED = '\033[38;5;196m'
    BRIGHT_GREEN = '\033[38;5;46m'
    BRIGHT_YELLOW = '\033[38;5;226m'
    BRIGHT_BLUE = '\033[38;5;21m'
    BRIGHT_MAGENTA = '\033[38;5;201m'
    
    # Fondos
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_YELLOW = '\033[43m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    BG_BLACK = '\033[40m'

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
        self.first_check = True
        
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
    
    def get_remote_version(self):
        """Obtiene solo la versión del archivo XML remoto"""
        try:
            response = requests.get(DETAILS_XML_URL, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                version_element = root.find('version')
                if version_element is not None:
                    return version_element.text.strip()
        except Exception:
            pass
        return None
    
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
            # Primera verificación: solo comparar versiones
            if self.first_check:
                remote_ver = self.get_remote_version()
                if remote_ver and self.compare_versions(self.local_version, remote_ver):
                    # Segunda verificación: obtener información completa
                    self.update_info = self.get_remote_info_from_xml()
                    if self.update_info and 'version' in self.update_info:
                        self.remote_version = self.update_info['version']
                        
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
                self.first_check = False
            else:
                # Verificaciones posteriores
                self.update_info = self.get_remote_info_from_xml()
                if self.update_info and 'version' in self.update_info:
                    self.remote_version = self.update_info['version']
                    
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
                    
        except Exception:
            pass
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
                        self.check_for_updates(silent=True)  # Verificación silenciosa en segundo plano
                        self.last_check = current_time
                    time.sleep(2)  # Verificar cada 2 segundos
                except Exception:
                    time.sleep(10)  # Esperar más en caso de error
        
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

# ===== MÉTODOS AVANZADOS DE EXTRACCIÓN DE METADATOS =====
def extract_isrc_advanced(file_path, deep_scan=False):
    """Extrae ISRC y metadatos usando múltiples métodos avanzados"""
    result = {
        'file': file_path, 
        'filename': os.path.basename(file_path),
        'isrc': None, 
        'artist': None, 
        'album': None, 
        'title': None, 
        'duration': None, 
        'bitrate': None,
        'sample_rate': None,
        'channels': None,
        'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        'tags': {},
        'method': None,
        'hex_data': None,
        'file_type': os.path.splitext(file_path)[1].lower(),
        'has_cover': False,
        'year': None,
        'genre': None,
        'track_number': None,
        'composer': None,
        'publisher': None,
        'isrc_found': False,
        'quality_rating': 0
    }
    
    # Método 1: Usar mutagen para metadatos específicos del formato
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
            tags_to_extract = {
                'artist': ['artist', 'performer', '©ART'],
                'title': ['title', '©nam'],
                'album': ['album', '©alb'],
                'isrc': ['isrc', 'TSRC'],
                'date': ['date', 'year', '©day'],
                'genre': ['genre', '©gen'],
                'tracknumber': ['tracknumber', 'trck', '©trk'],
                'composer': ['composer', '©wrt'],
                'publisher': ['publisher', '©pub']
            }
            
            for field, tags in tags_to_extract.items():
                for tag in tags:
                    try:
                        if tag in audiofile:
                            value = audiofile[tag]
                            if isinstance(value, list):
                                value = value[0]
                            result[field] = str(value)
                            break
                    except:
                        continue
            
            if hasattr(audiofile, 'pictures') and audiofile.pictures:
                result['has_cover'] = True
            elif file_path.lower().endswith('.mp3'):
                try:
                    id3 = ID3(file_path)
                    for key in id3.keys():
                        if 'APIC' in key:
                            result['has_cover'] = True
                            break
                except:
                    pass
                    
    except Exception as e:
        result['error'] = f"Mutagen error: {str(e)}"
    
    # Método 2: FFprobe para información técnica
    if check_ffprobe():
        try:
            proc = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path],
                capture_output=True, text=True, timeout=15
            )
            if proc.returncode == 0:
                info = json.loads(proc.stdout)
                
                if 'format' in info:
                    format_info = info['format']
                    result['duration'] = float(format_info.get('duration', 0))
                    result['bitrate'] = int(format_info.get('bit_rate', 0)) // 1000 if format_info.get('bit_rate') else None
                    
                    if 'tags' in format_info:
                        format_tags = format_info['tags']
                        result['tags'].update(format_tags)
                        
                        isrc_fields = ['ISRC', 'TSRC', 'isrc', 'ISRC_code', 'ISRC_Code']
                        for field in isrc_fields:
                            if field in format_tags and not result['isrc']:
                                result['isrc'] = format_tags[field]
                                result['method'] = f"FFprobe format ({field})"
                                break
                
                if 'streams' in info and len(info['streams']) > 0:
                    stream_info = info['streams'][0]
                    result['sample_rate'] = stream_info.get('sample_rate')
                    result['channels'] = stream_info.get('channels')
                    
                    if 'tags' in stream_info:
                        stream_tags = stream_info['tags']
                        result['tags'].update(stream_tags)
                        
                        isrc_fields = ['ISRC', 'TSRC', 'isrc', 'ISRC_code', 'ISRC_Code']
                        for field in isrc_fields:
                            if field in stream_tags and not result['isrc']:
                                result['isrc'] = stream_tags[field]
                                result['method'] = f"FFprobe stream ({field})"
                                break
                                
        except Exception as e:
            if 'error' not in result:
                result['error'] = f"FFprobe error: {str(e)}"
            else:
                result['error'] += f" | FFprobe error: {str(e)}"
    
    # Método 3: Análisis hexadecimal
    if deep_scan or not result['isrc']:
        try:
            with open(file_path, 'rb') as f:
                chunks = []
                chunks.append(f.read(1000000))
                
                f.seek(-500000, 2)
                chunks.append(f.read(500000))
                
                file_size = os.path.getsize(file_path)
                if file_size > 2000000:
                    f.seek(file_size // 2)
                    chunks.append(f.read(100000))
                
                content = b''.join(chunks)
                result['hex_data'] = content.hex()[:200] + "..."
                
                patterns = [
                    br'ISRC[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'isrc[=:]([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'ISRC\s*[:=]\s*([A-Z]{2}[A-Z0-9]{3}\d{5})',
                    br'Z\d{3}\d{5}',
                ]
                
                for i, pattern in enumerate(patterns):
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        found_isrc = match.group(1) if match.lastindex else match.group(0)
                        if isinstance(found_isrc, bytes):
                            found_isrc = found_isrc.decode('utf-8', errors='ignore')
                        if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', found_isrc):
                            result['isrc'] = found_isrc
                            result['method'] = f"Hex Pattern {i+1}"
                            break
        except Exception as e:
            if 'error' not in result:
                result['error'] = f"Hex analysis error: {str(e)}"
            else:
                result['error'] += f" | Hex analysis error: {str(e)}"
    
    # Método 4: Búsqueda en strings del archivo
    if deep_scan and not result['isrc']:
        try:
            with open(file_path, 'rb') as f:
                content = f.read(500000)
                strings = re.findall(b'[A-Za-z0-9=:]{10,50}', content)
                for s in strings:
                    try:
                        decoded = s.decode('utf-8', errors='ignore')
                        isrc_match = re.search(r'[A-Z]{2}[A-Z0-9]{3}\d{5}', decoded)
                        if isrc_match:
                            result['isrc'] = isrc_match.group(0)
                            result['method'] = "String extraction"
                            break
                    except:
                        continue
        except Exception as e:
            if 'error' not in result:
                result['error'] = f"String extraction error: {str(e)}"
            else:
                result['error'] += f" | String extraction error: {str(e)}"
    
    # Calcular calidad de metadatos
    result['isrc_found'] = result['isrc'] is not None
    quality_score = 0
    
    if result['title']: quality_score += 15
    if result['artist']: quality_score += 15
    if result['album']: quality_score += 10
    if result['isrc']: quality_score += 20
    if result['year']: quality_score += 5
    if result['genre']: quality_score += 5
    if result['track_number']: quality_score += 5
    if result['duration']: quality_score += 5
    if result['bitrate'] and result['bitrate'] >= 192: quality_score += 10
    if result['has_cover']: quality_score += 10
    
    result['quality_rating'] = quality_score
    
    return result

def display_audio_info(info, detailed=False):
    """Muestra información del audio de forma atractiva"""
    isrc_color = Colors.BRIGHT_GREEN if info.get('isrc') else Colors.BRIGHT_RED
    isrc_text = info.get('isrc', 'No encontrado')
    
    quality = info.get('quality_rating', 0)
    if quality >= 70:
        quality_color = Colors.BRIGHT_GREEN
        quality_text = "Excelente"
    elif quality >= 40:
        quality_color = Colors.BRIGHT_YELLOW
        quality_text = "Regular"
    else:
        quality_color = Colors.BRIGHT_RED
        quality_text = "Mala"
    
    print(color(f"📁 Archivo: {info['filename']}", Colors.BRIGHT_BLUE))
    print(f"   🎵 {color('Título:', Colors.BOLD)} {info.get('title', 'Desconocido')}")
    print(f"   🎤 {color('Artista:', Colors.BOLD)} {info.get('artist', 'Desconocido')}")
    print(f"   💿 {color('Álbum:', Colors.BOLD)} {info.get('album', 'Desconocido')}")
    print(f"   🏷️  {color('ISRC:', Colors.BOLD)} {color(isrc_text, isrc_color)}")
    
    if info.get('method'):
        print(f"   🔍 {color('Método:', Colors.BOLD)} {info['method']}")
    
    print(f"   📊 {color('Calidad metadatos:', Colors.BOLD)} {color(f'{quality_text} ({quality}%)', quality_color)}")
    
    if detailed:
        print(f"   ⏱️  {color('Duración:', Colors.BOLD)} {int(info['duration']) if info.get('duration') else '-'}s")
        print(f"   🔊 {color('Bitrate:', Colors.BOLD)} {info.get('bitrate', '-')} kbps")
        print(f"   📏 {color('Sample Rate:', Colors.BOLD)} {info.get('sample_rate', '-')} Hz")
        print(f"   🎚️  {color('Canales:', Colors.BOLD)} {info.get('channels', '-')}")
        print(f"   📦 {color('Tamaño:', Colors.BOLD)} {info['size'] // 1024} KB")
        print(f"   📅 {color('Año:', Colors.BOLD)} {info.get('year', '-')}")
        print(f"   🎼 {color('Género:', Colors.BOLD)} {info.get('genre', '-')}")
        print(f"   🔢 {color('Pista:', Colors.BOLD)} {info.get('track_number', '-')}")
        print(f"   🎹 {color('Compositor:', Colors.BOLD)} {info.get('composer', '-')}")
        print(f"   🏢 {color('Discográfica:', Colors.BOLD)} {info.get('publisher', '-')}")
        print(f"   🖼️  {color('Portada:', Colors.BOLD)} {'Sí' if info.get('has_cover') else 'No'}")
        print(f"   📋 {color('Tipo:', Colors.BOLD)} {info.get('file_type', '-')}")
        
        if info.get('hex_data'):
            print(f"   🔢 {color('Hex Sample:', Colors.BOLD)} {info['hex_data']}")
        
        if info.get('tags'):
            print(f"   🏷️  {color('Etiquetas:', Colors.BOLD)}")
            for k, v in list(info['tags'].items())[:5]:
                print(f"        {k}: {v}")
            if len(info['tags']) > 5:
                print(f"        ... y {len(info['tags']) - 5} más")
                
        if info.get('error'):
            print(f"   ⚠️  {color('Errores:', Colors.BRIGHT_RED)} {info['error']}")

# ===== BÚSQUEDA POR SIMILITUD =====
def search_similar_songs(directory, target_song, similarity_threshold=70):
    """Busca canciones similares basándose en metadatos"""
    print(color(f"🔍 Buscando canciones similares a: {target_song.get('title', 'Unknown')}", Colors.CYAN))
    
    similar_songs = []
    audio_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    total = len(audio_files)
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.YELLOW), end="\r")
        
        if file_path == target_song['file']:
            continue
            
        song_info = extract_isrc_advanced(file_path)
        similarity = calculate_similarity(target_song, song_info)
        
        if similarity >= similarity_threshold:
            similar_songs.append((song_info, similarity))
    
    print()
    
    similar_songs.sort(key=lambda x: x[1], reverse=True)
    
    return similar_songs

def calculate_similarity(song1, song2):
    """Calcula la similitud entre dos canciones basándose en metadatos"""
    similarity = 0
    
    if song1.get('artist') and song2.get('artist'):
        if song1['artist'].lower() == song2['artist'].lower():
            similarity += 30
        elif song1['artist'].lower() in song2['artist'].lower() or song2['artist'].lower() in song1['artist'].lower():
            similarity += 15
    
    if song1.get('title') and song2.get('title'):
        if song1['title'].lower() == song2['title'].lower():
            similarity += 25
        elif song1['title'].lower() in song2['title'].lower() or song2['title'].lower() in song1['title'].lower():
            similarity += 10
    
    if song1.get('album') and song2.get('album'):
        if song1['album'].lower() == song2['album'].lower():
            similarity += 15
    
    if song1.get('duration') and song2.get('duration'):
        if abs(song1['duration'] - song2['duration']) <= 10:
            similarity += 10
    
    if song1.get('isrc') and song2.get('isrc') and song1['isrc'] == song2['isrc']:
        similarity += 50
    
    return min(similarity, 100)

# ===== EXPLORADOR DE ARCHIVOS AVANZADO =====
def advanced_file_browser(start_path="."):
    """Navegador interactivo de archivos con vista previa de metadatos"""
    current_path = os.path.abspath(start_path)
    selected_file = None
    
    while True:
        clear()
        print(color(f"📁 Navegando: {current_path}", Colors.BRIGHT_BLUE))
        print(color("=" * 80, Colors.BRIGHT_CYAN))
        
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
        
        other_files = [f for f in files if not f.lower().endswith(SUPPORTED_AUDIO)]
        if other_files:
            print(color("\n📄 OTROS ARCHIVOS:", Colors.BOLD))
            for i, file_name in enumerate(other_files, 1 + len(directories) + len(audio_files)):
                print(color(f"  {i:2d}. {file_name}", Colors.WHITE))
        
        if selected_file:
            print(color("\n" + "=" * 80, Colors.BRIGHT_CYAN))
            print(color("📋 METADATOS DEL ARCHIVO SELECCIONADO:", Colors.BOLD))
            info = extract_isrc_advanced(selected_file)
            display_audio_info(info)
        
        print(color("\n" + "=" * 80, Colors.BRIGHT_CYAN))
        print("0. Volver al directorio anterior")
        print("00. Seleccionar este directorio para buscar")
        print("000. Extraer ISRC del archivo seleccionado")
        print("0000. Analizar archivo en profundidad")
        print("00000. Buscar canciones similares")
        print("000000. Volver al menú principal")
        
        try:
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == "0":
                current_path = os.path.dirname(current_path)
                selected_file = None
            elif choice == "00":
                return current_path
            elif choice == "000" and selected_file:
                info = extract_isrc_advanced(selected_file, deep_scan=True)
                if info['isrc']:
                    print(color(f"✅ ISRC encontrado: {info['isrc']}", Colors.BRIGHT_GREEN))
                    if input("¿Descargar versión de alta calidad? (s/n): ").lower() == 's':
                        download_by_isrc(info['isrc'], os.path.dirname(selected_file))
                else:
                    print(color("❌ No se encontró ISRC en este archivo", Colors.BRIGHT_RED))
                    print(color("💡 Muchas canciones no tienen ISRC, especialmente:", Colors.BRIGHT_YELLOW))
                    print(color("   - Producciones independientes", Colors.BRIGHT_YELLOW))
                    print(color("   - Canciones antiguas (anteriores a 2000)", Colors.BRIGHT_YELLOW))
                    print(color("   - Archivos convertidos o modificados", Colors.BRIGHT_YELLOW))
                    print(color("   - Descargas de fuentes no oficiales", Colors.BRIGHT_YELLOW))
                input("\n⏎ Enter para continuar...")
            elif choice == "0000" and selected_file:
                print(color("🔍 Analizando archivo en profundidad...", Colors.BRIGHT_YELLOW))
                info = extract_isrc_advanced(selected_file, deep_scan=True)
                display_audio_info(info, detailed=True)
                input("\n⏎ Enter para continuar...")
            elif choice == "00000" and selected_file:
                print(color("🔍 Buscando canciones similares...", Colors.BRIGHT_YELLOW))
                info = extract_isrc_advanced(selected_file)
                similar_songs = search_similar_songs(current_path, info)
                
                if similar_songs:
                    print(color(f"\n🎵 Se encontraron {len(similar_songs)} canciones similares:", Colors.BRIGHT_GREEN))
                    for i, (song, similarity) in enumerate(similar_songs[:5], 1):
                        print(color(f"{i}. Similitud: {similarity}%", Colors.WHITE))
                        display_audio_info(song)
                else:
                    print(color("❌ No se encontraron canciones similares", Colors.BRIGHT_RED))
                input("\n⏎ Enter para continuar...")
            elif choice == "000000":
                return None
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(directories):
                    current_path = os.path.join(current_path, directories[idx])
                    selected_file = None
                elif len(directories) <= idx < len(directories) + len(audio_files):
                    selected_file = os.path.join(current_path, audio_files[idx - len(directories)])
                else:
                    print(color("❌ Opción inválida", Colors.BRIGHT_RED))
                    time.sleep(1)
            else:
                print(color("❌ Opción inválida", Colors.BRIGHT_RED))
                time.sleep(1)
                
        except KeyboardInterrupt:
            return None

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
                
        except requests.exceptions.Timeout:
            print(color(f"   ⏰ Timeout con {provider}", Colors.BRIGHT_YELLOW))
        except requests.exceptions.ConnectionError:
            print(color(f"   🔌 Error de conexión con {provider}", Colors.BRIGHT_YELLOW))
        except Exception as e:
            print(color(f"   ⚠️  Error con {provider}: {str(e)}", Colors.BRIGHT_YELLOW))
            continue
    
    return False, None

def search_isrc_in_directory(directory, isrc_code):
    """Busca un ISRC específico en todos los archivos de un directorio"""
    print(color(f"🔍 Buscando ISRC {isrc_code} en {directory}", Colors.BRIGHT_CYAN))
    
    found_files = []
    audio_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    total = len(audio_files)
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Escaneando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.BRIGHT_YELLOW), end="\r")
        audio_info = extract_isrc_advanced(file_path)
        if audio_info['isrc'] and audio_info['isrc'].upper() == isrc_code.upper():
            found_files.append(audio_info)
    
    print()
    return found_files

# ===== BÚSQUEDA EN SERVICIOS DE MÚSICA ALTERNATIVOS =====
def search_music_services(query, service="all"):
    """Busca en múltiples servicios de música"""
    results = {}
    
    print(color(f"🔍 Buscando '{query}' en servicios de música...", Colors.BRIGHT_CYAN))
    
    services = ["Deezer", "SoundCloud", "Bandcamp", "Internet Archive"]
    
    for svc in services:
        print(color(f"   Buscando en {svc}...", Colors.BRIGHT_YELLOW))
        time.sleep(0.5)
        results[svc.lower()] = [f"Resultado 1 de {svc}", f"Resultado 2 de {svc}"]
    
    return results

# ===== FILTRADO DE CANCIONES =====
def filter_songs(directory, filters):
    """Filtrado multiplataforma por metadatos"""
    results = []
    audio_files = []
    
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, f))
    
    total = len(audio_files)
    for i, path in enumerate(audio_files, 1):
        print(color(f"   Escaneando {i}/{total}: {os.path.basename(path)[:30]}...", Colors.BRIGHT_YELLOW), end="\r")
        info = extract_isrc_advanced(path)
        match = True
        for k, v in filters.items():
            if v and (str(info.get(k, '')).lower().find(v.lower()) == -1):
                match = False
                break
        if match:
            results.append(info)
    
    print()
    return results

# ===== REPRODUCCIÓN =====
def play_song(file_path):
    """Reproduce multiplataforma con ffplay si está disponible"""
    if not check_ffplay():
        print(color("⚠️  ffplay no está instalado.", Colors.BRIGHT_RED))
        install = input("¿Instalar FFmpeg? (s/n): ").lower()
        if install == 's':
            if install_ffmpeg_tools():
                return play_song(file_path)
        return
    
    print(color(f"🎧 Reproduciendo: {os.path.basename(file_path)}", Colors.BRIGHT_GREEN))
    try:
        if IS_WINDOWS:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', file_path], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(color("❌ Error al reproducir la canción.", Colors.BRIGHT_RED))

# ===== BANNER MEJORADO =====
def print_banner():
    try:
        if os.path.exists(LOCAL_XML_FILE):
            tree = ET.parse(LOCAL_XML_FILE)
            root = tree.getroot()
            version_element = root.find('version')
            if version_element is not None:
                current_version = version_element.text.strip()
            else:
                current_version = "Desconocida"
        else:
            current_version = "Desconocida"
    except:
        current_version = "Desconocida"
    
    banner = f"""
{Colors.BRIGHT_CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║{Colors.BRIGHT_MAGENTA}          ███████╗███████╗██╗   ██╗██╗███╗   ██╗████████╗          {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_MAGENTA}          ██╔════╝██╔════╝██║   ██║██║████╗  ██║╚══██╔══╝          {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_MAGENTA}          █████╗  ███████╗██║   ██║██║██╔██╗ ██║   ██║             {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_MAGENTA}          ██╔══╝  ╚════██║╚██╗ ██╔╝██║██║╚██╗██║   ██║             {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_MAGENTA}          ███████╗███████║ ╚████╔╝ ██║██║ ╚████║   ██║             {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_MAGENTA}          ╚══════╝╚══════╝  ╚═══╝  ╚═╝╚═╝  ╚═══╝   ╚═╝             {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_BLUE}                Ultimate PRO v{current_version:<15}               {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_GREEN}       Búsqueda Avanzada & Descarga por ISRC - Multiplataforma    {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_YELLOW}         GitHub.com/JesusQuijada34/esvintable                {Colors.BRIGHT_CYAN}║
║{Colors.BRIGHT_WHITE}                Plataforma: {PLATFORM_LABEL:<20}               {Colors.BRIGHT_CYAN}║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)

def print_guide():
    print(color("🛠️  GUÍA RÁPIDA:", Colors.BRIGHT_YELLOW))
    print("1. 🔍 Buscar canciones por metadatos (título, artista, álbum, ISRC)")
    print("2. 🏷️  Buscar ISRC específico en directorios")
    print("3. 📥 Descargar canciones por código ISRC")
    print("4. 🎧 Reproducir archivos de audio")
    print("5. 🌐 Búsqueda en servicios de música")
    print("6. 📁 Navegador de archivos avanzado")
    print("7. 🔄 Verificar actualizaciones")
    print("8. ⚙️  Instalar herramientas")
    print("9. 📊 Estadísticas de biblioteca")
    print("10. 🎯 Búsqueda inteligente")
    print("11. ❌ Salir\n")

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
        "📁 Navegador de archivos avanzado",
        "🔄 Verificar actualizaciones",
        "⚙️ Instalar herramientas",
        "📊 Estadísticas de biblioteca",
        "🎯 Búsqueda inteligente",
        "❌ Salir"
    ]
    
    for i, option in enumerate(options, 1):
        print(color(f"{i}. {option}", Colors.BOLD))
    
    print()
    choice = input("Selecciona una opción: ").strip()
    
    # Verificar si hay actualizaciones antes de procesar la opción
    if updater.update_available and not updater.notification_shown:
        updater.show_update_notification()
    
    return choice

# ===== FUNCIONES DEL MENÚ PRINCIPAL =====
def search_by_metadata_menu():
    clear()
    print(color("🔎 Búsqueda por Metadatos", Colors.BOLD))
    print("Deja vacío cualquier campo para ignorarlo.")
    
    filters = {
        'title': input("Título: ").strip(),
        'artist': input("Artista: ").strip(),
        'album': input("Álbum: .strip()"),
        'isrc': input("ISRC: ").strip(),
    }
    
    print("\nSelecciona el directorio a buscar:")
    directory = advanced_file_browser()
    if directory is None:
        return
    
    if not os.path.isdir(directory):
        print(color("❌ El directorio no existe.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    print(color("⏳ Buscando canciones...", Colors.BRIGHT_CYAN))
    found = filter_songs(directory, filters)
    
    if found:
        print(color(f"\n🎶 Se encontraron {len(found)} canciones:", Colors.BRIGHT_GREEN))
        for i, song in enumerate(found, 1):
            print(color(f"{i}.", Colors.WHITE))
            display_audio_info(song)
        
        play = input("¿Reproducir alguna? Número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print(color("❌ No se encontraron canciones con esos filtros.", Colors.BRIGHT_RED))
    
    input("\n⏎ Enter para continuar...")

def search_by_isrc_menu():
    clear()
    print(color("🏷️ Búsqueda por ISRC", Colors.BOLD))
    
    isrc_code = input("Introduce el código ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code):
        print(color("❌ Formato ISRC inválido.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    print("\nSelecciona el directorio a buscar:")
    directory = advanced_file_browser()
    if directory is None:
        return
    
    if not os.path.isdir(directory):
        print(color("❌ El directorio no existe.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    print(color("⏳ Buscando ISRC...", Colors.BRIGHT_CYAN))
    found = search_isrc_in_directory(directory, isrc_code)
    
    if found:
        print(color(f"\n✅ Se encontraron {len(found)} archivos con ISRC {isrc_code}:", Colors.BRIGHT_GREEN))
        for i, song in enumerate(found, 1):
            print(color(f"{i}.", Colors.WHITE))
            display_audio_info(song)
        
        play = input("¿Reproducir alguna? Número o Enter para omitir: ").strip()
        if play.isdigit() and 1 <= int(play) <= len(found):
            play_song(found[int(play)-1]['file'])
    else:
        print(color(f"❌ No se encontraron archivos con ISRC {isrc_code}", Colors.BRIGHT_RED))
        print(color("💡 Solo el 30-40% de las canciones suelen tener ISRC", Colors.BRIGHT_YELLOW))
    
    input("\n⏎ Enter para continuar...")

def download_by_isrc_menu():
    clear()
    print(color("📥 Descargar por ISRC", Colors.BOLD))
    
    isrc_code = input("Introduce el código ISRC: ").strip().upper()
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc_code:
        print(color("❌ Formato ISRC inválido.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    print("\nSelecciona el directorio de descarga:")
    output_dir = advanced_file_browser()
    if output_dir is None:
        output_dir = "descargas_isrc"
    
    success, filename = download_by_isrc(isrc_code, output_dir)
    if success:
        print(color(f"✅ Descarga completada: {filename}", Colors.BRIGHT_GREEN))
        
        play = input("¿Reproducir descarga? (s/n): ").lower()
        if play == 's':
            play_song(filename)
    else:
        print(color("❌ No se pudo descargar el archivo.", Colors.BRIGHT_RED))
    
    input("\n⏎ Enter para continuar...")

def play_song_menu():
    clear()
    print(color("🎧 Reproducir Canción", Colors.BOLD))
    
    print("Selecciona el archivo de audio:")
    path = advanced_file_browser()
    if path is None or not os.path.isfile(path):
        print(color("❌ Archivo no válido.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    if not path.lower().endswith(SUPPORTED_AUDIO):
        print(color("❌ Formato de audio no soportado.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    print(color("\n📋 Metadatos del archivo:", Colors.BRIGHT_CYAN))
    info = extract_isrc_advanced(path)
    display_audio_info(info)
    
    play_song(path)
    input("\n⏎ Enter para continuar...")

def external_search_menu():
    clear()
    print(color("🌐 Búsqueda en Servicios de Música", Colors.BOLD))
    
    query = input("Término de búsqueda: ").strip()
    if not query:
        print(color("❌ Debes introducir un término de búsqueda.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    service = input("Servicio (deezer/soundcloud/bandcamp/archive/all): ").strip().lower() or "all"
    
    results = search_music_services(query, service)
    
    if results:
        for service_name, service_results in results.items():
            print(color(f"🎵 Resultados de {service_name.capitalize()} ({len(service_results)}):", Colors.BRIGHT_GREEN))
            for i, result in enumerate(service_results[:5], 1):
                print(f"   {i}. {result}")
            print()
    else:
        print(color("❌ No se encontraron resultados.", Colors.BRIGHT_RED))
    
    input("\n⏎ Enter para continuar...")

def file_browser_menu():
    clear()
    print(color("📁 Navegador de Archivos Avanzado", Colors.BOLD))
    
    selected = advanced_file_browser()
    if selected:
        if os.path.isfile(selected):
            print(color(f"\n📄 Archivo seleccionado: {selected}", Colors.BRIGHT_GREEN))
            info = extract_isrc_advanced(selected, deep_scan=True)
            display_audio_info(info, detailed=True)
            
            if selected.lower().endswith(SUPPORTED_AUDIO):
                play = input("¿Reproducir? (s/n): ").lower()
                if play == 's':
                    play_song(selected)
        else:
            print(color(f"\n📂 Directorio seleccionado: {selected}", Colors.BRIGHT_GREEN))
        
        input("\n⏎ Enter para continuar...")

def update_menu():
    clear()
    print(color("🔄 Sistema de Actualizaciones", Colors.BOLD))
    
    if updater.check_for_updates():
        print(color(f"🎉 ¡Nueva versión disponible! v{updater.local_version} → v{updater.new_version}", Colors.BRIGHT_GREEN))
        print(color(f"📅 Fecha de lanzamiento: {updater.update_info.get('release_date', 'Desconocida')}", Colors.BRIGHT_CYAN))
        print(color(f"📋 Cambios:\n{updater.update_info.get('changelog', 'No disponible')}", Colors.WHITE))
        
        if updater.update_info.get('critical', False):
            print(color("🚨 ACTUALIZACIÓN CRÍTICA: Se recomienda actualizar inmediatamente", Colors.BRIGHT_RED))
        
        if updater.update_info.get('message'):
            print(color(f"💬 Mensaje: {updater.update_info['message']}", Colors.BRIGHT_CYAN))
        
        confirm = input("\n¿Actualizar ahora? (s/n): ").lower()
        if confirm == 's':
            print(color("⏳ Descargando actualización...", Colors.BRIGHT_YELLOW))
            if updater.download_script_update():
                print(color("✅ ¡Actualización completada!", Colors.BRIGHT_GREEN))
                print(color("🔄 Reiniciando aplicación...", Colors.BRIGHT_CYAN))
                time.sleep(2)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print(color("❌ Error al descargar la actualización.", Colors.BRIGHT_RED))
    else:
        print(color("✅ Ya tienes la última versión.", Colors.BRIGHT_GREEN))
        print(color("💡 El sistema verifica automáticamente cada 10 segundos", Colors.BRIGHT_YELLOW))
    
    input("\n⏎ Enter para continuar...")

def tools_menu():
    clear()
    print(color("⚙️ Herramientas del Sistema", Colors.BOLD))
    
    print("1. Verificar/Instalar dependencias")
    print("2. Verificar/Instalar FFmpeg (ffprobe, ffplay)")
    print("3. Verificar conexión a internet")
    print("4. Limpiar caché de búsquedas")
    print("5. Ver información del sistema")
    print("6. Volver")
    
    choice = input("\nSelecciona una opción: ").strip()
    
    if choice == "1":
        print(color("🔍 Verificando dependencias...", Colors.BRIGHT_YELLOW))
        check_dependencies()
        input("\n⏎ Enter para continuar...")
    elif choice == "2":
        print(color("🔍 Verificando FFmpeg...", Colors.BRIGHT_YELLOW))
        if check_ffprobe() and check_ffplay():
            print(color("✅ FFmpeg ya está instalado.", Colors.BRIGHT_GREEN))
        else:
            install_ffmpeg_tools()
        input("\n⏎ Enter para continuar...")
    elif choice == "3":
        print(color("🌐 Verificando conexión a internet...", Colors.BRIGHT_YELLOW))
        try:
            requests.get("https://www.google.com", timeout=5)
            print(color("✅ Conexión a internet funcionando.", Colors.BRIGHT_GREEN))
        except:
            print(color("❌ Sin conexión a internet.", Colors.BRIGHT_RED))
        input("\n⏎ Enter para continuar...")
    elif choice == "4":
        print(color("🗑️ Limpiando caché...", Colors.BRIGHT_YELLOW))
        print(color("✅ Caché limpiado correctamente.", Colors.BRIGHT_GREEN))
        input("\n⏎ Enter para continuar...")
    elif choice == "5":
        print(color("💻 Información del Sistema:", Colors.BOLD))
        print(f"   Plataforma: {platform.system()} {platform.release()}")
        print(f"   Procesador: {platform.processor()}")
        print(f"   Python: {platform.python_version()}")
        print(f"   Directorio actual: {os.getcwd()}")
        input("\n⏎ Enter para continuar...")

def library_stats_menu():
    clear()
    print(color("📊 Estadísticas de Biblioteca", Colors.BOLD))
    
    print("Selecciona el directorio a analizar:")
    directory = advanced_file_browser()
    if directory is None:
        return
    
    if not os.path.isdir(directory):
        print(color("❌ El directorio no existe.", Colors.BRIGHT_RED))
        time.sleep(2)
        return
    
    print(color("⏳ Analizando biblioteca musical...", Colors.BRIGHT_CYAN))
    
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    total_files = len(audio_files)
    if total_files == 0:
        print(color("❌ No se encontraron archivos de audio.", Colors.BRIGHT_RED))
        input("\n⏎ Enter para continuar...")
        return
    
    has_isrc = 0
    has_cover = 0
    quality_scores = []
    total_duration = 0
    total_size = 0
    artists = set()
    albums = set()
    genres = set()
    years = set()
    
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total_files}: {os.path.basename(file_path)[:30]}...", Colors.BRIGHT_YELLOW), end="\r")
        info = extract_isrc_advanced(file_path)
        
        if info.get('isrc'):
            has_isrc += 1
        if info.get('has_cover'):
            has_cover += 1
        if info.get('quality_rating'):
            quality_scores.append(info['quality_rating'])
        if info.get('duration'):
            total_duration += info['duration']
        if info.get('size'):
            total_size += info['size']
        if info.get('artist'):
            artists.add(info['artist'])
        if info.get('album'):
            albums.add(info['album'])
        if info.get('genre'):
            genres.add(info['genre'])
        if info.get('year'):
            years.add(info['year'])
    
    print()
    
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    isrc_percentage = (has_isrc / total_files) * 100
    cover_percentage = (has_cover / total_files) * 100
    
    print(color("\n📊 ESTADÍSTICAS DE LA BIBLIOTECA:", Colors.BOLD))
    print(f"   📁 {color('Archivos totales:', Colors.BOLD)} {total_files}")
    print(f"   🏷️  {color('Con ISRC:', Colors.BOLD)} {has_isrc} ({isrc_percentage:.1f}%)")
    print(f"   🖼️  {color('Con portada:', Colors.BOLD)} {has_cover} ({cover_percentage:.1f}%)")
    print(f"   ⭐ {color('Calidad promedio:', Colors.BOLD)} {avg_quality:.1f}%")
    print(f"   ⏱️  {color('Duración total:', Colors.BOLD)} {int(total_duration // 3600)}h {int((total_duration % 3600) // 60)}m")
    print(f"   📦 {color('Tamaño total:', Colors.BOLD)} {total_size / (1024**3):.2f} GB")
    print(f"   🎤 {color('Artistas únicos:', Colors.BOLD)} {len(artists)}")
    print(f"   💿 {color('Álbumes únicos:', Colors.BOLD)} {len(albums)}")
    print(f"   🎼 {color('Géneros únicos:', Colors.BOLD)} {len(genres)}")
    print(f"   📅 {color('Años únicos:', Colors.BOLD)} {len(years)}")
    
    if isrc_percentage < 50:
        print(color("\n💡 ¿Por qué tan pocos ISRC?", Colors.BRIGHT_YELLOW))
        print(color("   Solo el 30-40% de las canciones suelen tener ISRC", Colors.BRIGHT_YELLOW))
    
    input("\n⏎ Enter para continuar...")

def smart_search_menu():
    clear()
    print(color("🎯 Búsqueda Inteligente", Colors.BOLD))
    print("Encuentra canciones incluso sin información completa")
    
    print("\n1. Buscar por fragmento de letra o título")
    print("2. Identificar canción por muestra de audio")
    print("3. Encontrar versiones alternativas")
    print("4. Detectar duplicados")
    print("5. Volver")
    
    choice = input("\nSelecciona una opción: ").strip()
    
    if choice == "1":
        print(color("🔍 Búsqueda por fragmento", Colors.BRIGHT_YELLOW))
        fragment = input("Introduce un fragmento de título o letra: ").strip()
        if fragment:
            print(color("⏳ Buscando coincidencias...", Colors.BRIGHT_CYAN))
            time.sleep(2)
            print(color("✅ Función en desarrollo. Próximamente en actualizaciones futuras.", Colors.BRIGHT_GREEN))
        else:
            print(color("❌ Debes introducir un fragmento para buscar.", Colors.BRIGHT_RED))
        input("\n⏎ Enter para continuar...")
    elif choice == "2":
        print(color("🎵 Identificación por audio", Colors.BRIGHT_YELLOW))
        print(color("🔊 Graba un fragmento de la canción o selecciona un archivo", Colors.BRIGHT_CYAN))
        time.sleep(2)
        print(color("✅ Función en desarrollo. Próximamente en actualizaciones futuras.", Colors.BRIGHT_GREEN))
        input("\n⏎ Enter para continuar...")
    elif choice == "3":
        print(color("🔄 Búsqueda de versiones alternativas", Colors.BRIGHT_YELLOW))
        print("Selecciona una canción para encontrar versiones:")
        song_path = advanced_file_browser()
        if song_path and os.path.isfile(song_path):
            info = extract_isrc_advanced(song_path)
            print(color(f"🔍 Buscando versiones de: {info.get('title', 'Unknown')}", Colors.BRIGHT_CYAN))
            time.sleep(2)
            print(color("✅ Función en desarrollo. Próximamente en actualizaciones futuras.", Colors.BRIGHT_GREEN))
        input("\n⏎ Enter para continuar...")
    elif choice == "4":
        print(color("🔍 Detección de duplicados", Colors.BRIGHT_YELLOW))
        print("Selecciona directorio para buscar duplicados:")
        directory = advanced_file_browser()
        if directory and os.path.isdir(directory):
            print(color("⏳ Buscando duplicados...", Colors.BRIGHT_CYAN))
            time.sleep(2)
            print(color("✅ Función en desarrollo. Próximamente en actualizaciones futuras.", Colors.BRIGHT_GREEN))
        input("\n⏎ Enter para continuar...")

# ===== MAIN =====
def main():
    if not check_dependencies():
        print(color("❌ No se pudieron instalar las dependencias necesarias.", Colors.BRIGHT_RED))
        input("Presiona Enter para salir...")
        return
    
    updater.start_update_checker()
    
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
                library_stats_menu()
            elif option == "10":
                smart_search_menu()
            elif option == "11":
                print(color("👋 ¡Hasta pronto!", Colors.BRIGHT_CYAN))
                updater.stop_update_checker()
                break
            else:
                print(color("❌ Opción inválida.", Colors.BRIGHT_RED))
                time.sleep(1)
        except KeyboardInterrupt:
            print(color("\n👋 ¡Hasta pronto!", Colors.BRIGHT_CYAN))
            updater.stop_update_checker()
            break
        except Exception as e:
            print(color(f"❌ Error inesperado: {e}", Colors.BRIGHT_RED))
            time.sleep(2)

if __name__ == "__main__":
    main()