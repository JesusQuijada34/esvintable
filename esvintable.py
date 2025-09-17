#!/usr/bin/env python3
# @JesusQuijada34 | @jq34_channel | @jq34_group
# Console version - Trebel esVint.v2
# Compatible with Android (Termux) and traditional consoles
# Remix from: @SiMijoSiManda | @simijosimethodleaks
# Github: github.com/JesusQuijada34/esvintable/

import sys
import os
import requests
import cloudscraper
import platform
import subprocess
import tempfile
import re
from urllib.parse import urlparse

PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

TREBEL_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"
)

def clear_screen():
    """Limpia la pantalla de manera compatible con múltiples plataformas"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║             ESVINTABLE - Trebel esVint.v2        ║
    ║          Versión Consola (Android compatible)    ║
    ║      Con extracción de ISRC desde audio/URL      ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)

def print_menu():
    """Muestra el menú principal"""
    menu = """
    ╔══════════════════════════════════════════════════╗
    ║                   MENÚ PRINCIPAL                 ║
    ╠══════════════════════════════════════════════════╣
    ║ 1. Descargar por ISRC                            ║
    ║ 2. Extraer ISRC desde archivo de audio           ║
    ║ 3. Extraer ISRC desde URL                        ║
    ║ 4. Verificar ubicación                           ║
    ║ 5. Salir                                         ║
    ╚══════════════════════════════════════════════════╝
    """
    print(menu)

def get_user_choice():
    """Obtiene la elección del usuario"""
    while True:
        try:
            choice = input("\nSelecciona una opción (1-5): ").strip()
            if choice in ['1', '2', '3', '4', '5']:
                return choice
            else:
                print("❌ Opción no válida. Por favor, elige entre 1 y 5.")
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)

def get_output_directory():
    """Solicita al usuario el directorio de salida"""
    default_dir = "op"
    print(f"\n📁 Directorio de salida (presiona Enter para usar '{default_dir}'):")
    output_dir = input().strip()
    return output_dir if output_dir else default_dir

def press_enter_to_continue():
    """Espera a que el usuario presione Enter"""
    input("\n⏎ Presiona Enter para continuar...")

def get_country_code():
    try:
        cIP = requests.get('https://ipinfo.io/json', timeout=5).json()
        return cIP.get('country', None)
    except Exception as e:
        return None

def download_isrc(isrc, output_dir, log_callback=None):
    s = cloudscraper.create_scraper()
    for provider in PROVIDERS:
        ep = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
        headers = {"Authorization": f"Bearer {TREBEL_TOKEN}"}
        if log_callback:
            log_callback(f"🔍 Solicitando API para {provider}...")
        try:
            r = s.get(ep, headers=headers, timeout=15)
            if r.status_code == 200:
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                fn = os.path.join(output_dir, f"{isrc}.m4a")
                with open(fn, "wb") as o:
                    o.write(r.content)
                if log_callback:
                    log_callback(f"💾 Archivo guardado como: {fn}\n")
                return True, fn
            else:
                if log_callback:
                    log_callback(f"❌ Proveedor {provider}: {r.status_code} - {r.text}")
        except requests.exceptions.RequestException as o:
            if log_callback:
                log_callback(f"🌐 Error de red para '{provider}': {o}")
    return False, None

def extract_isrc_from_file(file_path):
    """Extrae el ISRC de un archivo de audio usando ffprobe"""
    try:
        # Verificar si ffprobe está disponible
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True)
        if result.returncode != 0:
            return None, "❌ ffprobe no está instalado. Instala ffmpeg para extraer metadatos."
        
        # Ejecutar ffprobe para obtener metadatos
        cmd = [
            'ffprobe', 
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"❌ Error al analizar el archivo: {result.stderr}"
        
        # Buscar ISRC en los metadatos
        metadata = result.stdout
        isrc_match = re.search(r'"ISRC"\s*:\s*"([^"]+)"', metadata)
        if isrc_match:
            return isrc_match.group(1), None
        else:
            return None, "❌ No se encontró ISRC en los metadatos del archivo."
            
    except Exception as e:
        return None, f"❌ Error al extraer ISRC: {str(e)}"

def download_file_from_url(url, output_path):
    """Descarga un archivo desde una URL"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True, None
        else:
            return False, f"❌ Error HTTP {response.status_code}"
    except Exception as e:
        return False, f"❌ Error al descargar: {str(e)}"

def extract_isrc_from_url(url):
    """Extrae ISRC desde una URL descargando primero el archivo"""
    try:
        # Crear un archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.audio', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Descargar el archivo
        print(f"📥 Descargando archivo desde URL...")
        success, error = download_file_from_url(url, tmp_path)
        if not success:
            os.unlink(tmp_path)
            return None, error
        
        # Extraer ISRC
        print("🔍 Extrayendo ISRC del archivo...")
        isrc, error = extract_isrc_from_file(tmp_path)
        
        # Limpiar archivo temporal
        os.unlink(tmp_path)
        
        return isrc, error
        
    except Exception as e:
        return None, f"❌ Error al procesar URL: {str(e)}"

