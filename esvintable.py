#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
esVintable PyQt5 GUI - Estilo GitHub (claro/oscuro automático)
Requisitos (instalar con pip si hace falta):
    pip install PyQt5 mutagen
Autor: @JesusQuijada34 | Mejoras: @MkelCT | Portado: GitHub Copilot
"""

import sys
import os
import hashlib
import subprocess
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLineEdit, QTextEdit,
    QLabel, QFileDialog, QHBoxLayout, QVBoxLayout, QStatusBar, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

# mutagen imports
# try importar mutagen; si falla, intentar instalar y reintentar. Si sigue fallando, salir.
try:
    from mutagen.easyid3 import EasyID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.id3 import ID3, error as ID3error
except Exception:
    try:
        # intentar instalar mutagen usando el mismo intérprete de Python
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"])
        # reintentar import
        from mutagen.easyid3 import EasyID3
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.id3 import ID3, error as ID3error
    except Exception as e:
        print("[!] No se pudo importar ni instalar 'mutagen'.", file=sys.stderr)
        print("Detalle:", e, file=sys.stderr)
        print("Si tiene conexión a internet, intente: pip install mutagen", file=sys.stderr)
        # no continuar si no hay mutagen
        sys.exit(1)

# ---------- Theme detection ----------
def detect_dark_mode():
    try:
        plat = sys.platform
        if plat.startswith("win"):
            import winreg
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return value == 0  # 0 -> dark, 1 -> light
            except Exception:
                return False
        elif plat == "darwin":
            # returns 'Dark' when in dark mode
            p = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            return "Dark" in p.stdout
        else:
            # Try GNOME/GTK via gsettings
            p = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            if p.returncode == 0:
                return "prefer-dark" in p.stdout
            # fallback: check theme name
            p2 = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            if p2.returncode == 0:
                return "dark" in p2.stdout.lower()
    except Exception:
        pass
    return False

# ---------- QSS Styles (GitHub-like) ----------
QSS_DARK = """
QWidget { background: #0d1117; color: #c9d1d9; font-family: "Segoe UI", "Helvetica Neue", Arial; }
QLineEdit, QTextEdit { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }
QPushButton {
    background: #238636; color: white; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: #2ea043; }
QPushButton:pressed { background: #196127; }
QLabel#title { color: #58a6ff; font-weight: 600; font-size: 18px; }
QStatusBar { background: transparent; color: #8b949e; }
QTextEdit { selection-background-color: #1f6feb; selection-color: #ffffff; }
"""

QSS_LIGHT = """
QWidget { background: #f6f8fa; color: #24292f; font-family: "Segoe UI", "Helvetica Neue", Arial; }
QLineEdit, QTextEdit { background: #ffffff; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px; }
QPushButton {
    background: #0969da; color: white; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover { background: #0b57d0; }
QPushButton:pressed { background: #053d9b; }
QLabel#title { color: #0969da; font-weight: 600; font-size: 18px; }
QStatusBar { background: transparent; color: #57606a; }
QTextEdit { selection-background-color: #0969da; selection-color: #ffffff; }
"""

# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("esVintable - Audio Metadata Explorer")
        self.setMinimumSize(900, 600)
        self._set_window_icon()
        self._build_ui()
        self._apply_theme()

    def _set_window_icon(self):
        """
        Intenta establecer el icono de la ventana desde:
        1) app/app-icon.ico (ruta relativa dentro del proyecto o del bundle de PyInstaller)
        2) app-icon.ico en el mismo directorio
        3) extraer el icono del ejecutable en Windows (si está compilado)
        """
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "app", "app-icon.ico"),
            os.path.join(base_dir, "app-icon.ico"),
        ]
        # también comprobar en el directorio del ejecutable (útil para algunos despliegues)
        try:
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "app-icon.ico"))
        except Exception:
            pass

        for p in candidates:
            if p and os.path.isfile(p):
                self.setWindowIcon(QIcon(p))
                return

        # si estamos en Windows y estamos en un ejecutable compilado/ejecutando, intentar usar el .exe como fuente de icono
        if sys.platform.startswith("win"):
            try:
                exe_path = sys.executable
                if exe_path and os.path.isfile(exe_path):
                    # QIcon acepta .exe en Windows y cargará el icono incorporado
                    self.setWindowIcon(QIcon(exe_path))
                    return
            except Exception:
                pass

        # fallback: no icono (QIcon() vacío)
        self.setWindowIcon(QIcon())

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        # Title
        self.title_label = QLabel("🎵 esVintable - Audio Metadata Explorer")
        self.title_label.setObjectName("title")

        # File input and buttons
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Ruta del archivo...")
        self.btn_browse = QPushButton("Examinar")
        self.btn_extract = QPushButton("Extraer")
        self.btn_fingerprint = QPushButton("Fingerprint")

        self.btn_browse.clicked.connect(self.on_browse)
        self.btn_extract.clicked.connect(self.on_extract)
        self.btn_fingerprint.clicked.connect(self.on_fingerprint)

        # Metadata display
        self.metadata_view = QTextEdit()
        self.metadata_view.setReadOnly(True)
        self.metadata_view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._set_status("Listo", "info")

        # Layouts
        top_row = QHBoxLayout()
        top_row.addWidget(self.file_input)
        top_row.addWidget(self.btn_browse)
        top_row.addWidget(self.btn_extract)
        top_row.addWidget(self.btn_fingerprint)

        main_layout = QVBoxLayout(central)
        main_layout.addWidget(self.title_label)
        main_layout.addSpacing(8)
        main_layout.addLayout(top_row)
        main_layout.addSpacing(12)
        main_layout.addWidget(self.metadata_view)

    def _apply_theme(self):
        dark = detect_dark_mode()
        self.setStyleSheet(QSS_DARK if dark else QSS_LIGHT)

    def _set_status(self, text, level="info"):
        # level: info, success, error, warning
        color_map = {
            "info": "#8b949e",
            "success": "#2ea043",
            "error": "#d73a49",
            "warning": "#bf8700"
        }
        color = color_map.get(level, "#8b949e")
        self.status.showMessage(text)
        # small inline styling in statusbar (keeps rest of QSS clean)
        self.status.setStyleSheet(f"color: {color};")

    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de audio", os.path.expanduser("~"),
                                              "Audio files (*.mp3 *.flac *.m4a *.mp4 *.aac);;All files (*)")
        if path:
            self.file_input.setText(path)
            self._set_status("Archivo seleccionado", "info")

    def on_extract(self):
        file_path = self.file_input.text().strip()
        if not file_path or not os.path.isfile(file_path):
            self._set_status("[!] Archivo no encontrado", "error")
            return
        metadata = self._extract_metadata_from_file(file_path)
        self._show_metadata(metadata)
        self._set_status(f"[✓] Metadatos extraídos: {os.path.basename(file_path)}", "success")

    def on_fingerprint(self):
        file_path = self.file_input.text().strip()
        if not file_path or not os.path.isfile(file_path):
            self._set_status("[!] Archivo no encontrado", "error")
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
            self._show_metadata(metadata)
            self._set_status("[✓] Fingerprint generado exitosamente", "success")
        except Exception as e:
            self._set_status(f"[!] Error: {str(e)}", "error")

    def _show_metadata(self, metadata: dict):
        lines = []
        for k, v in metadata.items():
            lines.append(f"{k}: {v}")
        self.metadata_view.setPlainText("\n".join(lines))

    def _extract_metadata_from_file(self, file_path):
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
            # common fields
            metadata["Archivo"] = os.path.basename(file_path)
            metadata["Tamaño"] = f"{os.path.getsize(file_path) / (1024*1024):.2f} MB"
        except Exception as e:
            metadata["Error"] = str(e)
        return metadata

# ---------- Entry point ----------
def main():
    app = QApplication(sys.argv)
    # optional app icon
    # app.setWindowIcon(QIcon('icon.png'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
