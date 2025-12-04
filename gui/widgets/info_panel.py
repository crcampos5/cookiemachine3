"""
gui/widgets/info_panel.py
Widget para mostrar la información de estado (Idle, Run, Alarm),
las coordenadas de la máquina (X, Y, Z) y un registro de mensajes.
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QFormLayout, QLabel, QTextEdit, QHBoxLayout, QCheckBox
from PySide6.QtCore import Slot, Signal
from PySide6.QtGui import QColor, QPalette, QFont

class InfoPanel(QGroupBox):
    """
    Este widget (panel) muestra toda la información pasiva 
    recibida desde el MachineController.
    """

    request_laser_monitoring = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__("Estado y Registros", parent)
        
        # --- Layouts ---
        main_layout = QVBoxLayout()
        position_layout = QFormLayout()
        data_layout = QHBoxLayout()
        dlaser_layout = QHBoxLayout()
        
        # --- 1. Etiqueta de Estado de la Máquina ---
        self.state_label = QLabel("DESCONECTADO")
        font = self.state_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.state_label.setFont(font)
        self.update_status("Desconectado") # Poner el color inicial
        
        # --- 2. Layout de Posición (Formulario) ---
        style_pos = ("font-weight: bold; color: #555; font-size: 12pt;")
        self.x_pos_label = QLabel("---")
        self.x_pos_label.setStyleSheet(style_pos)
        self.y_pos_label = QLabel("---")
        self.y_pos_label.setStyleSheet(style_pos)
        self.z_pos_label = QLabel("---")
        self.z_pos_label.setStyleSheet(style_pos)
        x_label = QLabel("X:")
        x_label.setStyleSheet(style_pos)
        y_label = QLabel("Y:")
        y_label.setStyleSheet(style_pos)
        z_label = QLabel("Z:")
        z_label.setStyleSheet(style_pos)
        self.check_laser = QCheckBox("D:")
        self.check_laser.setStyleSheet(style_pos)
        self.check_laser.setToolTip("Activar medición de distancia en tiempo real")
        self.d_pos_label = QLabel("---")
        self.d_pos_label.setStyleSheet(style_pos)
        dlaser_layout.addWidget(self.check_laser)
        dlaser_layout.addWidget(self.d_pos_label)

        position_layout.addRow(x_label, self.x_pos_label)
        position_layout.addRow(y_label, self.y_pos_label)
        position_layout.addRow(z_label, self.z_pos_label)

        data_layout.addLayout(position_layout)
        data_layout.addLayout(dlaser_layout)
        
        # --- 3. Registro de Mensajes ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200) # Darle un buen tamaño
        
        # --- Ensamblaje ---
        main_layout.addWidget(self.state_label)
        main_layout.addLayout(data_layout)
        #main_layout.addWidget(QLabel("Registro:"))
        main_layout.addWidget(self.log_text, 1) # El '1' le da espacio extra
        
        self.setLayout(main_layout)

        self.check_laser.toggled.connect(self.request_laser_monitoring)

    # --- Slots (para ser llamados desde MainWindow) ---

    @Slot(str)
    def update_status(self, state: str):
        """
        Slot: Se llama cuando el controlador emite 'status_changed'.
        Actualiza la etiqueta de estado y su color.
        """
        self.state_label.setText(state.upper())
        
        # Cambiar el color de la etiqueta de estado
        style = "font-size: 14pt; font-weight: bold; padding: 5px; border-radius: 4px;"
        
        if state == "Idle":
            style += "background-color: #4CAF50; color: white;" # Verde
        elif state == "Run":
            style += "background-color: #03A9F4; color: white;" # Azul
        elif state == "Alarm":
            style += "background-color: #F44336; color: white;" # Rojo
        elif state == "Desconectado":
            style += "background-color: #9E9E9E; color: white;" # Gris
        else:
            style += "background-color: #FFC107; color: black;" # Naranja (para estados intermedios)

        self.state_label.setStyleSheet(style)

    @Slot(float, float, float)
    def update_position(self, x: float, y: float, z: float):
        """
        Slot: Se llama cuando el controlador emite 'position_updated'.
        Actualiza las etiquetas de coordenadas.
        """
        self.x_pos_label.setText(f"{x:.3f} mm")
        self.y_pos_label.setText(f"{y:.3f} mm")
        self.z_pos_label.setText(f"{z:.3f} mm")
    
    @Slot(float)
    def update_laser_distance(self, d: float):
        """ Actualiza la etiqueta de distancia láser. """
        self.d_pos_label.setText(f"{d:.3f} mm")

    @Slot(str)
    def add_log(self, message: str):
        """
        Slot: Se llama cuando el controlador emite 'log_message'.
        Añade el mensaje al registro de texto.
        """
        self.log_text.append(message)
        # Auto-scroll al final
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    @Slot(bool)
    def on_connection_changed(self, is_connected: bool):
        """
        Slot: Se llama cuando el controlador emite 'connection_changed'.
        Limpia las etiquetas si se pierde la conexión.
        """
        if not is_connected:
            self.update_status("Desconectado")
            self.x_pos_label.setText("---")
            self.y_pos_label.setText("---")
            self.z_pos_label.setText("---")
            self.add_log("--- Conexión perdida ---")