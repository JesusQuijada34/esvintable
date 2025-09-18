#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# esVintable Lite - Multiplataforma (versión extendida con más funciones y API restaurada)
# Autor original: @JesusQuijada34 | GitHub.com/JesusQuijada34/esvintable

import os
import sys
import platform
import subprocess
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from threading import Thread, Event
import cloudscraper
from mutagen.id3 import ID3, error as ID3error
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

# ===== CONFIGURACIÓN GLOBAL =====
REPO_RAW_URL = "https://raw.githubusercontent.com/JesusQuijada34/esvintable/main/"
SCRIPT_FILENAME = "esvintable_lite.py"
DETAILS_XML_URL = f"{REPO_RAW_URL}details.xml"
LOCAL_XML_FILE = "details.xml"
UPDATE_INTERVAL = 10

# ⚠️ Token API restaurado (mantener seguro, no compartir públicamente)
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOiJhcGlfZXN2aW50YWJsZSJ9.VM4mKjhrUguvQ0l6wHgFfW6v6m8yF_8jO3wT6jLxQwo"

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

SUPPORTED_AUDIO = ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma')

# ===== COLORES =====
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


def color(text, color_code):
    return f"{color_code}{text}{Colors.END}"


def clear():
    os.system('cls' if IS_WINDOWS else 'clear')

# ===== SISTEMA DE ACTUALIZACIÓN =====
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
        self.load_local_version()

    def load_local_version(self):
        try:
            if os.path.exists(LOCAL_XML_FILE):
                tree = ET.parse(LOCAL_XML_FILE)
                root = tree.getroot()
                version_element = root.find('version')
                if version_element is not None:
                    self.local_version = version_element.text.strip()
                    return True
        except:
            pass
        self.local_version = "0.0"
        return False

    def get_remote_info_from_xml(self):
        try:
            response = requests.get(DETAILS_XML_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                info = {}
                info['version'] = root.find('version').text.strip() if root.find('version') is not None else self.local_version
                info['changelog'] = root.find('changelog').text.strip() if root.find('changelog') is not None else ""
                return info
        except:
            return None

    def compare_versions(self, local_ver, remote_ver):
        try:
            local_parts = tuple(map(int, local_ver.split('.')))
            remote_parts = tuple(map(int, remote_ver.split('.')))
            return remote_parts > local_parts
        except:
            return remote_ver > local_ver

    def check_for_updates(self, silent=False):
        try:
            self.update_info = self.get_remote_info_from_xml()
            if self.update_info and 'version' in self.update_info:
                self.remote_version = self.update_info['version']
                if self.compare_versions(self.local_version, self.remote_version):
                    self.update_available = True
                    self.new_version = self.remote_version
                    if not silent and not self.notification_shown:
                        print(color(f"\n*** Nueva versión disponible: {self.new_version} ***", Colors.BRIGHT_GREEN))
                        self.notification_shown = True
                    return True
        except:
            if not silent:
                print(color("Error al verificar actualizaciones", Colors.RED))
        return False

    def start_update_checker(self):
        def checker_thread():
            while self.running:
                current_time = datetime.now()
                if (current_time - self.last_check).total_seconds() >= UPDATE_INTERVAL:
                    self.check_for_updates(silent=True)
                    self.last_check = current_time
                time.sleep(2)
        Thread(target=checker_thread, daemon=True).start()

    def stop_update_checker(self):
        self.running = False

updater = UpdateChecker()

# ===== DEPENDENCIAS =====
def check_dependencies():
    missing = []
    for dep in ["requests", "cloudscraper", "mutagen"]:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if missing:
        print(color("Instalando dependencias...", Colors.YELLOW))
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing)
    return True

# ===== FUNCIONES DE AUDIO =====
def extract_isrc(file_path):
    result = {'file': file_path, 'filename': os.path.basename(file_path), 'isrc': None, 'artist': None, 'title': None}
    try:
        audiofile = None
        if file_path.lower().endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                try:
                    audiofile = ID3(file_path)
                except:
                    pass
        elif file_path.lower().endswith('.flac'):
            audiofile = FLAC(file_path)
        elif file_path.lower().endswith(('.m4a', '.mp4')):
            audiofile = MP4(file_path)
        if audiofile:
            if 'isrc' in audiofile:
                val = audiofile['isrc'][0] if isinstance(audiofile['isrc'], list) else str(audiofile['isrc'])
                result['isrc'] = val.strip().upper()
            if 'artist' in audiofile:
                result['artist'] = audiofile['artist'][0] if isinstance(audiofile['artist'], list) else str(audiofile['artist'])
            if 'title' in audiofile:
                result['title'] = audiofile['title'][0] if isinstance(audiofile['title'], list) else str(audiofile['title'])
    except Exception as e:
        result['error'] = str(e)
    return result


