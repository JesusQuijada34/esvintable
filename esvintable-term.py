#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esVintable Terminal - Versión Mejorada de Terminal
Herramienta avanzada para extraer metadatos de archivos de audio
Autor: @JesusQuijada34 | Mejoras: @MkelCT
"""

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
import json
import hashlib

# ===== COLORES ANSI MEJORADOS =====
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    BRIGHT_RED = '\033[38;5;196m'
    BRIGHT_GREEN = '\033[38;5;46m'
    BRIGHT_YELLOW = '\033[38;5;226m'
    BRIGHT_BLUE = '\033[38;5;21m'
    BRIGHT_CYAN = '\033[38;5;87m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'

def color(text, color_code):
    return f"{color_code}{text}{Colors.END}"

def clear():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def print_header():
    """Imprime el encabezado de la aplicación"""
    clear()
    header = f"""
    {color('╔════════════════════════════════════════════════════════════╗', Colors.CYAN)}
    {color('║', Colors.CYAN)}  {color('🎵 esVintable - Audio Metadata Explorer', Colors.BRIGHT_CYAN)} {color('║', Colors.CYAN)}
    {color('║', Colors.CYAN)}  {color('Versión Mejorada de Terminal', Colors.BRIGHT_YELLOW)}                  {color('║', Colors.CYAN)}
    {color('╚════════════════════════════════════════════════════════════╝', Colors.CYAN)}
    """
    print(header)

def print_menu():
    """Imprime el menú principal mejorado"""
    menu = f"""
    {color('┌─ MENÚ PRINCIPAL ─────────────────────────────────────────┐', Colors.BLUE)}
    {color('│', Colors.BLUE)} {color('1', Colors.BRIGHT_GREEN)} - Extraer metadatos de archivo
    {color('│', Colors.BLUE)} {color('2', Colors.BRIGHT_GREEN)} - Extraer ISRC de archivo
    {color('│', Colors.BLUE)} {color('3', Colors.BRIGHT_GREEN)} - Buscar en directorio
    {color('│', Colors.BLUE)} {color('4', Colors.BRIGHT_GREEN)} - Generar fingerprint
    {color('│', Colors.BLUE)} {color('5', Colors.BRIGHT_GREEN)} - Buscar en Spotify
    {color('│', Colors.BLUE)} {color('6', Colors.BRIGHT_GREEN)} - Verificar actualización
    {color('│', Colors.BLUE)} {color('0', Colors.BRIGHT_RED)} - Salir
    {color('└───────────────────────────────────────────────────────────┘', Colors.BLUE)}
    """
    print(menu)

def extract_metadata(file_path):
    """Extrae metadatos de un archivo de audio"""
    ext = os.path.splitext(file_path)[1].lower()
    metadata = {}
    try:
        if ext == ".mp3":
            try:
                audio = EasyID3(file_path)
                metadata["title"] = audio.get("title", ["Desconocido"])[0]
                metadata["artist"] = audio.get("artist", ["Desconocido"])[0]
                metadata["album"] = audio.get("album", ["Desconocido"])[0]
                metadata["date"] = audio.get("date", [""])[0]
            except ID3error:
                audio = ID3(file_path)
                metadata["title"] = str(audio.get("TIT2", "Desconocido"))
                metadata["artist"] = str(audio.get("TPE1", "Desconocido"))
                metadata["album"] = str(audio.get("TALB", "Desconocido"))
        elif ext == ".flac":
            audio = FLAC(file_path)
            metadata["title"] = audio.get("title", ["Desconocido"])[0]
            metadata["artist"] = audio.get("artist", ["Desconocido"])[0]
            metadata["album"] = audio.get("album", ["Desconocido"])[0]
            metadata["date"] = audio.get("date", [""])[0]
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(file_path)
            metadata["title"] = str(audio.get("\xa9nam", ["Desconocido"])[0])
            metadata["artist"] = str(audio.get("\xa9ART", ["Desconocido"])[0])
            metadata["album"] = str(audio.get("\xa9alb", ["Desconocido"])[0])
    except Exception as e:
        print(color(f"[!] Error extrayendo metadatos: {e}", Colors.RED))
    
    return metadata

def extract_isrc(file_path):
    """Extrae ISRC de un archivo de audio"""
    result = {
        'file': file_path,
        'filename': os.path.basename(file_path),
        'isrc': None,
        'artist': None,
        'title': None
    }
    
    try:
        audiofile = None
        fp = file_path.lower()
        
        if fp.endswith('.mp3'):
            try:
                audiofile = EasyID3(file_path)
            except ID3error:
                audiofile = ID3(file_path)
        elif fp.endswith('.flac'):
            audiofile = FLAC(file_path)
        elif fp.endswith(('.m4a', '.mp4', '.aac')):
            audiofile = MP4(file_path)
        
        if audiofile:
            # Buscar ISRC
            for key in ('isrc', 'TSRC'):
                try:
                    if key in audiofile:
                        val = audiofile[key]
                        if isinstance(val, list):
                            val = val[0]
                        result['isrc'] = str(val).strip().upper()
                        break
                except Exception:
                    continue
            
            # Buscar artista
            for art in ('artist', 'ARTIST', '©ART'):
                try:
                    if art in audiofile:
                        val = audiofile[art]
                        result['artist'] = val[0] if isinstance(val, list) else str(val)
                        break
                except Exception:
                    pass
            
            # Buscar título
            for tit in ('title', 'TITLE', '©nam'):
                try:
                    if tit in audiofile:
                        val = audiofile[tit]
                        result['title'] = val[0] if isinstance(val, list) else str(val)
                        break
                except Exception:
                    pass
    
    except Exception as e:
        print(color(f"[!] Error extrayendo ISRC: {e}", Colors.RED))
    
    return result

def process_directory(directory):
    """Procesa todos los archivos de audio en un directorio"""
    SUPPORTED_AUDIO = ('.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma')
    
    if not os.path.isdir(directory):
        print(color(f"[!] El directorio '{directory}' no existe.", Colors.RED))
        return
    
    audio_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_AUDIO):
                audio_files.append(os.path.join(root, file))
    
    if not audio_files:
        print(color(f"[!] No se encontraron archivos de audio en '{directory}'.", Colors.YELLOW))
        return
    
    print(color(f"\n[✓] Se encontraron {len(audio_files)} archivo(s) de audio.\n", Colors.GREEN))
    
    results = []
    for i, file_path in enumerate(audio_files, 1):
        print(color(f"[{i}/{len(audio_files)}] Procesando: {os.path.basename(file_path)}", Colors.CYAN))
        
        isrc_data = extract_isrc(file_path)
        metadata = extract_metadata(file_path)
        
        result = {
            'filename': os.path.basename(file_path),
            'path': file_path,
            'isrc': isrc_data.get('isrc'),
            'artist': isrc_data.get('artist') or metadata.get('artist'),
            'title': isrc_data.get('title') or metadata.get('title'),
            'album': metadata.get('album'),
            'date': metadata.get('date')
        }
        results.append(result)
        
        # Mostrar resultado
        print(f"  {color('Artista:', Colors.YELLOW)} {result['artist']}")
        print(f"  {color('Título:', Colors.YELLOW)} {result['title']}")
        print(f"  {color('ISRC:', Colors.YELLOW)} {result['isrc'] or 'No encontrado'}")
        print()
    
    # Guardar resultados en JSON
    output_file = f"esvintable_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(color(f"[✓] Resultados guardados en: {output_file}", Colors.GREEN))

def generate_fingerprint(file_path):
    """Genera un fingerprint SHA256 del archivo"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        fingerprint = sha256_hash.hexdigest()
        print(color(f"\n[✓] Fingerprint SHA256:", Colors.GREEN))
        print(color(f"    {fingerprint}", Colors.BRIGHT_CYAN))
        return fingerprint
    except Exception as e:
        print(color(f"[!] Error generando fingerprint: {e}", Colors.RED))

