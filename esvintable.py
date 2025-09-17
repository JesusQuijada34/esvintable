#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @JesusQuijada34 | @jq34_channel | @jq34_group
# esVintable Ultimate v3.1 - Scanner ISRC Profundo Multiplataforma
# GitHub: github.com/JesusQuijada34/esvintable/
# Última actualización: 2024-01-15

import os
import sys
import re
import time
import json
import requests
import platform
import subprocess
import tempfile
import cloudscraper
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# ===== CONFIGURACIÓN GLOBAL =====
VERSION = "3.1"
LAST_UPDATE = "2024-01-15"
REPO_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/esvintable_ultimate.py"
CONFIG_FILE = "esvintable_config.json"
UPDATE_FLAG_FILE = ".update_available"

# Colores ANSI para terminal
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

# Detección de plataforma
IS_TERMUX = "com.termux" in os.environ.get('PREFIX', '')
IS_ANDROID = "ANDROID_ROOT" in os.environ
IS_PYDROID = "ru.iiec.pydroid3" in os.environ.get('PREFIX', '')
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

# Proveedores de música
PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"

# ===== FUNCIONES DE UTILIDAD =====
def clear_screen():
    """Limpia la pantalla según el SO"""
    os.system('cls' if IS_WINDOWS else 'clear')

def print_color(text, color):
    """Imprime texto coloreado"""
    print(f"{color}{text}{Colors.END}")

def print_banner():
    """Muestra el banner de la aplicación"""
    banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                   🎵 esVintable Ultimate v{VERSION}            ║
║                 Scanner ISRC Profesional                     ║
║                 GitHub.com/JesusQuijada34                    ║
║                 Última actualización: {LAST_UPDATE}           ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}"""
    print(banner)
    print(f"{Colors.YELLOW}Plataforma: {platform.system()} | Terminal: {'Termux' if IS_TERMUX else 'Pydroid' if IS_PYDROID else 'Standard'}{Colors.END}\n")

def load_config():
    """Carga la configuración desde archivo"""
    config = {
        "last_check": "",
        "auto_update": True,
        "deep_scan": True,
        "color_mode": True,
        "download_path": "descargas_isrc",
        "ffprobe_installed": False
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
        except:
            pass
    
    return config

def save_config(config):
    """Guarda la configuración en archivo"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except:
        pass

def check_dependencies():
    """Verifica e instala dependencias automáticamente"""
    missing_deps = []
    
    for dep in ["requests", "cloudscraper", "mutagen"]:
        try:
            __import__(dep)
        except ImportError:
            missing_deps.append(dep)
    
    if missing_deps:
        print_color("⚠️  Instalando dependencias faltantes...", Colors.YELLOW)
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing_deps, 
                         check=True, capture_output=True)
            print_color("✅ Dependencias instaladas correctamente", Colors.GREEN)
            return True
        except:
            print_color("❌ Error instalando dependencias", Colors.RED)
            return False
    
    return True

