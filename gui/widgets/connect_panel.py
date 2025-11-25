"""
gui/widgets/connect_panel.py
Widget para manejar la conexión manual independiente de:
1. MÁQUINA (FluidNC)
2. LEDLASER (Arduino)
"""

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QComboBox, QLabel, QFrame)
from PySide6.QtCore import Slot, Qt

class ConnectPanel(QGroupBox):
    
    def __init__(self, parent=None):
        super().__init__("Conexiones", parent)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        
        # --- 1. Refrescar Global ---
        self.refresh_button = QPushButton("🔄 Refrescar Puertos USB")
        main_layout.addWidget(self.refresh_button)
        
        # =============================================
        # SECCIÓN A: MÁQUINA (FluidNC)
        # =============================================
        machine_box = QGroupBox("MÁQUINA")
        machine_box.setStyleSheet("QGroupBox { font-weight: bold; color: #1565C0; }")
        m_layout = QVBoxLayout()
        
        self.machine_combo = QComboBox()
        self.machine_combo.setPlaceholderText("Seleccione puerto...")
        m_layout.addWidget(self.machine_combo)
        
        m_btn_layout = QHBoxLayout()
        self.btn_connect_machine = QPushButton("Conectar")
        self.btn_disconnect_machine = QPushButton("Desconectar")
        self.btn_disconnect_machine.setEnabled(False)
        self.lbl_status_machine = QLabel("🔴 DESCONECTADO")
        self.lbl_status_machine.setAlignment(Qt.AlignCenter)
        self.lbl_status_machine.setStyleSheet("background-color: #FFCDD2; border-radius: 4px; padding: 2px;")
        m_btn_layout.addWidget(self.btn_connect_machine)
        m_btn_layout.addWidget(self.btn_disconnect_machine)
        m_btn_layout.addWidget(self.lbl_status_machine)
        
        m_layout.addLayout(m_btn_layout)
        
        machine_box.setLayout(m_layout)
        main_layout.addWidget(machine_box)

        # =============================================
        # SECCIÓN B: LEDLASER (Arduino)
        # =============================================
        arduino_box = QGroupBox("LEDLASER")
        arduino_box.setStyleSheet("QGroupBox { font-weight: bold; color: #2E7D32; }")
        a_layout = QVBoxLayout()
        
        self.arduino_combo = QComboBox()
        a_layout.addWidget(self.arduino_combo)
        
        a_btn_layout = QHBoxLayout()
        self.btn_connect_arduino = QPushButton("Conectar")
        self.btn_disconnect_arduino = QPushButton("Desconectar")
        self.btn_disconnect_arduino.setEnabled(False)
        self.lbl_status_arduino = QLabel("🔴 DESCONECTADO")
        self.lbl_status_arduino.setAlignment(Qt.AlignCenter)
        self.lbl_status_arduino.setStyleSheet("background-color: #FFCDD2; border-radius: 4px; padding: 2px;")
        a_btn_layout.addWidget(self.btn_connect_arduino)
        a_btn_layout.addWidget(self.btn_disconnect_arduino)
        a_btn_layout.addWidget(self.lbl_status_arduino)
        a_layout.addLayout(a_btn_layout)
        
        
        #a_layout.addWidget(self.lbl_status_arduino)
        
        arduino_box.setLayout(a_layout)
        main_layout.addWidget(arduino_box)
        
        main_layout.addStretch()
        self.setLayout(main_layout)

    @Slot(list)
    def update_port_list(self, ports: list):
        current_machine = self.get_machine_port()
        current_arduino = self.get_arduino_port()
        
        self.machine_combo.clear()
        self.arduino_combo.clear()
        
        if not ports:
            self.machine_combo.addItem("Sin puertos")
            self.arduino_combo.addItem("Sin puertos")
            return

        for port_info in ports:
            display = f"{port_info.get('display', port_info['name'])}"
            name = port_info['name']
            self.machine_combo.addItem(display, name)
            self.arduino_combo.addItem(display, name)
            
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
            self.lbl_status_machine.setText("🟢 CONECTADO")
            self.lbl_status_machine.setStyleSheet("background-color: #C8E6C9; color: #2E7D32; border-radius: 4px; padding: 2px; font-weight: bold;")
        else:
            self.lbl_status_machine.setText("🔴 DESCONECTADO")
            self.lbl_status_machine.setStyleSheet("background-color: #FFCDD2; color: #C62828; border-radius: 4px; padding: 2px;")

    @Slot(bool)
    def set_arduino_status(self, connected: bool):
        self.btn_connect_arduino.setEnabled(not connected)
        self.btn_disconnect_arduino.setEnabled(connected)
        self.arduino_combo.setEnabled(not connected)
        
        if connected:
            self.lbl_status_arduino.setText("🟢 CONECTADO")
            self.lbl_status_arduino.setStyleSheet("background-color: #C8E6C9; color: #2E7D32; border-radius: 4px; padding: 2px; font-weight: bold;")
        else:
            self.lbl_status_arduino.setText("🔴 DESCONECTADO")
            self.lbl_status_arduino.setStyleSheet("background-color: #FFCDD2; color: #C62828; border-radius: 4px; padding: 2px;")

    def get_machine_port(self):
        return self.machine_combo.currentData()

    def get_arduino_port(self):
        return self.arduino_combo.currentData()