def main():
    """Función principal"""
    print_header()
    
    while True:
        print_menu()
        choice = input(color("Selecciona una opción: ", Colors.BRIGHT_YELLOW)).strip()
        
        if choice == '1':
            file_path = input(color("Ruta del archivo: ", Colors.BRIGHT_YELLOW)).strip()
            if os.path.isfile(file_path):
                metadata = extract_metadata(file_path)
                print(color("\n[✓] Metadatos extraídos:", Colors.GREEN))
                for key, value in metadata.items():
                    print(f"  {color(key.capitalize() + ':', Colors.YELLOW)} {value}")
                print()
            else:
                print(color("[!] El archivo no existe.\n", Colors.RED))
        
        elif choice == '2':
            file_path = input(color("Ruta del archivo: ", Colors.BRIGHT_YELLOW)).strip()
            if os.path.isfile(file_path):
                result = extract_isrc(file_path)
                print(color("\n[✓] Información extraída:", Colors.GREEN))
                print(f"  {color('Archivo:', Colors.YELLOW)} {result['filename']}")
                print(f"  {color('Artista:', Colors.YELLOW)} {result['artist'] or 'Desconocido'}")
                print(f"  {color('Título:', Colors.YELLOW)} {result['title'] or 'Desconocido'}")
                print(f"  {color('ISRC:', Colors.YELLOW)} {result['isrc'] or 'No encontrado'}")
                print()
            else:
                print(color("[!] El archivo no existe.\n", Colors.RED))
        
        elif choice == '3':
            directory = input(color("Ruta del directorio: ", Colors.BRIGHT_YELLOW)).strip()
            process_directory(directory)
        
        elif choice == '4':
            file_path = input(color("Ruta del archivo: ", Colors.BRIGHT_YELLOW)).strip()
            if os.path.isfile(file_path):
                generate_fingerprint(file_path)
                print()
            else:
                print(color("[!] El archivo no existe.\n", Colors.RED))
        
        elif choice == '5':
            print(color("[i] Funcionalidad de Spotify en desarrollo...\n", Colors.YELLOW))
        
        elif choice == '6':
            print(color("[i] Verificando actualizaciones...\n", Colors.CYAN))
        
        elif choice == '0':
            print(color("\n[✓] ¡Hasta luego!\n", Colors.GREEN))
            sys.exit(0)
        
        else:
            print(color("[!] Opción no válida.\n", Colors.RED))
        
        input(color("Presiona Enter para continuar...", Colors.DIM))
        print_header()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(color("\n\n[!] Programa interrumpido por el usuario.", Colors.YELLOW))
        sys.exit(0)
    except Exception as e:
        print(color(f"\n[!] Error: {e}", Colors.RED))
        sys.exit(1)

