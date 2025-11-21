"""
gui/widgets/machine_control_panel.py
Botones básicos de la máquina (Home, Unlock, Reset).
"""

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal

class MachineControlPanel(QGroupBox):
    
    def __init__(self, parent=None):
        super().__init__("Comandos Máquina", parent)
        
        layout = QHBoxLayout()
        
        self.home_button = QPushButton("🏠 Home ($H)")
        self.home_button.setMinimumHeight(40)
        
        self.unlock_button = QPushButton("🔓 Desbloquear ($X)")
        self.unlock_button.setMinimumHeight(40)
        
        self.reset_button = QPushButton("Reset (Ctrl+X)")
        self.reset_button.setMinimumHeight(40)
        
        layout.addWidget(self.home_button)
        layout.addWidget(self.unlock_button)
        layout.addWidget(self.reset_button)
        
        self.setLayout(layout)