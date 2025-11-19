"""
gui/widgets/action_panel.py
Panel dedicado a las acciones críticas de ejecución: 
Parada de Emergencia, Pausa y Reanudar.
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Slot, QSize
from PySide6.QtGui import QFont

class ActionPanel(QGroupBox):
    
    def __init__(self, parent=None):
        super().__init__("Control de Ejecución", parent)
        
        layout = QVBoxLayout()
        
        # --- Botón de Emergencia (Grande y Rojo) ---
        self.estop_button = QPushButton("PARADA DE EMERGENCIA")
        self.estop_button.setMinimumHeight(60) # Más alto que los normales
        
        # Estilo agresivo para emergencia
        self.estop_button.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F; 
                color: white; 
                font-weight: bold;
                font-size: 14pt;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #B71C1C; }
            QPushButton:pressed { background-color: #8B0000; }
            QPushButton:disabled { background-color: #FFCDD2; color: #E57373; }
        """)
        
        # --- Botones de Control (Pausa / Reanudar) ---
        control_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("Pausar (!)")
        self.pause_button.setMinimumHeight(40)
        self.pause_button.setStyleSheet("background-color: #FFF176; color: black; font-weight: bold;")
        
        self.resume_button = QPushButton("Reanudar (~)")
        self.resume_button.setMinimumHeight(40)
        self.resume_button.setStyleSheet("background-color: #81C784; color: black; font-weight: bold;")
        
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.resume_button)
        
        # --- Ensamblaje ---
        layout.addWidget(self.estop_button)
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
        
        # Estado inicial: Deshabilitado hasta conectar
        self.set_enabled(False)

    @Slot(bool)
    def set_enabled(self, is_connected: bool):
        """ Habilita los controles solo si hay conexión. """
        self.estop_button.setEnabled(is_connected)
        self.pause_button.setEnabled(is_connected)
        self.resume_button.setEnabled(is_connected)