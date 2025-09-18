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
        print("000000. Salir del navegador")
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == "0":
            # Volver al directorio anterior
            current_path = os.path.dirname(current_path)
            selected_file = None
        elif choice == "00":
            # Seleccionar este directorio
            return current_path
        elif choice == "000":
            # Extraer ISRC del archivo seleccionado
            if selected_file:
                info = extract_isrc_advanced(selected_file, deep_scan=True)
                clear()
                print(color("🔍 ANÁLISIS EN PROFUNDIDAD:", Colors.BRIGHT_BLUE))
                display_audio_info(info, detailed=True)
                input("\nPresiona Enter para continuar...")
            else:
                print(color("❌ Primero selecciona un archivo", Colors.RED))
                time.sleep(1)
        elif choice == "0000":
            # Analizar archivo en profundidad
            if selected_file:
                info = extract_isrc_advanced(selected_file, deep_scan=True)
                clear()
                print(color("🔍 ANÁLISIS EN PROFUNDIDAD:", Colors.BRIGHT_BLUE))
                display_audio_info(info, detailed=True)
                input("\nPresiona Enter para continuar...")
            else:
                print(color("❌ Primero selecciona un archivo", Colors.RED))
                time.sleep(1)
        elif choice == "00000":
            # Buscar canciones similares
            if selected_file:
                info = extract_isrc_advanced(selected_file)
                similar = search_similar_songs(current_path, info)
                clear()
                print(color("🎵 CANCIONES SIMILARES ENCONTRADAS:", Colors.BRIGHT_BLUE))
                for song, similarity in similar[:10]:
                    print(f"   {color(f'{similarity}%', Colors.BRIGHT_GREEN)} - {song.get('title', 'Unknown')} - {song.get('artist', 'Unknown')}")
                input("\nPresiona Enter para continuar...")
            else:
                print(color("❌ Primero selecciona un archivo", Colors.RED))
                time.sleep(1)
        elif choice == "000000":
            # Salir
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
                    # Otros archivos
                    print(color("❌ Este archivo no es de audio", Colors.RED))
                    time.sleep(1)
            except ValueError:
                print(color("❌ Opción no válida", Colors.RED))
                time.sleep(1)

# ===== MENÚ PRINCIPAL =====
def show_menu():
    """Muestra el menú principal con opciones"""
    clear()
    print(color("╔══════════════════════════════════════════════════════════════╗", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("                   🎵 ESVINTABLE ULTIMATE PRO 🎵                   ", Colors.BG_BLUE + Colors.BRIGHT_YELLOW) + color("║", Colors.BRIGHT_BLUE))
    print(color("╠══════════════════════════════════════════════════════════════╣", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color(f"   Plataforma: {PLATFORM_LABEL:<20} v{updater.local_version:<10} ", Colors.BRIGHT_WHITE) + color("║", Colors.BRIGHT_BLUE))
    print(color("╠══════════════════════════════════════════════════════════════╣", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   1. Buscar ISRC en archivo individual                      ", Colors.BRIGHT_GREEN) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   2. Buscar ISRC en directorio                             ", Colors.BRIGHT_GREEN) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   3. Buscar ISRC en múltiples directorios                  ", Colors.BRIGHT_GREEN) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   4. Explorador de archivos avanzado                       ", Colors.BRIGHT_CYAN) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   5. Analizar calidad de metadatos                         ", Colors.BRIGHT_CYAN) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   6. Buscar canciones similares                            ", Colors.BRIGHT_CYAN) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   7. Verificar actualizaciones                             ", Colors.BRIGHT_YELLOW) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   8. Configuración                                         ", Colors.BRIGHT_YELLOW) + color("║", Colors.BRIGHT_BLUE))
    print(color("║", Colors.BRIGHT_BLUE) + color("   9. Salir                                                 ", Colors.BRIGHT_RED) + color("║", Colors.BRIGHT_BLUE))
    print(color("╚══════════════════════════════════════════════════════════════╝", Colors.BRIGHT_BLUE))
    
    if updater.update_available and not updater.notification_shown:
        print(color(f"   🔔 ¡Actualización disponible! v{updater.new_version} - Ejecuta opción 7", Colors.BRIGHT_GREEN))
    
    return input("\nSelecciona una opción: ").strip()

