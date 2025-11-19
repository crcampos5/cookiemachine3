"""
gui/widgets/move_controls.py
Widget para los controles de movimiento manual (Jogging) X, Y, Z.
"""

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QDoubleSpinBox, QGridLayout,
                               QLabel, QWidget, QSizePolicy, QSpinBox)
from PySide6.QtCore import Signal, Slot, Qt

class MoveControls(QGroupBox):
    """
    Este widget (panel) emite señales con comandos G-code de jogging
    basados en los valores de distancia y velocidad seleccionados.
    """
    
    # Señal que emite el comando G-code de jogging (ej: "G91 G0 X10 F1000")
    jog_command = Signal(str)

    def __init__(self, parent=None):
        super().__init__("Movimiento Manual (Jog)", parent)
        
        # --- Layouts ---
        main_layout = QVBoxLayout()
        settings_layout = QHBoxLayout()
        buttons_layout = QHBoxLayout()
        xy_layout = QGridLayout()
        z_layout = QVBoxLayout()
        
        # --- 1. Ajustes de Movimiento ---
        # (Análogo a tus 'step_move' y 'feed_move')
        
        self.step_spinbox = QDoubleSpinBox()
        self.step_spinbox.setSuffix(" mm")
        self.step_spinbox.setDecimals(2)
        self.step_spinbox.setValue(10.0)
        self.step_spinbox.setSingleStep(1.0)
        self.step_spinbox.setMinimum(0.01)
        self.step_spinbox.setMaximum(100.0)
        
        self.feed_spinbox = QSpinBox()
        self.feed_spinbox.setSuffix(" F")
        self.feed_spinbox.setValue(500)
        self.feed_spinbox.setSingleStep(10)
        self.feed_spinbox.setMinimum(0)
        self.feed_spinbox.setMaximum(1000)
        
        settings_layout.addWidget(QLabel("Distancia:"))
        settings_layout.addWidget(self.step_spinbox, 1) # stretch 1
        settings_layout.addWidget(QLabel("Velocidad:"))
        settings_layout.addWidget(self.feed_spinbox, 1) # stretch 1
        
        # --- 2. Botones de Movimiento ---
        
        # Botones X/Y
        self.y_pos_button = QPushButton("Y+")
        self.y_neg_button = QPushButton("Y-")
        self.x_pos_button = QPushButton("X+")
        self.x_neg_button = QPushButton("X-")
        
        # Botones Z
        self.z_pos_button = QPushButton("Z+")
        self.z_neg_button = QPushButton("Z-")
        
        # --- Ensamblaje de Botones ---
        
        # Layout de la cruceta X/Y
        xy_layout.addWidget(self.y_pos_button, 0, 1)
        xy_layout.addWidget(self.x_neg_button, 1, 0)
        xy_layout.addWidget(QWidget(), 1, 1) # Placeholder central
        xy_layout.addWidget(self.x_pos_button, 1, 2)
        xy_layout.addWidget(self.y_neg_button, 2, 1)
        
        # Layout de Z
        z_layout.addWidget(self.z_pos_button)
        z_layout.addWidget(self.z_neg_button)
        
        buttons_layout.addLayout(xy_layout, 2)  # X/Y ocupa más espacio
        buttons_layout.addStretch(1)            # Espaciador
        buttons_layout.addLayout(z_layout, 1)   # Z ocupa menos
        
        # --- Ensamblaje Principal ---
        main_layout.addLayout(settings_layout)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)
        
        # --- Conectar Señales ---
        self.x_pos_button.clicked.connect(lambda: self._on_jog_button_clicked("X"))
        self.x_neg_button.clicked.connect(lambda: self._on_jog_button_clicked("X", positive=False))
        self.y_pos_button.clicked.connect(lambda: self._on_jog_button_clicked("Y"))
        self.y_neg_button.clicked.connect(lambda: self._on_jog_button_clicked("Y", positive=False))
        self.z_pos_button.clicked.connect(lambda: self._on_jog_button_clicked("Z"))
        self.z_neg_button.clicked.connect(lambda: self._on_jog_button_clicked("Z", positive=False))
        
    def _on_jog_button_clicked(self, axis: str, positive: bool = True):
        """
        Función interna para construir y emitir el comando G-code.
        """
        step = self.step_spinbox.value()
        feed = self.feed_spinbox.value()
        
        if not positive:
            step = -step
            
        # G91 = Movimiento Relativo
        # G0 = Movimiento Rápido
        gcode_command = f"G91 G1 {axis}{step} F{feed}"
        
        # Emitir la señal para que MainWindow la capture
        self.jog_command.emit(gcode_command)
        
    # --- Slots (para ser llamados desde MainWindow) ---

    @Slot(bool)
    def set_controls_enabled(self, is_enabled: bool):
        """
        Slot: Se llama cuando el controlador emite 'machine_ready'.
        Habilita o deshabilita todos los controles de este panel.
        """
        # Deshabilita el QGroupBox entero, lo cual
        # deshabilita todos sus widgets hijos (botones, spinboxes).
        self.setEnabled(is_enabled)