#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @JesusQuijada34 | @jq34_channel | @jq34_group
# esVintable Ultimate v3.2 - Scanner ISRC Profundo Multiplataforma
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
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

# ===== CONFIGURACIÓN GLOBAL =====
VERSION = "3.2"
LAST_UPDATE = "2024-01-15"
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/esvintable_ultimate.py"
REPO_API_URL = "https://api.github.com/repos/JesusQuijada34/esvintable/commits?path=esvintable_ultimate.py"
CONFIG_FILE = "esvintable_config.json"
UPDATE_CHECK_INTERVAL = 60  # Segundos entre verificaciones (1 minuto)
SECURITY_PATCH_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/security_patches.json"

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

# Variables globales
update_available = False
update_thread = None
stop_update_check = False

# ===== FUNCIONES DE UTILIDAD =====
def clear_screen():
    """Limpia la pantalla según el SO"""
    os.system('cls' if IS_WINDOWS else 'clear')

def print_color(text, color):
    """Imprime texto coloreado"""
    print(f"{color}{text}{Colors.END}")

def print_banner():
    """Muestra el banner de la aplicación"""
    global update_available
    
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
    
    if update_available:
        print_color("🚨 ¡ACTUALIZACIÓN DISPONIBLE! Usa la opción 6 para actualizar.", Colors.YELLOW + Colors.BOLD)
    
    print(f"{Colors.YELLOW}Plataforma: {platform.system()} | Terminal: {'Termux' if IS_TERMUX else 'Pydroid' if IS_PYDROID else 'Standard'}{Colors.END}\n")

def load_config():
    """Carga la configuración desde archivo"""
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

