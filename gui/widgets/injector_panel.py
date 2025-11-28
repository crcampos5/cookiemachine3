from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QFrame, QComboBox)
from PySide6.QtCore import Signal, Slot, Qt

class InjectorStrip(QFrame):
    """ Columna de control para UN inyector. """
    def __init__(self, index, color_hex, parent=None):
        super().__init__(parent)
        self.index = index
        self.default_border = color_hex
        
        self.setFrameShape(QFrame.StyledPanel)
        # Guardamos el estilo base para poder restaurarlo o modificarlo
        self.current_border_color = color_hex
        self._apply_style()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_title = QLabel(f"INY {index}")
        self.lbl_title.setStyleSheet(f"font-weight: bold; color: {color_hex};")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_title)
        
        # Etiqueta para mostrar el nombre del color del G-code (Ej: "Glaseado Rojo")
        self.lbl_gcode_info = QLabel("---")
        self.lbl_gcode_info.setStyleSheet("font-size: 9pt; color: #555;")
        self.lbl_gcode_info.setAlignment(Qt.AlignCenter)
        self.lbl_gcode_info.setWordWrap(True)
        layout.addWidget(self.lbl_gcode_info)
        
        # 1. Pistón
        self.btn_piston = QPushButton("Pistón ▲")
        self.btn_piston.setCheckable(True)
        self.btn_piston.setStyleSheet("background-color: #E0E0E0;")
        self.btn_piston.toggled.connect(lambda c: self.btn_piston.setText("Pistón ▼" if c else "Pistón ▲"))
        layout.addWidget(self.btn_piston)
        
        # ... (Resto de botones Presión y Válvula igual que antes) ...
        # [Copia aquí el código de btn_press y btn_valve de tu archivo original]
        self.btn_press = QPushButton("Pres. OFF")
        self.btn_press.setCheckable(True)
        self.btn_press.setStyleSheet("background-color: #E0E0E0;")
        self.btn_press.toggled.connect(lambda c: self.btn_press.setText("Pres. ON" if c else "Pres. OFF"))
        layout.addWidget(self.btn_press)

        self.btn_valve = QPushButton("Válv. 🔒")
        self.btn_valve.setCheckable(True)
        self.btn_valve.setStyleSheet("background-color: #E0E0E0;")
        self.btn_valve.toggled.connect(lambda c: self.btn_valve.setText("Válv. 🔓" if c else "Válv. 🔒"))
        layout.addWidget(self.btn_valve)
    
    def _apply_style(self):
        """ Aplica el estilo del borde basado en self.current_border_color """
        self.setStyleSheet(f"""
            InjectorStrip {{
                border: 2px solid {self.current_border_color};
                border-radius: 5px;
                background-color: #F5F5F5;
            }}
        """)
    
    def _apply_title_style(self):
        """ Aplica el color al texto del título """
        self.lbl_title.setStyleSheet(f"font-weight: bold; color: {self.current_border_color}; font-size: 10pt;")

    def update_strip_color(self, new_color_hex):
        """ 
        Cambia el color del borde y del título dinámicamente.
        Útil para reflejar el color del ingrediente asignado.
        """
        self.current_border_color = new_color_hex
        if self.isEnabled():
            self._apply_style()
            self._apply_title_style()

    def set_active_state(self, enabled: bool):
        """ Habilita o deshabilita visualmente el strip """
        self.setEnabled(enabled)
        if not enabled:
            self.setStyleSheet("""
                InjectorStrip {
                    border: 2px dashed #999;
                    border-radius: 5px;
                    background-color: #E0E0E0;
                }
            """)
            self.lbl_title.setText(f"INY {self.index} (OFF)")
            self.lbl_title.setStyleSheet("color: #777; font-weight: bold;")
        else:
            self._apply_style()
            self.lbl_title.setText(f"INY {self.index}")
            self._apply_title_style()