def verify_location():
    """Verifica la ubicación del usuario"""
    print("🌍 Verificando país...")
    country = get_country_code()
    
    if not country:
        print("❌ Error: No se pudo obtener el país. ¿Conexión a internet?")
        return False
    
    print(f"📍 País detectado: {country}")
    
    if country != "US":
        print("❌ Error: ¡Se requiere ubicación en US (Estados Unidos)!")
        print("🔒 Usa VPN o Proxy para cambiar tu ubicación a US")
        return False
    
    print("✅ Ubicación verificada correctamente (US)")
    return True

def download_by_isrc():
    """Función para descargar por ISRC directamente"""
    clear_screen()
    print_banner()
    print("⬇️  DESCARGA POR ISRC DIRECTAMENTE\n")
    
    isrc = input("Introduce el código ISRC: ").strip()
    if not isrc:
        print("❌ Debes introducir un código ISRC válido.")
        press_enter_to_continue()
        return
    
    output_dir = get_output_directory()
    
    if not verify_location():
        press_enter_to_continue()
        return
    
    print(f"\n🚀 Iniciando descarga para ISRC: {isrc}...")
    print(f"📁 Directorio de salida: {output_dir}")
    print("-" * 50)
    
    success, filename = download_isrc(isrc, output_dir, log_callback=print)
    
    if success:
        print("\n✅ ¡Descarga completada exitosamente!")
        print(f"💾 Archivo: {filename}")
        
        # En Android, mostrar la ruta completa
        is_android = "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ
        if is_android:
            full_path = os.path.abspath(filename)
            print(f"📂 Ruta completa: {full_path}")
    else:
        print("\n❌ Error: No se pudo descargar el archivo con ningún proveedor.")
    
    press_enter_to_continue()

def extract_from_file():
    """Función para extraer ISRC desde archivo"""
    clear_screen()
    print_banner()
    print("📁 EXTRAER ISRC DESDE ARCHIVO DE AUDIO\n")
    
    file_path = input("Introduce la ruta del archivo de audio: ").strip()
    if not file_path or not os.path.isfile(file_path):
        print("❌ La ruta del archivo no es válida o el archivo no existe.")
        press_enter_to_continue()
        return
    
    print(f"🔍 Extrayendo ISRC desde: {file_path}")
    isrc, error = extract_isrc_from_file(file_path)
    
    if isrc:
        print(f"\n✅ ISRC extraído: {isrc}")
        
        # Preguntar si quiere descargar
        download_choice = input("\n¿Quieres descargar este archivo? (s/n): ").strip().lower()
        if download_choice in ['s', 'si', 'sí', 'y', 'yes']:
            output_dir = get_output_directory()
            
            if verify_location():
                print(f"\n🚀 Iniciando descarga para ISRC: {isrc}...")
                success, filename = download_isrc(isrc, output_dir, log_callback=print)
                
                if success:
                    print("\n✅ ¡Descarga completada exitosamente!")
                    print(f"💾 Archivo: {filename}")
                else:
                    print("\n❌ Error: No se pudo descargar el archivo.")
    else:
        print(f"\n{error}")
    
    press_enter_to_continue()

def extract_from_url():
    """Función para extraer ISRC desde URL"""
    clear_screen()
    print_banner()
    print("🌐 EXTRAER ISRC DESDE URL\n")
    
    url = input("Introduce la URL del archivo de audio: ").strip()
    if not url or not url.startswith(('http://', 'https://')):
        print("❌ URL no válida. Debe comenzar con http:// o https://")
        press_enter_to_continue()
        return
    
    print(f"🔍 Extrayendo ISRC desde: {url}")
    isrc, error = extract_isrc_from_url(url)
    
    if isrc:
        print(f"\n✅ ISRC extraído: {isrc}")
        
        # Preguntar si quiere descargar
        download_choice = input("\n¿Quieres descargar este archivo? (s/n): ").strip().lower()
        if download_choice in ['s', 'si', 'sí', 'y', 'yes']:
            output_dir = get_output_directory()
            
            if verify_location():
                print(f"\n🚀 Iniciando descarga para ISRC: {isrc}...")
                success, filename = download_isrc(isrc, output_dir, log_callback=print)
                
                if success:
                    print("\n✅ ¡Descarga completada exitosamente!")
                    print(f"💾 Archivo: {filename}")
                else:
                    print("\n❌ Error: No se pudo descargar el archivo.")
    else:
        print(f"\n{error}")
    
    press_enter_to_continue()

def check_location():
    """Función para verificar ubicación"""
    clear_screen()
    print_banner()
    print("🌍 VERIFICAR UBICACIÓN\n")
    
    verify_location()
    press_enter_to_continue()

def main():
    """Función principal con menú interactivo"""
    while True:
        try:
            clear_screen()
            print_banner()
            print_menu()
            
            choice = get_user_choice()
            
            if choice == '1':
                download_by_isrc()
            elif choice == '2':
                extract_from_file()
            elif choice == '3':
                extract_from_url()
            elif choice == '4':
                check_location()
            elif choice == '5':
                print("\n👋 ¡Hasta luego!")
                break
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
            press_enter_to_continue()

if __name__ == "__main__":
    # Verificar si estamos en Android
    is_android = "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ
    if is_android:
        print("✅ Detectado entorno Android (Termux)")
    
    main()