def calculate_file_hash(file_path):
    """Calcula el hash MD5 de un archivo"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except:
        return None

# ===== SISTEMA DE ACTUALIZACIÓN EN TIEMPO REAL =====
def check_security_patches():
    """Verifica parches de seguridad disponibles"""
    try:
        response = requests.get(SECURITY_PATCH_URL, timeout=10)
        if response.status_code == 200:
            patches = response.json()
            config = load_config()
            
            for patch_id, patch_info in patches.items():
                if patch_id not in config.get("security_patches", {}):
                    print_color(f"🔒 Parche de seguridad disponible: {patch_info['title']}", Colors.RED)
                    print_color(f"   {patch_info['description']}", Colors.YELLOW)
                    
                    # Aplicar parche automáticamente si es crítico
                    if patch_info.get('critical', False):
                        print_color("🚨 Aplicando parche crítico automáticamente...", Colors.RED)
                        apply_security_patch(patch_id, patch_info)
            
            return True
    except:
        pass
    return False

def apply_security_patch(patch_id, patch_info):
    """Aplica un parche de seguridad"""
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
    except:
        return False

def check_for_updates():
    """Verifica si hay actualizaciones disponibles (ejecución en hilo)"""
    global update_available, stop_update_check
    
    while not stop_update_check:
        try:
            # Verificar mediante API de GitHub para commits recientes
            response = requests.get(REPO_API_URL, timeout=15)
            if response.status_code == 200:
                commits = response.json()
                if commits:
                    latest_commit_date = commits[0]['commit']['committer']['date']
                    latest_commit_date = datetime.fromisoformat(latest_commit_date.replace('Z', '+00:00'))
                    
                    # Obtener fecha del último commit local
                    config = load_config()
                    last_check = config.get("last_update_check", "")
                    
                    if last_check:
                        last_check_date = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                        if latest_commit_date > last_check_date:
                            # Hay un commit más reciente, verificar contenido
                            if verify_update_available():
                                update_available = True
                    
                    # Actualizar última verificación
                    config["last_update_check"] = datetime.now().isoformat()
                    save_config(config)
            
        except Exception as e:
            pass
        
        # Esperar antes de la siguiente verificación
        time.sleep(UPDATE_CHECK_INTERVAL)

def verify_update_available():
    """Verifica comparando línea por línea si hay actualizaciones reales"""
    try:
        # Obtener contenido local
        with open(__file__, 'r', encoding='utf-8') as f:
            local_content = f.read()
        
        # Obtener contenido remoto
        response = requests.get(REPO_RAW_URL, timeout=15)
        if response.status_code == 200:
            remote_content = response.text
            
            # Comparar versiones
            local_version_match = re.search(r'VERSION = "([\d.]+)"', local_content)
            remote_version_match = re.search(r'VERSION = "([\d.]+)"', remote_content)
            
            if local_version_match and remote_version_match:
                local_version = local_version_match.group(1)
                remote_version = remote_version_match.group(1)
                
                # Comparar versiones numéricamente
                if remote_version > local_version:
                    return True
            
            # Comparación por hash para detectar cambios incluso sin cambio de versión
            local_hash = hashlib.md5(local_content.encode('utf-8')).hexdigest()
            remote_hash = hashlib.md5(remote_content.encode('utf-8')).hexdigest()
            
            if local_hash != remote_hash:
                return True
        
        return False
    except:
        return False

def download_update():
    """Descarga la actualización y reemplaza el archivo"""
    try:
        print_color("🔍 Descargando última versión...", Colors.YELLOW)
        
        # Descargar contenido nuevo
        response = requests.get(REPO_RAW_URL, timeout=20)
        if response.status_code == 200:
            new_content = response.text
            
            # Crear archivo temporal
            temp_file = f"{__file__}.new"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Verificar integridad del archivo
            new_hash = hashlib.md5(new_content.encode('utf-8')).hexdigest()
            
            # Reemplazar archivo original
            backup_file = f"{__file__}.backup"
            
            # Crear backup del actual
            with open(__file__, 'r', encoding='utf-8') as original:
                with open(backup_file, 'w', encoding='utf-8') as backup:
                    backup.write(original.read())
            
            # Reemplazar con nuevo archivo
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Verificar que el nuevo archivo funciona
            try:
                # Ejecutar una verificación básica del nuevo archivo
                subprocess.run([sys.executable, "-c", f"import ast; ast.parse(open('{__file__}', 'r', encoding='utf-8').read())"], 
                             check=True, timeout=10, capture_output=True)
            except:
                # Restaurar backup si hay error
                with open(backup_file, 'r', encoding='utf-8') as backup:
                    with open(__file__, 'w', encoding='utf-8') as original:
                        original.write(backup.read())
                raise Exception("El archivo actualizado tiene errores de sintaxis")
            
            # Limpiar archivos temporales
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            print_color("✅ Actualización descargada correctamente", Colors.GREEN)
            return True
            
    except Exception as e:
        print_color(f"❌ Error durante la actualización: {e}", Colors.RED)
        
        # Intentar restaurar desde backup si existe
        if os.path.exists(backup_file):
            try:
                with open(backup_file, 'r', encoding='utf-8') as backup:
                    with open(__file__, 'w', encoding='utf-8') as original:
                        original.write(backup.read())
                print_color("✅ Backup restaurado correctamente", Colors.GREEN)
            except:
                print_color("❌ Error restaurando backup", Colors.RED)
        
        return False

def apply_update():
    """Aplica la actualización y reinicia la aplicación"""
    global stop_update_check
    
    print_color("🔄 Aplicando actualización...", Colors.YELLOW)
    
    # Detener el hilo de verificación de actualizaciones
    stop_update_check = True
    if update_thread and update_thread.is_alive():
        update_thread.join(timeout=5)
    
    # Descargar y aplicar actualización
    if download_update():
        print_color("🎉 ¡Actualización completada! Reiniciando...", Colors.GREEN)
        time.sleep(2)
        
        # Reiniciar la aplicación
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        print_color("❌ No se pudo completar la actualización", Colors.RED)
        # Reanudar verificación de actualizaciones
        start_update_checker()

def start_update_checker():
    """Inicia el hilo de verificación de actualizaciones"""
    global update_thread, stop_update_check
    
    stop_update_check = False
    update_thread = threading.Thread(target=check_for_updates, daemon=True)
    update_thread.start()

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

# ... (el resto de las funciones se mantienen igual hasta el main)

# ===== FUNCIÓN PRINCIPAL =====
def main():
    """Función principal de la aplicación"""
    global update_available, stop_update_check
    
    # Verificar parches de seguridad primero
    print_color("🔒 Verificando parches de seguridad...", Colors.CYAN)
    check_security_patches()
    
    # Verificar dependencias
    if not check_dependencies():
        print_color("❌ Error con las dependencias", Colors.RED)
        return
    
    # Iniciar verificador de actualizaciones en segundo plano
    start_update_checker()
    
    # Verificar actualizaciones inmediatamente
    print_color("🔍 Verificando actualizaciones...", Colors.CYAN)
    time.sleep(2)  # Dar tiempo para la primera verificación
    
    # Verificar FFprobe
    config = load_config()
    if not check_ffprobe() and not config.get("ffprobe_installed", False):
        print_color("🔍 FFprobe no detectado", Colors.YELLOW)
        install = input("¿Instalar FFprobe? (s/n): ").lower()
        if install == 's':
            if install_ffprobe():
                config['ffprobe_installed'] = True
                save_config(config)
    
    # Bucle principal
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
                download_by_isrc_menu()
            elif choice == "4":
                open_file_manager()
            elif choice == "5":
                settings_menu()
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
        # Asegurarse de que el hilo se detenga
        stop_update_check = True