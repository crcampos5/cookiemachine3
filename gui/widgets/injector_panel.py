"""
gui/widgets/injector_panel.py
Panel de control para el sistema de 4 inyectores.
Incluye selector de color dinámico basado en el archivo G-code.
"""

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QFrame, QComboBox)
from PySide6.QtCore import Signal, Slot, Qt

class InjectorStrip(QFrame):
    """ Columna de control para UN inyector. """
    def __init__(self, index, color_hex, parent=None):
        super().__init__(parent)
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            InjectorStrip {{
                border: 2px solid {color_hex};
                border-radius: 5px;
                background-color: #F5F5F5;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(2, 2, 2, 2)
        
        lbl = QLabel(f"INY {index}")
        lbl.setStyleSheet(f"font-weight: bold; color: {color_hex};")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        
        # --- NUEVO: Selector de Color ---
        self.combo_color = QComboBox()
        self.combo_color.setPlaceholderText("Color...")
        self.combo_color.setStyleSheet("background-color: white;")
        layout.addWidget(self.combo_color)
        
        # 1. Pistón
        self.btn_piston = QPushButton("Pistón ▲")
        self.btn_piston.setCheckable(True)
        self.btn_piston.setStyleSheet("background-color: #E0E0E0;")
        self.btn_piston.toggled.connect(lambda c: self.btn_piston.setText("Pistón ▼" if c else "Pistón ▲"))
        layout.addWidget(self.btn_piston)
        
        # 2. Presión
        self.btn_press = QPushButton("Pres. OFF")
        self.btn_press.setCheckable(True)
        self.btn_press.setStyleSheet("background-color: #E0E0E0;")
        self.btn_press.toggled.connect(lambda c: self.btn_press.setText("Pres. ON" if c else "Pres. OFF"))
        layout.addWidget(self.btn_press)
        
        # 3. Válvula
        self.btn_valve = QPushButton("Válv. 🔒")
        self.btn_valve.setCheckable(True)
        self.btn_valve.setStyleSheet("background-color: #E0E0E0;")
        self.btn_valve.toggled.connect(lambda c: self.btn_valve.setText("Válv. 🔓" if c else "Válv. 🔒"))
        layout.addWidget(self.btn_valve)

class InjectorPanel(QGroupBox):
    
    request_piston = Signal(int, bool)   
    request_pressure = Signal(int, bool) 
    request_valve = Signal(int, bool)    

    def __init__(self, parent=None):
        super().__init__("Sistema de Inyección", parent)
        
        layout = QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        colors = ["#00BCD4", "#E91E63", "#FFC107", "#795548"]
        
        self.injectors = []
        
        for i in range(4):
            idx = i + 1
            strip = InjectorStrip(idx, colors[i])
            
            strip.btn_piston.toggled.connect(lambda c, x=idx: self.request_piston.emit(x, c))
            strip.btn_press.toggled.connect(lambda c, x=idx: self.request_pressure.emit(x, c))
            strip.btn_valve.toggled.connect(lambda c, x=idx: self.request_valve.emit(x, c))
            
            layout.addWidget(strip)
            self.injectors.append(strip)
            
        self.setLayout(layout)
        self.setMaximumHeight(220) # Aumentado un poco para el combo

    @Slot(list)
    def update_color_options(self, colors: list):
        """
        Recibe la lista de colores del G-code y actualiza los combos.
        """
        for strip in self.injectors:
            strip.combo_color.clear()
            if colors:
                strip.combo_color.addItems(colors)
            else:
                strip.combo_color.addItem("Sin Colores")