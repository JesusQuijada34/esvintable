# @JesusQuijada34 | @jq34_channel | @jq34_group
# PyQt5 GUI version - Trebel esVint.v2
# Remix from: @SiMijoSiManda | @simijosimethodleaks
# Github: github.com/JesusQuijada34/esvintable/

import sys
import os
import requests
import cloudscraper

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

# ====================
# QSS - GithubLike Assets
# ====================
GITHUBLIKE_QSS = """
QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Segoe UI', 'Liberation Sans', Arial, sans-serif;
    font-size: 14px;
}
QLabel {
    color: #58a6ff;
    font-weight: bold;
}
QLineEdit, QTextEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    color: #c9d1d9;
    padding: 4px;
}
QPushButton {
    background-color: #238636;
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2ea043;
}
QPushButton:pressed {
    background-color: #196c2e;
}
QMessageBox {
    background-color: #161b22;
    color: #c9d1d9;
}
"""

PROVIDERS = [
    'Warner', 'Orchard', 'SonyMusic', 'UMG', 'INgrooves', 'Fuga', 'Vydia', 'Empire',
    'LabelCamp', 'AudioSalad', 'ONErpm', 'Symphonic', 'Colonize'
]

TREBEL_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIxODkyNDQ0MDEiLCJkZXZpY2VJZCI6IjE1NDAyNjIyMCIsInRyYW5zYWN0aW9uSWQiOjAsImlhdCI6MTc0Mjk4ODg5MX0.Cyj5j4HAmRZpCXQacS8I24p5_hWhIqPdMqb_NVKS4mI"
)

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
            log_callback(f"Solicitando API para {provider}...")
        try:
            r = s.get(ep, headers=headers, timeout=15)
            if r.status_code == 200:
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                fn = os.path.join(output_dir, f"{isrc}.m4a")
                with open(fn, "wb") as o:
                    o.write(r.content)
                if log_callback:
                    log_callback(f"Archivo guardado como: {fn}\n")
                return True, fn
            else:
                if log_callback:
                    log_callback(f"Proveedor {provider}: {r.status_code} - {r.text}")
        except requests.exceptions.RequestException as o:
            if log_callback:
                log_callback(f"Error de red para '{provider}': {o}")
    return False, None

class EsVintableApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESVINTABLE - Trebel esVint.v2")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.banner = QLabel("ESVINTABLE - Trebel esVint.v2")
        self.banner.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.banner)

        self.isrc_label = QLabel("ISRC:")
        layout.addWidget(self.isrc_label)

        self.isrc_input = QLineEdit()
        self.isrc_input.setPlaceholderText("Introduce el ISRC aquí...")
        layout.addWidget(self.isrc_input)

        self.output_label = QLabel("Directorio de salida:")
        layout.addWidget(self.output_label)

        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText("op")
        layout.addWidget(self.output_dir_input)

        self.browse_btn = QPushButton("Seleccionar carpeta")
        self.browse_btn.clicked.connect(self.select_output_dir)
        layout.addWidget(self.browse_btn)

        self.download_btn = QPushButton("Descargar")
        self.download_btn.clicked.connect(self.handle_download)
        layout.addWidget(self.download_btn)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Selecciona el directorio de salida")
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def log(self, message):
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()

    def handle_download(self):
        isrc = self.isrc_input.text().strip()
        output_dir = self.output_dir_input.text().strip()
        if not isrc:
            QMessageBox.warning(self, "Error", "¡El campo ISRC está vacío!")
            return

        self.log_output.clear()
        self.log(f"Verificando país...")

        country = get_country_code()
        if not country:
            QMessageBox.critical(self, "Error", "No se pudo obtener el país. ¿Conexión a internet?")
            return

        if country != "US":
            QMessageBox.critical(self, "Error", "¡Usa VPN o Proxy para 'US' (campo country)!")
            self.log(f"País detectado: {country}. Se requiere US.")
            return

        self.log(f"País detectado: {country}. Iniciando descarga para ISRC: {isrc}...")
        success, filename = download_isrc(isrc, output_dir, log_callback=self.log)
        if success:
            QMessageBox.information(self, "Éxito", f"Descarga completada: {filename}")
        else:
            QMessageBox.warning(self, "Fallo", "No se pudo descargar el archivo con ningún proveedor.")

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GITHUBLIKE_QSS)
    window = EsVintableApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
