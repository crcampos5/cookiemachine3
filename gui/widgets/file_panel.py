"""
gui/widgets/file_panel.py
Panel para cargar archivos G-code.
Simplificado: Solo carga el archivo, el inicio se controla externamente.
"""

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QFileDialog)
from PySide6.QtCore import Signal, Slot, Qt

class FilePanel(QGroupBox):
    
    # Señal que avisa que se cargó un archivo (envía la ruta)
    file_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__("Archivo de Trabajo", parent)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Etiqueta del archivo
        self.lbl_filename = QLabel("Ningún archivo cargado")
        self.lbl_filename.setAlignment(Qt.AlignCenter)
        self.lbl_filename.setStyleSheet("color: #666; font-style: italic; border: 1px dashed #CCC; padding: 5px;")
        self.lbl_filename.setWordWrap(True)
        
        # Botón de Carga (Solo uno)
        self.btn_load = QPushButton("📂 Cargar G-code")
        
        layout.addWidget(self.lbl_filename)
        layout.addWidget(self.btn_load)
        
        self.setLayout(layout)
        
        # Conexiones internas
        self.btn_load.clicked.connect(self.open_file_dialog)
        
        self.file_path = None

    def open_file_dialog(self):
        """ Abre el selector de archivos nativo. """
        fname, _ = QFileDialog.getOpenFileName(
            self, 
            "Abrir diseño G-code", 
            "", 
            "G-code Files (*.gcode *.nc *.txt)"
        )
        
        if fname:
            self.file_path = fname
            # Mostrar solo el nombre visualmente
            name = fname.split('/')[-1] 
            self.lbl_filename.setText(f"📄 {name}")
            self.lbl_filename.setStyleSheet("color: black; font-weight: bold; border: 1px solid #81C784; padding: 5px;")
            
            # Emitir señal inmediatamente para que el controlador prepare el archivo
            self.file_selected.emit(self.file_path)