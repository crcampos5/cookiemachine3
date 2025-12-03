"""
gui/widgets/led_control_panel.py
Panel lateral para controlar Luz LED y Láser.
"""

from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QSlider, QLabel)
from PySide6.QtCore import Qt, Signal

class LedControlPanel(QGroupBox):
    
    # Señales para enviar al controlador
    request_led_brightness = Signal(int)
    request_laser_power = Signal(int)
    request_led_on = Signal(int,int,int)
    request_led_off = Signal()
    request_laser_off = Signal()
    
    def __init__(self, parent=None):
        super().__init__("Control LedLaser", parent)
        
        layout = QVBoxLayout()
        
        # --- Control LUZ LED ---
        self.lbl_led_val = QLabel("🔆 Brillo Anillo LED: 0")
        
        
        self.led_slider = QSlider(Qt.Horizontal)
        self.led_slider.setRange(0, 255)
        self.led_slider.setValue(0)
        layout.addWidget(self.led_slider)
        
        led_btns = QHBoxLayout()
        self.btn_led_on = QPushButton("Encender Luz")
        self.btn_led_off = QPushButton("Apagar Luz")
        led_btns.addWidget(self.btn_led_on)
        led_btns.addWidget(self.btn_led_off)
        led_btns.addWidget(self.lbl_led_val)
        layout.addLayout(led_btns)
        
        layout.addSpacing(10)
        
        # --- Control LÁSER ---
        self.lbl_laser_val = QLabel("🔥 Intensidad Láser: 0")
        
        
        self.laser_slider = QSlider(Qt.Horizontal)
        self.laser_slider.setRange(0, 255)
        self.laser_slider.setValue(0)
        layout.addWidget(self.laser_slider)
        
        laser_btns = QHBoxLayout()
        self.btn_laser_on = QPushButton("Encender Láser")
        self.btn_laser_on.setStyleSheet("background-color: #FFEBEE; color: #D32F2F;")
        self.btn_laser_off = QPushButton("Apagar Láser")
        laser_btns.addWidget(self.btn_laser_on)
        laser_btns.addWidget(self.btn_laser_off)
        laser_btns.addWidget(self.lbl_laser_val)
        layout.addLayout(laser_btns)
        
        self.setLayout(layout)
        
        # --- Conexiones Internas ---
        self.led_slider.valueChanged.connect(self.request_led_brightness.emit)
        self.led_slider.valueChanged.connect(self.update_led_label)
        # Botón ON manda el valor actual del slider (o un máximo)
        self.btn_led_on.clicked.connect(lambda: self.request_led_on.emit(255,255,255))
        self.btn_led_off.clicked.connect(self.request_led_off.emit)
        
        self.laser_slider.valueChanged.connect(self.request_laser_power.emit)
        self.laser_slider.valueChanged.connect(self.update_laser_label)
        self.btn_laser_on.clicked.connect(lambda: self.request_laser_power.emit(self.laser_slider.value() or 255))
        self.btn_laser_off.clicked.connect(self.request_laser_off.emit)

    def update_led_label(self, value):
        """Actualiza el texto con el valor actual del slider LED"""
        self.lbl_led_val.setText(f"🔆 Brillo Anillo LED: {value}")

    def update_laser_label(self, value):
        """Actualiza el texto con el valor actual del slider Láser"""
        self.lbl_laser_val.setText(f"🔥 Intensidad Láser: {value}")