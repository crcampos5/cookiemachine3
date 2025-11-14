"""
gui/widgets/connect_panel.py
Widget para manejar la selección de puerto, conexión, desconexión y
comandos básicos como Home y Unlock.
(Versión compatible con la arquitectura Cerebro/Cartero)
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
from PySide6.QtCore import Slot

class ConnectPanel(QGroupBox):
    """
    Este widget (panel) contiene todos los controles relacionados
    con la conexión y los comandos de estado de la máquina.
    """
    
    def __init__(self, parent=None):
        super().__init__("Control de Máquina", parent)
        
        # --- Layouts ---
        main_layout = QVBoxLayout()
        port_layout = QHBoxLayout()
        action_layout = QHBoxLayout()
        control_layout = QHBoxLayout()
        
        # --- 1. Fila de Selección de Puerto ---
        self.port_label = QLabel("Puerto:")
        self.port_combo = QComboBox()
        # Darle más espacio para las descripciones largas
        self.port_combo.setMinimumWidth(250) 
        self.port_combo.addItem("Buscando...")
        
        self.refresh_button = QPushButton("Refrescar")
        
        port_layout.addWidget(self.port_label)
        port_layout.addWidget(self.port_combo, 1) # El '1' le da espacio extra
        port_layout.addWidget(self.refresh_button)
        
        # --- 2. Fila de Acciones de Conexión ---
        self.connect_button = QPushButton("Conectar")
        self.disconnect_button = QPushButton("Desconectar")
        
        action_layout.addWidget(self.connect_button)
        action_layout.addWidget(self.disconnect_button)

        # --- 3. Fila de Comandos ---
        self.home_button = QPushButton("Home ($H)")
        self.unlock_button = QPushButton("Desbloquear ($X)")
        
        control_layout.addWidget(self.home_button)
        control_layout.addWidget(self.unlock_button)
        
        # --- 4. Etiqueta de Estado ---
        self.status_label = QLabel("Estado: DESCONECTADO")
        
        # --- Ensamblaje ---
        main_layout.addLayout(port_layout)
        main_layout.addLayout(action_layout)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.status_label)
        main_layout.addStretch(1) # Empuja todo hacia arriba
        
        self.setLayout(main_layout)
        
        # --- Estado Inicial ---
        # Deshabilitar botones hasta que se conecte
        self.update_connection_status(False)

    # --- Slots (para ser llamados desde MainWindow) ---

    @Slot(list)
    def update_port_list(self, ports: list):
        """
        Slot: Se llama cuando el 'Cartero' (SerialConnection) emite 'port_list_updated'.
        Recibe la lista de diccionarios de puertos.
        """
        self.port_combo.clear()
        
        if ports:
            for port_info in ports:
                # Texto a mostrar: "USB-SERIAL CH340 (COM3)"
                display_text = f"{port_info['description']} ({port_info['name']})"
                
                # Dato interno: "COM3"
                port_name = port_info['name']
                
                # Añadimos ambos al ComboBox
                self.port_combo.addItem(display_text, port_name)
                
            self.connect_button.setEnabled(True)
        else:
            self.port_combo.addItem("No se encontraron puertos")
            self.connect_button.setEnabled(False) # No se puede conectar si no hay puertos

    @Slot(bool)
    def update_connection_status(self, is_connected: bool):
        """
        Slot: Se llama cuando el 'Cartero' (SerialConnection) emite 'connection_changed'.
        Habilita/deshabilita los botones según el estado de la conexión.
        """
        # Botones que deben estar habilitados SÓLO si NO estamos conectados
        self.connect_button.setEnabled(not is_connected)
        self.refresh_button.setEnabled(not is_connected)
        self.port_combo.setEnabled(not is_connected)
        
        # Botones que deben estar habilitados SÓLO si SÍ estamos conectados
        self.disconnect_button.setEnabled(is_connected)
        self.home_button.setEnabled(is_connected)
        self.unlock_button.setEnabled(is_connected)
        
        # Actualizar la etiqueta de estado visualmente
        if is_connected:
            self.status_label.setText("Estado: CONECTADO")
            # Estilo CSS para el color verde
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.status_label.setText("Estado: DESCONECTADO")
            # Estilo CSS para el color rojo
            self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")

    # --- Métodos de Ayuda (para ser llamados desde MainWindow) ---

    def get_selected_port(self) -> str:
        """
        Devuelve el dato interno (ej: "COM3") del puerto seleccionado.
        """
        if self.port_combo.count() > 0:
            # currentData() obtiene el segundo argumento (el dato interno) 
            # que pasamos a addItem()
            return self.port_combo.currentData()
        return None