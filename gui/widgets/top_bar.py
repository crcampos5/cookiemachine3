"""
gui/widgets/top_bar.py
Barra superior reservada para menús y parámetros futuros.
"""
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy

class TopBar(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QGroupBox { border: none; background-color: #EEEEEE; }")
        self.setMaximumHeight(50)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Título o Logo
        title = QLabel("COOKIE MACHINE CONTROL")
        title.setStyleSheet("font-weight: bold; color: #555; font-size: 12pt;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Botón Futuro
        self.btn_params = QPushButton("⚙️ Parámetros")
        self.btn_params.setMinimumHeight(30)
        layout.addWidget(self.btn_params)
        
        self.setLayout(layout)