def main():
    """Función principal del programa"""
    # Verificar dependencias
    if not check_dependencies():
        print(color("❌ No se pudieron instalar las dependencias necesarias", Colors.RED))
        return
    
    # Verificar herramientas FFmpeg
    if not check_ffprobe():
        print(color("⚠️  FFprobe no está disponible. Algunas funciones estarán limitadas.", Colors.YELLOW))
        install_ffmpeg_tools()
    
    # Iniciar verificador de actualizaciones en segundo plano
    updater.start_update_checker()
    
    # Verificar actualizaciones al inicio
    updater.check_for_updates(silent=True)
    
    try:
        while True:
            choice = show_menu()
            
            if choice == "1":
                # Buscar ISRC en archivo individual
                file_path = input("Introduce la ruta del archivo: ").strip()
                if os.path.isfile(file_path):
                    info = extract_isrc_advanced(file_path, deep_scan=True)
                    clear()
                    display_audio_info(info, detailed=True)
                    input("\nPresiona Enter para continuar...")
                else:
                    print(color("❌ Archivo no encontrado", Colors.RED))
                    time.sleep(1)
            
            elif choice == "2":
                # Buscar ISRC en directorio
                directory = input("Introduce la ruta del directorio: ").strip()
                if os.path.isdir(directory):
                    process_directory(directory)
                else:
                    print(color("❌ Directorio no encontrado", Colors.RED))
                    time.sleep(1)
            
            elif choice == "3":
                # Buscar ISRC en múltiples directorios
                directories = input("Introduce las rutas separadas por coma: ").strip().split(',')
                for dir_path in directories:
                    dir_path = dir_path.strip()
                    if os.path.isdir(dir_path):
                        process_directory(dir_path)
                    else:
                        print(color(f"❌ Directorio no encontrado: {dir_path}", Colors.RED))
                        time.sleep(1)
            
            elif choice == "4":
                # Explorador de archivos avanzado
                start_dir = input("Directorio inicial (Enter para actual): ").strip()
                if not start_dir:
                    start_dir = "."
                selected_dir = advanced_file_browser(start_dir)
                if selected_dir:
                    print(color(f"📁 Directorio seleccionado: {selected_dir}", Colors.GREEN))
                    process_directory(selected_dir)
            
            elif choice == "5":
                # Analizar calidad de metadatos
                directory = input("Introduce la ruta del directorio: ").strip()
                if os.path.isdir(directory):
                    analyze_metadata_quality(directory)
                else:
                    print(color("❌ Directorio no encontrado", Colors.RED))
                    time.sleep(1)
            
            elif choice == "6":
                # Buscar canciones similares
                file_path = input("Introduce la ruta del archivo de referencia: ").strip()
                if os.path.isfile(file_path):
                    directory = input("Directorio donde buscar similares: ").strip()
                    if not directory:
                        directory = os.path.dirname(file_path)
                    
                    if os.path.isdir(directory):
                        ref_info = extract_isrc_advanced(file_path)
                        similar_songs = search_similar_songs(directory, ref_info)
                        
                        clear()
                        print(color("🎵 CANCIONES SIMILARES ENCONTRADAS:", Colors.BRIGHT_BLUE))
                        for song, similarity in similar_songs[:10]:
                            print(f"   {color(f'{similarity}%', Colors.BRIGHT_GREEN)} - {song.get('title', 'Unknown')} - {song.get('artist', 'Unknown')}")
                        input("\nPresiona Enter para continuar...")
                    else:
                        print(color("❌ Directorio no encontrado", Colors.RED))
                        time.sleep(1)
                else:
                    print(color("❌ Archivo no encontrado", Colors.RED))
                    time.sleep(1)
            
            elif choice == "7":
                # Verificar actualizaciones manualmente
                clear()
                print(color("🔍 Buscando actualizaciones...", Colors.YELLOW))
                if updater.check_for_updates(silent=False):
                    print(color("✅ ¡Estás al día!", Colors.GREEN))
                else:
                    print(color("❌ Error al verificar actualizaciones", Colors.RED))
                time.sleep(2)
            
            elif choice == "8":
                # Configuración
                show_settings()
            
            elif choice == "9":
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

