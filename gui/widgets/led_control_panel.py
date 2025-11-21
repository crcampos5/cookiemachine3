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
        layout.addWidget(QLabel("🔆 Brillo Anillo LED:"))
        
        self.led_slider = QSlider(Qt.Horizontal)
        self.led_slider.setRange(0, 255)
        self.led_slider.setValue(0)
        layout.addWidget(self.led_slider)
        
        led_btns = QHBoxLayout()
        self.btn_led_on = QPushButton("Encender Luz")
        self.btn_led_off = QPushButton("Apagar Luz")
        led_btns.addWidget(self.btn_led_on)
        led_btns.addWidget(self.btn_led_off)
        layout.addLayout(led_btns)
        
        layout.addSpacing(10)
        
        # --- Control LÁSER ---
        layout.addWidget(QLabel("🔥 Intensidad Láser:"))
        
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
        layout.addLayout(laser_btns)
        
        self.setLayout(layout)
        
        # --- Conexiones Internas ---
        self.led_slider.valueChanged.connect(self.request_led_brightness.emit)
        # Botón ON manda el valor actual del slider (o un máximo)
        self.btn_led_on.clicked.connect(lambda: self.request_led_on.emit(255,255,255))
        self.btn_led_off.clicked.connect(self.request_led_off.emit)
        
        self.laser_slider.valueChanged.connect(self.request_laser_power.emit)
        self.btn_laser_on.clicked.connect(lambda: self.request_laser_power.emit(self.laser_slider.value() or 255))
        self.btn_laser_off.clicked.connect(self.request_laser_off.emit)