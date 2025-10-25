#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esVintable GUI - Versión Pygame Avanzada
Herramienta visual para extraer metadatos de archivos de audio
Autor: @JesusQuijada34 | Mejoras: @MkelCT
"""

import os
import sys
import pygame
import json
import hashlib
from datetime import datetime
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, error as ID3error

# ===== INICIALIZACIÓN DE PYGAME =====
pygame.init()

# ===== CONFIGURACIÓN DE PANTALLA =====
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# ===== COLORES =====
class Colors:
    BG = (20, 20, 30)
    SURFACE = (35, 35, 50)
    ACCENT = (0, 120, 212)
    ACCENT_HOVER = (16, 124, 16)
    TEXT_PRIMARY = (240, 240, 240)
    TEXT_SECONDARY = (180, 180, 180)
    BORDER = (80, 80, 100)
    SUCCESS = (16, 124, 16)
    ERROR = (196, 49, 11)
    WARNING = (255, 184, 28)

# ===== FUENTES =====
FONT_LARGE = pygame.font.Font(None, 32)
FONT_MEDIUM = pygame.font.Font(None, 24)
FONT_SMALL = pygame.font.Font(None, 18)

class Button:
    """Clase para crear botones interactivos"""
    def __init__(self, x, y, width, height, text, color=Colors.ACCENT, hover_color=Colors.ACCENT_HOVER):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
    
    def draw(self, surface):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, Colors.BORDER, self.rect, 2, border_radius=8)
        
        text_surface = FONT_MEDIUM.render(self.text, True, Colors.TEXT_PRIMARY)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)
    
    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

class TextInput:
    """Clase para campos de entrada de texto"""
    def __init__(self, x, y, width, height, placeholder=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.is_active = False
    
    def draw(self, surface):
        color = Colors.ACCENT if self.is_active else Colors.BORDER
        pygame.draw.rect(surface, Colors.SURFACE, self.rect, border_radius=6)
        pygame.draw.rect(surface, color, self.rect, 2, border_radius=6)
        
        display_text = self.text if self.text else self.placeholder
        text_color = Colors.TEXT_PRIMARY if self.text else Colors.TEXT_SECONDARY
        text_surface = FONT_SMALL.render(display_text, True, text_color)
        surface.blit(text_surface, (self.rect.x + 10, self.rect.y + 10))
    
    def update(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.is_active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.is_active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable():
                self.text += event.unicode

class MetadataDisplay:
    """Clase para mostrar metadatos extraídos"""
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.metadata = {}
        self.scroll_y = 0
    
    def set_metadata(self, metadata):
        self.metadata = metadata
        self.scroll_y = 0
    
    def draw(self, surface):
        pygame.draw.rect(surface, Colors.SURFACE, self.rect, border_radius=8)
        pygame.draw.rect(surface, Colors.BORDER, self.rect, 2, border_radius=8)
        
        y_offset = self.rect.y + 10 - self.scroll_y
        
        for key, value in self.metadata.items():
            label = FONT_SMALL.render(f"{key.upper()}:", True, Colors.ACCENT)
            value_text = FONT_SMALL.render(str(value), True, Colors.TEXT_PRIMARY)
            
            surface.blit(label, (self.rect.x + 10, y_offset))
            surface.blit(value_text, (self.rect.x + 150, y_offset))
            
            y_offset += 30

class App:
    """Aplicación principal de Pygame"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("🎵 esVintable - Audio Metadata Explorer")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Elementos de UI
        self.file_input = TextInput(20, 80, 400, 40, "Ruta del archivo...")
        self.btn_browse = Button(430, 80, 120, 40, "Examinar")
        self.btn_extract = Button(560, 80, 120, 40, "Extraer")
        self.btn_fingerprint = Button(690, 80, 150, 40, "Fingerprint")
        
        self.metadata_display = MetadataDisplay(20, 140, SCREEN_WIDTH - 40, SCREEN_HEIGHT - 200)
        
        self.status_text = ""
        self.status_color = Colors.TEXT_SECONDARY
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            self.file_input.update(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_browse.is_clicked(event.pos):
                    self.browse_file()
                elif self.btn_extract.is_clicked(event.pos):
                    self.extract_metadata()
                elif self.btn_fingerprint.is_clicked(event.pos):
                    self.generate_fingerprint()
            
            if event.type == pygame.MOUSEMOTION:
                self.btn_browse.update(event.pos)
                self.btn_extract.update(event.pos)
                self.btn_fingerprint.update(event.pos)
    
    def browse_file(self):
        """Simula la búsqueda de archivo (en una versión real usaría tkinter)"""
        self.status_text = "Funcionalidad de explorador en desarrollo..."
        self.status_color = Colors.WARNING
    
    def extract_metadata(self):
        """Extrae metadatos del archivo especificado"""
        file_path = self.file_input.text.strip()
        
        if not file_path or not os.path.isfile(file_path):
            self.status_text = "[!] Archivo no encontrado"
            self.status_color = Colors.ERROR
            return
        
        metadata = self._extract_metadata_from_file(file_path)
        self.metadata_display.set_metadata(metadata)
        self.status_text = f"[✓] Metadatos extraídos de: {os.path.basename(file_path)}"
        self.status_color = Colors.SUCCESS
    
    def generate_fingerprint(self):
        """Genera el fingerprint SHA256 del archivo"""
        file_path = self.file_input.text.strip()
        
        if not file_path or not os.path.isfile(file_path):
            self.status_text = "[!] Archivo no encontrado"
            self.status_color = Colors.ERROR
            return
        
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            fingerprint = sha256_hash.hexdigest()
            metadata = {
                "Archivo": os.path.basename(file_path),
                "Fingerprint SHA256": fingerprint,
                "Generado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.metadata_display.set_metadata(metadata)
            self.status_text = "[✓] Fingerprint generado exitosamente"
            self.status_color = Colors.SUCCESS
        except Exception as e:
            self.status_text = f"[!] Error: {str(e)}"
            self.status_color = Colors.ERROR
    
    def _extract_metadata_from_file(self, file_path):
        """Extrae metadatos de un archivo de audio"""
        ext = os.path.splitext(file_path)[1].lower()
        metadata = {}
        
        try:
            if ext == ".mp3":
                try:
                    audio = EasyID3(file_path)
                    metadata["Título"] = audio.get("title", ["Desconocido"])[0]
                    metadata["Artista"] = audio.get("artist", ["Desconocido"])[0]
                    metadata["Álbum"] = audio.get("album", ["Desconocido"])[0]
                    metadata["Año"] = audio.get("date", [""])[0]
                except ID3error:
                    audio = ID3(file_path)
                    metadata["Título"] = str(audio.get("TIT2", "Desconocido"))
                    metadata["Artista"] = str(audio.get("TPE1", "Desconocido"))
                    metadata["Álbum"] = str(audio.get("TALB", "Desconocido"))
            
            elif ext == ".flac":
                audio = FLAC(file_path)
                metadata["Título"] = audio.get("title", ["Desconocido"])[0]
                metadata["Artista"] = audio.get("artist", ["Desconocido"])[0]
                metadata["Álbum"] = audio.get("album", ["Desconocido"])[0]
                metadata["Año"] = audio.get("date", [""])[0]
            
            elif ext in (".m4a", ".mp4", ".aac"):
                audio = MP4(file_path)
                metadata["Título"] = str(audio.get("\xa9nam", ["Desconocido"])[0])
                metadata["Artista"] = str(audio.get("\xa9ART", ["Desconocido"])[0])
                metadata["Álbum"] = str(audio.get("\xa9alb", ["Desconocido"])[0])
            
            metadata["Archivo"] = os.path.basename(file_path)
            metadata["Tamaño"] = f"{os.path.getsize(file_path) / (1024*1024):.2f} MB"
        
        except Exception as e:
            metadata["Error"] = str(e)
        
        return metadata
    
    def draw(self):
        """Dibuja la interfaz"""
        self.screen.fill(Colors.BG)
        
        # Encabezado
        title = FONT_LARGE.render("🎵 esVintable - Audio Metadata Explorer", True, Colors.ACCENT)
        self.screen.blit(title, (20, 20))
        
        # Elementos de entrada
        self.file_input.draw(self.screen)
        self.btn_browse.draw(self.screen)
        self.btn_extract.draw(self.screen)
        self.btn_fingerprint.draw(self.screen)
        
        # Área de metadatos
        self.metadata_display.draw(self.screen)
        
        # Barra de estado
        status_surface = FONT_SMALL.render(self.status_text, True, self.status_color)
        self.screen.blit(status_surface, (20, SCREEN_HEIGHT - 40))
        
        pygame.display.flip()
    
    def run(self):
        """Bucle principal de la aplicación"""
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit(0)

if __name__ == '__main__':
    try:
        app = App()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        pygame.quit()
        sys.exit(1)