def process_directory(directory):
    """Procesa un directorio buscando ISRC en archivos de audio"""
    print(color(f"🔍 Buscando archivos de audio en: {directory}", Colors.CYAN))
    
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    if not audio_files:
        print(color("❌ No se encontraron archivos de audio", Colors.RED))
        time.sleep(1)
        return
    
    print(color(f"📊 Encontrados {len(audio_files)} archivos de audio", Colors.GREEN))
    
    results = []
    total = len(audio_files)
    
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.YELLOW), end="\r")
        info = extract_isrc_advanced(file_path)
        results.append(info)
    
    print()
    
    # Mostrar resultados
    clear()
    print(color("📊 RESULTADOS DEL ANÁLISIS:", Colors.BRIGHT_BLUE))
    print(color("=" * 120, Colors.BRIGHT_CYAN))
    
    found_count = sum(1 for r in results if r['isrc'])
    print(color(f"📈 Archivos con ISRC: {found_count}/{total} ({found_count/total*100:.1f}%)", 
                Colors.BRIGHT_GREEN if found_count/total > 0.5 else Colors.BRIGHT_YELLOW))
    
    # Estadísticas de calidad
    quality_scores = [r['quality_rating'] for r in results]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    print(color(f"📊 Calidad promedio de metadatos: {avg_quality:.1f}%", 
                Colors.BRIGHT_GREEN if avg_quality > 60 else Colors.BRIGHT_YELLOW if avg_quality > 30 else Colors.BRIGHT_RED))
    
    print(color("=" * 120, Colors.BRIGHT_CYAN))
    
    # Mostrar detalles
    for i, result in enumerate(results, 1):
        isrc_color = Colors.BRIGHT_GREEN if result['isrc'] else Colors.BRIGHT_RED
        isrc_text = result['isrc'] or "No encontrado"
        
        print(f"{i:3d}. {result['filename'][:40]:40} | "
              f"ISRC: {color(isrc_text, isrc_color):15} | "
              f"Artista: {result.get('artist', '?')[:20]:20} | "
              f"Título: {result.get('title', '?')[:25]:25}")
    
    input("\nPresiona Enter para continuar...")

def analyze_metadata_quality(directory):
    """Analiza la calidad de los metadatos en un directorio"""
    print(color(f"📊 Analizando calidad de metadatos en: {directory}", Colors.CYAN))
    
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    if not audio_files:
        print(color("❌ No se encontraron archivos de audio", Colors.RED))
        time.sleep(1)
        return
    
    results = []
    total = len(audio_files)
    
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"   Analizando {i}/{total}: {os.path.basename(file_path)[:30]}...", Colors.YELLOW), end="\r")
        info = extract_isrc_advanced(file_path)
        results.append(info)
    
    print()
    
    # Calcular estadísticas
    quality_scores = [r['quality_rating'] for r in results]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    has_isrc = sum(1 for r in results if r['isrc'])
    has_title = sum(1 for r in results if r['title'])
    has_artist = sum(1 for r in results if r['artist'])
    has_album = sum(1 for r in results if r['album'])
    has_cover = sum(1 for r in results if r['has_cover'])
    
    clear()
    print(color("📊 ESTADÍSTICAS DE CALIDAD DE METADATOS:", Colors.BRIGHT_BLUE))
    print(color("=" * 80, Colors.BRIGHT_CYAN))
    print(f"📁 Directorio: {directory}")
    print(f"🎵 Archivos analizados: {total}")
    print(color("=" * 80, Colors.BRIGHT_CYAN))
    
    print(f"🏆 {color('Calidad promedio:', Colors.BOLD)} {color(f'{avg_quality:.1f}%', Colors.BRIGHT_GREEN if avg_quality > 60 else Colors.BRIGHT_YELLOW if avg_quality > 30 else Colors.BRIGHT_RED)}")
    print(f"📊 {color('Distribución por calidad:', Colors.BOLD)}")
    
    # Histograma de calidad
    quality_ranges = [(90, 100), (70, 89), (50, 69), (30, 49), (0, 29)]
    for min_q, max_q in quality_ranges:
        count = sum(1 for r in results if min_q <= r['quality_rating'] <= max_q)
        percentage = count / total * 100
        bar = "█" * int(percentage / 5)
        color_code = (
            Colors.BRIGHT_GREEN if min_q >= 70 else
            Colors.BRIGHT_YELLOW if min_q >= 50 else
            Colors.BRIGHT_RED
        )
        print(f"   {min_q:2d}-{max_q:2d}%: {bar:<20} {count:3d} ({percentage:5.1f}%) {color('█' * int(percentage/5), color_code)}")
    
    print(color("=" * 80, Colors.BRIGHT_CYAN))
    print(f"🏷️  {color('Metadatos específicos:', Colors.BOLD)}")
    print(f"   📍 ISRC: {has_isrc:3d} ({has_isrc/total*100:5.1f}%)")
    print(f"   🎵 Título: {has_title:3d} ({has_title/total*100:5.1f}%)")
    print(f"   🎤 Artista: {has_artist:3d} ({has_artist/total*100:5.1f}%)")
    print(f"   💿 Álbum: {has_album:3d} ({has_album/total*100:5.1f}%)")
    print(f"   🖼️  Portada: {has_cover:3d} ({has_cover/total*100:5.1f}%)")
    
    # Top 5 archivos con mejor calidad
    best_quality = sorted(results, key=lambda x: x['quality_rating'], reverse=True)[:5]
    print(color("=" * 80, Colors.BRIGHT_CYAN))
    print(f"🏅 {color('Top 5 - Mejor calidad:', Colors.BOLD)}")
    for i, item in enumerate(best_quality, 1):
        print(f"   {i}. {item['filename'][:30]:30} - {item['quality_rating']:3.0f}%")
    
    # Top 5 archivos con peor calidad
    worst_quality = sorted(results, key=lambda x: x['quality_rating'])[:5]
    print(color("=" * 80, Colors.BRIGHT_CYAN))
    print(f"🔻 {color('Top 5 - Peor calidad:', Colors.BOLD)}")
    for i, item in enumerate(worst_quality, 1):
        print(f"   {i}. {item['filename'][:30]:30} - {item['quality_rating']:3.0f}%")
    
    input("\nPresiona Enter para continuar...")

