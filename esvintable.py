#!/usr/bin/env python3
# @JesusQuijada34 | @jq34_channel | @jq34_group
# Console version - Trebel esVint.v2
# Multiplataforma con autoinstalación para Termux
# Remix from: @SiMijoSiManda | @simijosimethodleaks
# Github: github.com/JesusQuijada34/esvintable/

import sys
import os
import platform
import subprocess
import requests
import cloudscraper
import tempfile
import re
from urllib.parse import urlparse

# Detectar si estamos en Android/Termux
IS_TERMUX = "com.termux" in os.environ.get('PREFIX', '') or "TERMUX_VERSION" in os.environ
IS_ANDROID = "ANDROID_ROOT" in os.environ
IS_PYDROID = "ru.iiec.pydroid3" in os.environ.get('PREFIX', '')

PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

TREBEL_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"

# Variables globales
FFPROBE_AVAILABLE = False
MUTAGEN_AVAILABLE = False

def clear_screen():
    """Limpia la pantalla de manera compatible"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════╗
    ║             ESVINTABLE - Trebel esVint.v2        ║
    ║          Versión Multiplataforma                 ║
    ║      Con extracción de ISRC desde audio/URL      ║
    ╚══════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"Plataforma: {platform.system()}")
    if IS_TERMUX:
        print("Entorno: Termux (Android)")
    elif IS_PYDROID:
        print("Entorno: Pydroid (Android)")
    elif IS_ANDROID:
        print("Entorno: Android")
    print()

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
    ║ 5. Instalar dependencias                         ║
    ║ 6. Salir                                         ║
    ╚══════════════════════════════════════════════════╝
    """
    print(menu)

def check_dependencies():
    """Verifica las dependencias necesarias"""
    global FFPROBE_AVAILABLE, MUTAGEN_AVAILABLE
    
    # Verificar ffprobe/ffmpeg
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, text=True, timeout=5)
        FFPROBE_AVAILABLE = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        FFPROBE_AVAILABLE = False
    
    # Verificar mutagen
    try:
        import mutagen
        MUTAGEN_AVAILABLE = True
    except ImportError:
        MUTAGEN_AVAILABLE = False
    
    # Verificar otras dependencias
    deps_status = {
        'requests': False,
        'cloudscraper': False,
        'mutagen': MUTAGEN_AVAILABLE,
        'ffprobe': FFPROBE_AVAILABLE
    }
    
    try:
        import requests
        deps_status['requests'] = True
    except ImportError:
        pass
        
    try:
        import cloudscraper
        deps_status['cloudscraper'] = True
    except ImportError:
        pass
    
    return deps_status

def install_dependencies():
    """Instala las dependencias necesarias"""
    print("🔧 Instalando dependencias...")
    
    if IS_TERMUX:
        # Instalar en Termux
        try:
            # Actualizar e instalar paquetes
            subprocess.run(['pkg', 'update'], check=True)
            subprocess.run(['pkg', 'install', '-y', 'python', 'ffmpeg', 'git'], check=True)
            print("✅ Paquetes de sistema instalados")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando paquetes de sistema: {e}")
            return False
    
    # Instalar dependencias de Python
    pip_packages = ['requests', 'cloudscraper', 'mutagen']
    
    for package in pip_packages:
        try:
            print(f"📦 Instalando {package}...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', package], check=True)
            print(f"✅ {package} instalado correctamente")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando {package}: {e}")
            return False
    
    # Verificar instalación de ffprobe en Termux
    if IS_TERMUX and not check_dependencies()['ffprobe']:
        try:
            subprocess.run(['pkg', 'install', '-y', 'ffmpeg'], check=True)
            print("✅ FFmpeg instalado correctamente")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando FFmpeg: {e}")
    
    print("✅ Todas las dependencias instaladas correctamente")
    return True

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
                    log_callback(f"❌ Proveedor {provider}: {r.status_code}")
        except Exception as o:
            if log_callback:
                log_callback(f"🌐 Error de red para '{provider}': {o}")
    return False, None

def extract_isrc_from_file_ffprobe(file_path):
    """Extrae el ISRC de un archivo de audio usando ffprobe"""
    try:
        result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                               '-show_format', '-show_streams', file_path], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return None, f"❌ Error al analizar el archivo: {result.stderr}"
        
        # Buscar ISRC en los metadatos
        metadata = result.stdout
        isrc_match = re.search(r'"ISRC"\s*:\s*"([^"]+)"', metadata)
        if isrc_match:
            return isrc_match.group(1), None
        else:
            return None, "❌ No se encontró ISRC en los metadatos del archivo."
            
    except subprocess.TimeoutExpired:
        return None, "❌ Tiempo de espera agotado al analizar el archivo"
    except Exception as e:
        return None, f"❌ Error al extraer ISRC: {str(e)}"