def check_ffprobe():
    """Verifica si ffprobe está disponible"""
    try:
        result = subprocess.run(['ffprobe', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def install_ffprobe():
    """Instala ffprobe según la plataforma"""
    print_color("🔧 Instalando FFprobe...", Colors.YELLOW)
    
    try:
        if IS_TERMUX or IS_PYDROID:
            subprocess.run(['pkg', 'install', 'ffmpeg', '-y'], check=True, 
                          capture_output=True, timeout=300)
        elif IS_LINUX:
            if subprocess.run(['which', 'apt-get'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'apt-get', 'install', 'ffmpeg', '-y'], 
                              check=True, timeout=300)
            elif subprocess.run(['which', 'yum'], capture_output=True).returncode == 0:
                subprocess.run(['sudo', 'yum', 'install', 'ffmpeg', '-y'], 
                              check=True, timeout=300)
        elif IS_MAC:
            subprocess.run(['brew', 'install', 'ffmpeg'], check=True, timeout=300)
        
        # Actualizar configuración
        config = load_config()
        config["ffprobe_installed"] = True
        save_config(config)
        
        print_color("✅ FFprobe instalado correctamente", Colors.GREEN)
        return True
    except subprocess.TimeoutExpired:
        print_color("❌ Tiempo de espera agotado instalando FFprobe", Colors.RED)
        return False
    except:
        print_color("❌ Error instalando FFprobe", Colors.RED)
        return False

# ===== SISTEMA DE ACTUALIZACIÓN MEJORADO =====
def check_updates(silent=False):
    """Verifica si hay actualizaciones disponibles"""
    config = load_config()
    
    # Verificar solo una vez al día
    if config["last_check"] == datetime.now().strftime("%Y-%m-%d") and os.path.exists(UPDATE_FLAG_FILE):
        if not silent:
            print_color("✅ Ya tienes la versión más reciente", Colors.GREEN)
        return False
    
    if not silent:
        print_color("🔍 Buscando actualizaciones...", Colors.CYAN)
    
    try:
        response = requests.get(REPO_URL, timeout=15)
        if response.status_code == 200:
            remote_content = response.text
            
            # Leer contenido local
            with open(__file__, 'r', encoding='utf-8') as f:
                local_content = f.read()
            
            # Comparar versiones
            local_version = re.search(r'VERSION = "([\d.]+)"', local_content)
            remote_version = re.search(r'VERSION = "([\d.]+)"', remote_content)
            
            if local_version and remote_version:
                if remote_version.group(1) > local_version.group(1):
                    # Guardar flag de actualización disponible
                    with open(UPDATE_FLAG_FILE, 'w') as f:
                        f.write(remote_version.group(1))
                    
                    if not silent:
                        print_color(f"🎉 ¡Nueva versión disponible! {local_version.group(1)} → {remote_version.group(1)}", Colors.GREEN)
                    return True
                else:
                    # Crear archivo vacío para indicar que ya está actualizado
                    open(UPDATE_FLAG_FILE, 'w').close()
            
        # Actualizar última verificación
        config["last_check"] = datetime.now().strftime("%Y-%m-%d")
        save_config(config)
        
    except Exception as e:
        if not silent:
            print_color(f"❌ Error buscando actualizaciones: {e}", Colors.RED)
    
    return False

def update_script():
    """Actualiza el script automáticamente"""
    print_color("🔄 Actualizando esVintable...", Colors.YELLOW)
    
    try:
        response = requests.get(REPO_URL, timeout=20)
        if response.status_code == 200:
            backup_file = f"{__file__}.backup"
            
            # Crear backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                with open(__file__, 'r', encoding='utf-8') as original:
                    f.write(original.read())
            
            # Escribir nueva versión
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Eliminar flag de actualización
            if os.path.exists(UPDATE_FLAG_FILE):
                os.remove(UPDATE_FLAG_FILE)
            
            print_color("✅ ¡Actualización completada!", Colors.GREEN)
            print_color("🔄 Reiniciando aplicación...", Colors.CYAN)
            time.sleep(2)
            
            # Reiniciar el script
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            print_color("❌ Error descargando actualización", Colors.RED)
    except Exception as e:
        print_color(f"❌ Error durante la actualización: {e}", Colors.RED)
        # Restaurar backup si existe
        backup_file = f"{__file__}.backup"
        if os.path.exists(backup_file):
            with open(backup_file, 'r', encoding='utf-8') as f:
                with open(__file__, 'w', encoding='utf-8') as original:
                    original.write(f.read())
            os.remove(backup_file)

# ===== FUNCIONES DE ESCANEO PROFUNDO =====
def deep_scan_isrc(file_path):
    """Escaneo profundo para encontrar ISRC"""
    results = []
    
    # Método 1: FFprobe (metadatos estándar)
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
        except:
            pass
    
    # Método 2: Mutagen (metadatos alternativo)
    try:
        from mutagen import File
        audio = File(file_path)
        if audio and hasattr(audio, 'tags') and audio.tags:
            for tag in ['ISRC', 'isrc', 'TSRC']:
                if tag in audio.tags:
                    isrc_value = audio.tags[tag][0] if isinstance(audio.tags[tag], list) else audio.tags[tag]
                    results.append((f"Mutagen {tag}", isrc_value))
                    break
    except:
        pass
    
    # Método 3: Análisis hexadecimal (búsqueda profunda)
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
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, bytes):
                    match = match.decode('utf-8', errors='ignore')
                # Validar formato ISRC
                if re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', match):
                    results.append(("Análisis Hexadecimal", match))
    except:
        pass
    
    return results

def scan_directory(directory, recursive=True):
    """Escanea un directorio en busca de archivos de audio"""
    audio_extensions = ['.mp3', '.m4a', '.wav', '.flac', '.aac', '.ogg', '.wma']
    audio_files = []
    
    try:
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in audio_extensions):
                        audio_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if any(file.lower().endswith(ext) for ext in audio_extensions):
                    audio_files.append(os.path.join(directory, file))
    except:
        pass
    
    return audio_files

