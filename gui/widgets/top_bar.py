"""
gui/widgets/top_bar.py
Barra superior para gestión de conexiones (FluidNC y Arduino).
Diseño compacto horizontal.
"""

from PySide6.QtWidgets import (QGroupBox, QHBoxLayout, QPushButton, 
                               QComboBox, QLabel, QWidget, QSizePolicy)
from PySide6.QtCore import Slot, Qt

class TopBar(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("") # Sin título para ahorrar espacio vertical
        self.setStyleSheet("QGroupBox { border: none; background-color: #E0E0E0; }")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # --- 1. Refrescar ---
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("Refrescar Puertos")
        self.refresh_button.setMaximumWidth(40)
        layout.addWidget(self.refresh_button)
        
        # --- 2. Sección Máquina (FluidNC) ---
        self.machine_combo = QComboBox()
        self.machine_combo.setPlaceholderText("Puerto Máquina...")
        self.machine_combo.setMinimumWidth(150)
        
        self.btn_connect_machine = QPushButton("Conectar Maq.")
        self.btn_disconnect_machine = QPushButton("X")
        self.btn_disconnect_machine.setMaximumWidth(30)
        self.btn_disconnect_machine.setEnabled(False)
        
        self.lbl_status_machine = QLabel("🔴")
        self.lbl_status_machine.setToolTip("Estado Máquina: Desconectado")
        
        layout.addWidget(QLabel("MAQ:"))
        layout.addWidget(self.machine_combo)
        layout.addWidget(self.btn_connect_machine)
        layout.addWidget(self.btn_disconnect_machine)
        layout.addWidget(self.lbl_status_machine)
        
        # Espaciador
        layout.addSpacing(20)

        # --- 3. Sección Sensor (Arduino) ---
        self.arduino_combo = QComboBox()
        self.arduino_combo.setPlaceholderText("Puerto LedLaser...")
        self.arduino_combo.setMinimumWidth(150)
        
        self.btn_connect_arduino = QPushButton("Conectar LED")
        self.btn_disconnect_arduino = QPushButton("X")
        self.btn_disconnect_arduino.setMaximumWidth(30)
        self.btn_disconnect_arduino.setEnabled(False)
        
        self.lbl_status_arduino = QLabel("🔴")
        self.lbl_status_arduino.setToolTip("Estado Sensor: Desconectado")
        
        layout.addWidget(QLabel("LED:"))
        layout.addWidget(self.arduino_combo)
        layout.addWidget(self.btn_connect_arduino)
        layout.addWidget(self.btn_disconnect_arduino)
        layout.addWidget(self.lbl_status_arduino)
        
        layout.addStretch() # Empujar todo a la izquierda
        self.setLayout(layout)
        self.setMaximumHeight(60) # Forzar altura pequeña

    # --- SLOTS (Lógica de UI) ---

    @Slot(list)
    def update_port_list(self, ports: list):
        """ Actualiza ambos combos. """
        current_machine = self.machine_combo.currentData()
        current_arduino = self.arduino_combo.currentData()
        
        self.machine_combo.clear()
        self.arduino_combo.clear()
        
        if not ports:
            return

        for port_info in ports:
            display = f"{port_info.get('display', port_info['name'])}"
            name = port_info['name']
            self.machine_combo.addItem(display, name)
            self.arduino_combo.addItem(display, name)
            
        # Restaurar selección
        if current_machine: 
            idx = self.machine_combo.findData(current_machine)
            if idx >= 0: self.machine_combo.setCurrentIndex(idx)
        if current_arduino:
            idx = self.arduino_combo.findData(current_arduino)
            if idx >= 0: self.arduino_combo.setCurrentIndex(idx)

    @Slot(bool)
    def set_machine_status(self, connected: bool):
        self.btn_connect_machine.setEnabled(not connected)
        self.btn_disconnect_machine.setEnabled(connected)
        self.machine_combo.setEnabled(not connected)
        if connected:
            self.lbl_status_machine.setText("🟢")
            self.lbl_status_machine.setToolTip("Estado Máquina: CONECTADO")
        else:
            self.lbl_status_machine.setText("🔴")
            self.lbl_status_machine.setToolTip("Estado Máquina: DESCONECTADO")

    @Slot(bool)
    def set_arduino_status(self, connected: bool):
        self.btn_connect_arduino.setEnabled(not connected)
        self.btn_disconnect_arduino.setEnabled(connected)
        self.arduino_combo.setEnabled(not connected)
        if connected:
            self.lbl_status_arduino.setText("🟢")
            self.lbl_status_arduino.setToolTip("Estado Sensor: CONECTADO")
        else:
            self.lbl_status_arduino.setText("🔴")
            self.lbl_status_arduino.setToolTip("Estado Sensor: DESCONECTADO")

    def get_machine_port(self): return self.machine_combo.currentData()
    def get_arduino_port(self): return self.arduino_combo.currentData()