def extract_isrc_from_file_mutagen(file_path):
    """Extrae el ISRC de un archivo de audio usando mutagen"""
    try:
        from mutagen import File
        
        audio = File(file_path)
        if audio is None:
            return None, "❌ No se pudo leer el archivo de audio"
        
        # Buscar ISRC en diferentes campos de metadatos
        isrc = None
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            # Diferentes estándares de metadata
            for field in ['ISRC', 'isrc', 'TSRC', 'tsrc']:
                if field in tags:
                    isrc = tags[field][0] if isinstance(tags[field], list) else tags[field]
                    break
        
        if isrc:
            return isrc, None
        else:
            return None, "❌ No se encontró ISRC en los metadatos del archivo."
            
    except Exception as e:
        return None, f"❌ Error al extraer ISRC: {str(e)}"

def extract_isrc_from_file(file_path):
    """Extrae ISRC usando el método disponible"""
    deps = check_dependencies()
    
    if deps['ffprobe']:
        return extract_isrc_from_file_ffprobe(file_path)
    elif deps['mutagen']:
        return extract_isrc_from_file_mutagen(file_path)
    else:
        return None, "❌ No hay métodos disponibles para extraer metadatos. Ejecuta 'Instalar dependencias'."

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

def get_user_choice():
    """Obtiene la elección del usuario"""
    while True:
        try:
            choice = input("\nSelecciona una opción (1-6): ").strip()
            if choice in ['1', '2', '3', '4', '5', '6']:
                return choice
            else:
                print("❌ Opción no válida. Por favor, elige entre 1 y 6.")
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)

def get_output_directory():
    """Solicita al usuario el directorio de salida"""
    default_dir = "descargas"
    print(f"\n📁 Directorio de salida (presiona Enter para usar '{default_dir}'):")
    output_dir = input().strip()
    return output_dir if output_dir else default_dir

def press_enter_to_continue():
    """Espera a que el usuario presione Enter"""
    input("\n⏎ Presiona Enter para continuar...")

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

def install_dependencies_menu():
    """Menú para instalar dependencias"""
    clear_screen()
    print_banner()
    print("🔧 INSTALAR DEPENDENCIAS\n")
    
    deps = check_dependencies()
    print("Estado de dependencias:")
    for dep, status in deps.items():
        print(f"  {dep}: {'✅' if status else '❌'}")
    
    print("\n¿Quieres instalar las dependencias faltantes? (s/n): ")
    choice = input().strip().lower()
    
    if choice in ['s', 'si', 'sí', 'y', 'yes']:
        if install_dependencies():
            print("✅ Instalación completada correctamente")
        else:
            print("❌ Hubo errores durante la instalación")
    else:
        print("❌ Instalación cancelada")
    
    press_enter_to_continue()

def main():
    """Función principal con menú interactivo"""
    # Verificar dependencias al inicio
    deps = check_dependencies()
    missing_deps = [dep for dep, status in deps.items() if not status]
    
    if missing_deps:
        print("⚠️  Advertencia: Faltan algunas dependencias:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("Puedes instalarlas desde la opción 5 del menú\n")
        press_enter_to_continue()
    
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
                install_dependencies_menu()
            elif choice == '6':
                print("\n👋 ¡Hasta luego!")
                break
                
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
            press_enter_to_continue()

if __name__ == "__main__":
    # Verificar si estamos en Termux y mostrar instrucciones
    if IS_TERMUX:
        print("✅ Detectado entorno Termux")
    
    main()