class InjectorPanel(QGroupBox):
    
    request_piston = Signal(int, bool)   
    request_pressure = Signal(int, bool) 
    request_valve = Signal(int, bool)  
    log_message = Signal(str)  

    def __init__(self, parent=None):
        super().__init__("Sistema de Inyección", parent)
        layout = QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        colors = ["#00BCD4", "#E91E63", "#FFC107", "#795548"]
        self.injectors = []
        self.physical_status = [True, True, True, True]
        
        for i in range(4):
            idx = i + 1
            strip = InjectorStrip(idx, colors[i])
            
            # Conexiones
            strip.btn_piston.toggled.connect(lambda c, x=idx: self.request_piston.emit(x, c))
            strip.btn_press.toggled.connect(lambda c, x=idx: self.request_pressure.emit(x, c))
            strip.btn_valve.toggled.connect(lambda c, x=idx: self.request_valve.emit(x, c))
            
            layout.addWidget(strip)
            self.injectors.append(strip)
            
        self.setLayout(layout)
        self.setMaximumHeight(240)

    @Slot(dict)
    def apply_startup_config(self, injectors_config: dict):
        """
        Recibe el diccionario 'injectors' del parameters.json
        Ej: { "injector1": {"disabled": 1}, ... }
        """
        self.physical_status = []

        for i, strip in enumerate(self.injectors):
            key = f"injector{i+1}"
            data = injectors_config.get(key, {})
            # Si disabled=1 -> Falso, si no -> Verdadero
            is_enabled = not (data.get("disabled", 0) == 1)
            
            self.physical_status.append(is_enabled)
            strip.set_active_state(is_enabled)

    @Slot(dict)
    def update_from_gcode_data(self, injectors_data: dict):
        """
        Asigna secuencialmente los inyectores del G-code a los físicos disponibles.
        Ejemplo: 
           Físicos disponibles: [2, 3] (porque 1 y 4 disabled)
           G-code pide: 1 (Rojo), 2 (Azul)
           ---------------------------------------------------
           Resultado: Físico 2 <- G-code 1 (Rojo)
                      Físico 3 <- G-code 2 (Azul)
        """
        # 1. Limpiar visualmente todos los strips
        for strip in self.injectors:
            strip.lbl_gcode_info.setText("---")
            strip.lbl_gcode_info.setStyleSheet("color: #999;")

        if not injectors_data:
            return
        

        # 2. Obtener lista de índices físicos disponibles (0, 1, 2, 3)
        # Ej: Si 1 y 4 están off, available_indices = [1, 2] (corresponde a INY2 e INY3)
        available_indices = [i for i, enabled in enumerate(self.physical_status) if enabled]

        # 3. Obtener IDs del G-code ordenados
        # Las claves vienen como strings "1", "2", etc.
        gcode_ids = sorted(injectors_data.keys(), key=lambda x: int(x))

        # 4. ALGORITMO DE MAPEO
        for i, gcode_id_str in enumerate(gcode_ids):
            # Verificar si tenemos cama física para esta gente
            if i < len(available_indices):
                physical_idx = available_indices[i] # Índice real del panel (0-3)
                # Obtener datos del G-code
                info = injectors_data[gcode_id_str]
                name = info.get('name', f'Inyector {gcode_id_str}')
                hex_col = info.get('color', '#333333')
                # Actualizar el Strip Físico correspondiente
                strip = self.injectors[physical_idx]
                
                # Mostramos visualmente el mapeo: "Nombre"
                strip.update_strip_color(hex_col)
                strip.lbl_gcode_info.setText(f"{name}")
                strip.lbl_gcode_info.setStyleSheet(
                    f"font-weight: bold; color: {hex_col}; background: white;"
                )
               
            else:
                # Caso borde: El G-code pide más colores que inyectores habilitados
                self.log_message.emit(f"⚠️ Alerta: No hay inyector físico disponible para G-code ID {gcode_id_str}")