def show_settings():
    """Muestra el menú de configuración"""
    while True:
        clear()
        print(color("⚙️  CONFIGURACIÓN:", Colors.BRIGHT_BLUE))
        print(color("=" * 50, Colors.BRIGHT_CYAN))
        print("1. Ver información del sistema")
        print("2. Verificar herramientas FFmpeg")
        print("3. Instalar herramientas FFmpeg")
        print("4. Ver información de la versión")
        print("5. Volver al menú principal")
        print(color("=" * 50, Colors.BRIGHT_CYAN))
        
        choice = input("Selecciona una opción: ").strip()
        
        if choice == "1":
            clear()
            print(color("💻 INFORMACIÓN DEL SISTEMA:", Colors.BRIGHT_BLUE))
            print(color("=" * 50, Colors.BRIGHT_CYAN))
            print(f"Plataforma: {PLATFORM_LABEL}")
            print(f"Python: {platform.python_version()}")
            print(f"Sistema: {platform.system()} {platform.release()}")
            print(f"Procesador: {platform.processor()}")
            print(f"Directorio actual: {os.getcwd()}")
            input("\nPresiona Enter para continuar...")
        
        elif choice == "2":
            clear()
            print(color("🔧 ESTADO DE HERRAMIENTAS FFMPEG:", Colors.BRIGHT_BLUE))
            print(color("=" * 50, Colors.BRIGHT_CYAN))
            print(f"FFprobe: {'✅ Disponible' if check_ffprobe() else '❌ No disponible'}")
            print(f"FFplay: {'✅ Disponible' if check_ffplay() else '❌ No disponible'}")
            input("\nPresiona Enter para continuar...")
        
        elif choice == "3":
            install_ffmpeg_tools()
            input("\nPresiona Enter para continuar...")
        
        elif choice == "4":
            clear()
            print(color("📋 INFORMACIÓN DE VERSIÓN:", Colors.BRIGHT_BLUE))
            print(color("=" * 50, Colors.BRIGHT_CYAN))
            print(f"Versión actual: {updater.local_version}")
            if updater.update_info:
                if 'release_date' in updater.update_info:
                    print(f"Fecha de lanzamiento: {updater.update_info['release_date']}")
                if 'changelog' in updater.update_info:
                    print(f"Cambios: {updater.update_info['changelog'][:100]}...")
            input("\nPresiona Enter para continuar...")
        
        elif choice == "5":
            break
        
        else:
            print(color("❌ Opción no válida", Colors.RED))
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(color(f"❌ Error crítico: {e}", Colors.RED))
        import traceback
        traceback.print_exc()
        input("Presiona Enter para salir...")