def display_file_info(info):
    isrc_text = info.get('isrc', 'No encontrado')
    isrc_color = Colors.BRIGHT_GREEN if info.get('isrc') else Colors.BRIGHT_RED
    print(color(f"Archivo: {info['filename']}", Colors.CYAN))
    print(f"   ISRC: {color(isrc_text, isrc_color)}")
    print(f"   Artista: {info.get('artist', 'Desconocido')}")
    print(f"   Título: {info.get('title', 'Desconocido')}")

# ===== FUNCIONALIDADES EXTRA =====
def list_audio_files(directory):
    print(color(f"Archivos de audio en {directory}:", Colors.BRIGHT_BLUE))
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                print(" -", file)

def search_isrc_in_directory(directory):
    print(color(f"Buscando ISRC en {directory}", Colors.BRIGHT_CYAN))
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                path = os.path.join(root, file)
                info = extract_isrc(path)
                if info['isrc']:
                    display_file_info(info)


def download_by_isrc(isrc, output_dir="descargas_isrc"):
    scraper = cloudscraper.create_scraper()
    print(color(f"Buscando ISRC: {isrc}", Colors.BRIGHT_CYAN))
    os.makedirs(output_dir, exist_ok=True)
    for provider in PROVIDERS:
        try:
            url = f"https://mds.projectcarmen.com/stream/download?provider={provider}&isrc={isrc}"
            headers = {"Authorization": f"Bearer {TOKEN}"}
            response = scraper.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                filename = os.path.join(output_dir, f"{isrc}_{provider}.m4a")
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(color(f"Descargado: {filename}", Colors.BRIGHT_GREEN))
                return True
        except Exception as e:
            print(color(f"Error con {provider}: {str(e)}", Colors.YELLOW))
    return False

# ===== MENÚ PRINCIPAL =====
def print_banner():
    print(color("============================================", Colors.BRIGHT_BLUE))
    print(color(f" ESVINTABLE LITE v{updater.local_version}", Colors.BRIGHT_GREEN))
    print(color(f" Plataforma: {PLATFORM_LABEL}", Colors.BRIGHT_YELLOW))
    print(color("============================================", Colors.BRIGHT_BLUE))


def main_menu():
    print("1. Buscar ISRC en archivo")
    print("2. Buscar ISRC en directorio")
    print("3. Descargar por ISRC")
    print("4. Listar archivos de audio en un directorio")
    print("5. Verificar actualizaciones")
    print("6. Salir")
    return input("Opción: ").strip()


def main():
    if not check_dependencies():
        return
    updater.start_update_checker()
    updater.check_for_updates(silent=True)
    try:
        while True:
            clear()
            print_banner()
            choice = main_menu()
            if choice == "1":
                file_path = input("Ruta del archivo: ").strip()
                if os.path.isfile(file_path):
                    info = extract_isrc(file_path)
                    display_file_info(info)
                else:
                    print(color("Archivo no encontrado", Colors.RED))
                input("Enter para continuar...")
            elif choice == "2":
                directory = input("Directorio: ").strip()
                if os.path.isdir(directory):
                    search_isrc_in_directory(directory)
                else:
                    print(color("Directorio no válido", Colors.RED))
                input("Enter para continuar...")
            elif choice == "3":
                isrc = input("Código ISRC: ").strip().upper()
                download_by_isrc(isrc)
                input("Enter para continuar...")
            elif choice == "4":
                directory = input("Directorio: ").strip()
                if os.path.isdir(directory):
                    list_audio_files(directory)
                else:
                    print(color("Directorio no válido", Colors.RED))
                input("Enter para continuar...")
            elif choice == "5":
                updater.check_for_updates(silent=False)
                input("Enter para continuar...")
            elif choice == "6":
                print(color("Hasta pronto!", Colors.GREEN))
                updater.stop_update_checker()
                break
            else:
                print(color("Opción inválida", Colors.RED))
                time.sleep(1)
    except KeyboardInterrupt:
        print(color("\nHasta pronto!", Colors.GREEN))
        updater.stop_update_checker()

if __name__ == "__main__":
    main()