# ===== FUNCIONES PRINCIPALES =====
def open_file_manager():
    """Abre el gestor de archivos según la plataforma"""
    try:
        current_dir = os.getcwd()
        
        if IS_TERMUX:
            # Usar termux-open con el directorio actual
            subprocess.run(['termux-open', current_dir], check=True, timeout=10)
        elif IS_PYDROID:
            # Pydroid puede usar xdg-open
            subprocess.run(['xdg-open', current_dir], check=True, timeout=10)
        elif IS_WINDOWS:
            os.startfile(current_dir)
        elif IS_LINUX:
            subprocess.run(['xdg-open', current_dir], check=True, timeout=10)
        elif IS_MAC:
            subprocess.run(['open', current_dir], check=True, timeout=10)
        
        print_color("📁 Gestor de archivos abierto", Colors.GREEN)
        return True
    except subprocess.TimeoutExpired:
        print_color("⏰ Tiempo de espera agotado abriendo gestor", Colors.YELLOW)
        return True
    except Exception as e:
        print_color(f"❌ No se pudo abrir el gestor de archivos: {e}", Colors.RED)
        return False

def get_country_code():
    """Obtiene el código de país"""
    try:
        response = requests.get('https://ipinfo.io/json', timeout=10)
        return response.json().get('country', '')
    except:
        return ''

def download_isrc(isrc, output_dir):
    """Descarga el archivo por ISRC"""
    scraper = cloudscraper.create_scraper()
    
    for provider in PROVIDERS:
        try:
            url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            
            print_color(f"🔍 Probando {provider}...", Colors.CYAN)
            response = scraper.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.join(output_dir, f"{isrc}.m4a")
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                print_color(f"✅ Descargado: {filename}", Colors.GREEN)
                return True, filename
                
        except Exception as e:
            continue
    
    return False, None

# ===== INTERFAZ DE USUARIO =====
def show_main_menu():
    """Muestra el menú principal"""
    # Verificar si hay actualizaciones disponibles
    update_available = os.path.exists(UPDATE_FLAG_FILE)
    
    menu = f"""
{Colors.BOLD}🎵 MENÚ PRINCIPAL{Colors.END}
{Colors.GREEN}1.{Colors.END} 🔍 Escanear archivo de audio
{Colors.GREEN}2.{Colors.END} 📁 Escanear directorio completo
{Colors.GREEN}3.{Colors.END} 🌐 Descargar por ISRC
{Colors.GREEN}4.{Colors.END} 📂 Abrir gestor de archivos
{Colors.GREEN}5.{Colors.END} ⚙️  Configuración
{Colors.GREEN}6.{Colors.END} 🔄 {'¡ACTUALIZAR!' if update_available else 'Verificar actualizaciones'}
{Colors.GREEN}7.{Colors.END} ❌ Salir
"""
    print(menu)
    choice = input(f"{Colors.YELLOW}👉 Selecciona una opción (1-7): {Colors.END}").strip()
    return choice

def scan_single_file():
    """Escanea un solo archivo"""
    print_color("\n📁 Escaneo de archivo individual", Colors.BOLD)
    file_path = input("Introduce la ruta del archivo: ").strip()
    
    if not os.path.exists(file_path):
        print_color("❌ El archivo no existe", Colors.RED)
        return
    
    print_color(f"🔍 Analizando: {file_path}", Colors.CYAN)
    results = deep_scan_isrc(file_path)
    
    if results:
        print_color("\n✅ ISRC ENCONTRADOS:", Colors.GREEN)
        for method, isrc in results:
            print_color(f"   {method}: {Colors.BOLD}{isrc}{Colors.END}", Colors.WHITE)
        
        # Preguntar si descargar
        download = input("\n¿Descargar archivo? (s/n): ").lower()
        if download == 's':
            config = load_config()
            success, filename = download_isrc(results[0][1], config["download_path"])
            if success:
                print_color(f"✅ Descarga completada: {filename}", Colors.GREEN)
    else:
        print_color("❌ No se encontraron ISRC en el archivo", Colors.RED)

def scan_directory_menu():
    """Escanea un directorio completo"""
    print_color("\n📁 Escaneo de directorio", Colors.BOLD)
    directory = input("Introduce la ruta del directorio: ").strip()
    
    if not os.path.isdir(directory):
        print_color("❌ El directorio no existe", Colors.RED)
        return
    
    print_color("🔍 Buscando archivos de audio...", Colors.CYAN)
    audio_files = scan_directory(directory)
    
    if not audio_files:
        print_color("❌ No se encontraron archivos de audio", Colors.RED)
        return
    
    print_color(f"✅ Encontrados {len(audio_files)} archivos de audio", Colors.GREEN)
    
    found_isrc = []
    for file_path in audio_files:
        results = deep_scan_isrc(file_path)
        if results:
            found_isrc.append((file_path, results[0][1]))
            print_color(f"   📄 {os.path.basename(file_path)}: {results[0][1]}", Colors.WHITE)
    
    if found_isrc:
        print_color(f"\n🎉 Se encontraron {len(found_isrc)} archivos con ISRC", Colors.GREEN)
    else:
        print_color("❌ No se encontraron archivos con ISRC", Colors.RED)

def download_by_isrc_menu():
    """Descarga por ISRC manual"""
    print_color("\n🌐 Descarga por ISRC", Colors.BOLD)
    isrc = input("Introduce el código ISRC: ").strip().upper()
    
    # Validar formato ISRC
    if not re.match(r'^[A-Z]{2}[A-Z0-9]{3}\d{5}$', isrc):
        print_color("❌ Formato ISRC inválido", Colors.RED)
        return
    
    config = load_config()
    print_color("🔍 Verificando ubicación...", Colors.CYAN)
    
    country = get_country_code()
    if country != "US":
        print_color("❌ Se requiere ubicación US. Usa VPN", Colors.RED)
        return
    
    print_color("✅ Ubicación verificada", Colors.GREEN)
    success, filename = download_isrc(isrc, config["download_path"])
    
    if success:
        print_color(f"✅ Descarga completada: {filename}", Colors.GREEN)
    else:
        print_color("❌ No se pudo descargar el archivo", Colors.RED)

def settings_menu():
    """Menú de configuración"""
    config = load_config()
    
    while True:
        print_color("\n⚙️ CONFIGURACIÓN", Colors.BOLD)
        print(f"1. Auto-actualización: {'✅' if config['auto_update'] else '❌'}")
        print(f"2. Escaneo profundo: {'✅' if config['deep_scan'] else '❌'}")
        print(f"3. Modo color: {'✅' if config['color_mode'] else '❌'}")
        print(f"4. Carpeta descargas: {config['download_path']}")
        print(f"5. FFprobe instalado: {'✅' if config.get('ffprobe_installed', False) else '❌'}")
        print("6. Instalar FFprobe")
        print("7. Volver al menú principal")
        
        choice = input("Selecciona opción (1-7): ").strip()
        
        if choice == "1":
            config['auto_update'] = not config['auto_update']
        elif choice == "2":
            config['deep_scan'] = not config['deep_scan']
        elif choice == "3":
            config['color_mode'] = not config['color_mode']
        elif choice == "4":
            new_path = input("Nueva carpeta de descargas: ").strip()
            if new_path:
                config['download_path'] = new_path
        elif choice == "5":
            # Solo mostrar estado
            pass
        elif choice == "6":
            if install_ffprobe():
                config['ffprobe_installed'] = True
        elif choice == "7":
            break
        else:
            print_color("❌ Opción inválida", Colors.RED)
        
        save_config(config)
        print_color("✅ Configuración guardada", Colors.GREEN)

# ===== FUNCIÓN PRINCIPAL =====
def main():
    """Función principal de la aplicación"""
    # Verificar y instalar dependencias
    if not check_dependencies():
        print_color("❌ Error con las dependencias", Colors.RED)
        return
    
    # Verificar actualizaciones al inicio
    config = load_config()
    if config["auto_update"] and check_updates(silent=True):
        print_color("🎉 ¡Actualización disponible! Usa la opción 6 para actualizar.", Colors.GREEN)
    
    # Verificar e instalar FFprobe si es necesario
    if not check_ffprobe() and not config.get("ffprobe_installed", False):
        print_color("🔍 FFprobe no detectado", Colors.YELLOW)
        install = input("¿Instalar FFprobe? (s/n): ").lower()
        if install == 's':
            if install_ffprobe():
                config['ffprobe_installed'] = True
                save_config(config)
    
    # Bucle principal
    while True:
        clear_screen()
        print_banner()
        
        choice = show_main_menu()
        
        if choice == "1":
            scan_single_file()
        elif choice == "2":
            scan_directory_menu()
        elif choice == "3":
            download_by_isrc_menu()
        elif choice == "4":
            open_file_manager()
        elif choice == "5":
            settings_menu()
        elif choice == "6":
            if os.path.exists(UPDATE_FLAG_FILE):
                update = input("¿Actualizar ahora? (s/n): ").lower()
                if update == 's':
                    update_script()
                    return
            else:
                if check_updates():
                    update = input("¿Actualizar ahora? (s/n): ").lower()
                    if update == 's':
                        update_script()
                        return
        elif choice == "7":
            print_color("👋 ¡Hasta pronto!", Colors.CYAN)
            break
        else:
            print_color("❌ Opción inválida", Colors.RED)
        
        input("\n⏎ Presiona Enter para continuar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\n👋 Interrupción por usuario", Colors.YELLOW)
    except Exception as e:
        print_color(f"❌ Error crítico: {e}", Colors.RED)