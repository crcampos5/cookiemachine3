"""
gui/dialogs/settings_dialog.py
Diálogo recursivo capaz de editar JSONs complejos con listas y diccionarios anidados.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, 
                               QDialogButtonBox, QLineEdit, QSpinBox, 
                               QDoubleSpinBox, QCheckBox, QLabel, QScrollArea, 
                               QWidget, QGroupBox, QHBoxLayout)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración Avanzada")
        self.resize(500, 700) # Un poco más grande para anidados
        
        self.manager = settings_manager
        # Hacemos una copia profunda para trabajar (requiere import copy si fuera muy complejo, 
        # pero para JSON estándar esto suele bastar o usamos json loads/dumps)
        import json
        self.temp_settings = json.loads(json.dumps(self.manager.settings))
        
        # Diccionario para mapear "ruta/de/clave" -> Widget(s)
        self.widget_map = {} 

        # Layout Principal
        main_layout = QVBoxLayout(self)

        # Área de Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.main_form_layout = QVBoxLayout(content_widget)
        
        # --- GENERACIÓN RECURSIVA ---
        self.populate_recursive(self.temp_settings, self.main_form_layout)
        
        #self.main_form_layout.addStretch() # Empujar todo hacia arriba
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def populate_recursive(self, data, parent_layout, prefix=""):
        """
        Recorre el diccionario 'data' y crea widgets en 'parent_layout'.
        Si encuentra un dict, se llama a sí misma.
        'prefix' rastrea la ruta de la clave (ej: "modes/Boquilla").
        """
        for key, value in data.items():
            # Crear la ruta única para este dato
            current_path = f"{prefix}/{key}" if prefix else key
            label_text = key.replace("_", " ").title()
            
            # CASO 1: DICCIONARIO ANIDADO (Recursión)
            if isinstance(value, dict):
                group = QGroupBox(label_text)
                group.setStyleSheet("QGroupBox { font-weight: bold; }")
                group_layout = QVBoxLayout()
                group.setLayout(group_layout)
                
                # Llamada recursiva para llenar el grupo
                self.populate_recursive(value, group_layout, current_path)
                parent_layout.addWidget(group)

            # CASO 2: LISTA (Asumimos lista de números, ej: coordenadas)
            elif isinstance(value, list):
                # Crear un layout horizontal para poner los números seguidos
                row_widget = QWidget()
                row_layout = QFormLayout(row_widget)
                row_layout.setContentsMargins(0,0,0,0)
                
                h_layout = QHBoxLayout()
                widget_list = []
                
                for item in value:
                    w = self._create_widget_for_value(item)
                    h_layout.addWidget(w)
                    widget_list.append(w)
                
                h_layout.addStretch() # Que no se estiren
                row_layout.addRow(label_text + ":", h_layout)
                parent_layout.addWidget(row_widget)
                
                # Guardamos la lista de widgets
                self.widget_map[current_path] = widget_list

            # CASO 3: VALOR SIMPLE (int, float, bool, str)
            else:
                row_widget = QWidget()
                row_layout = QFormLayout(row_widget)
                row_layout.setContentsMargins(0,0,0,0)
                
                widget = self._create_widget_for_value(value)
                row_layout.addRow(label_text + ":", widget)
                parent_layout.addWidget(row_widget)
                
                # Guardamos el widget único
                self.widget_map[current_path] = widget

    def _create_widget_for_value(self, value):
        """ Helper para crear el widget correcto según el tipo de dato. """
        if isinstance(value, bool):
            w = QCheckBox()
            w.setChecked(value)
            return w
        elif isinstance(value, int):
            w = QSpinBox()
            w.setRange(-99999, 99999)
            w.setValue(value)
            return w
        elif isinstance(value, float):
            w = QDoubleSpinBox()
            w.setRange(-99999.0, 99999.0)
            w.setDecimals(3)
            w.setValue(value)
            return w
        else:
            w = QLineEdit(str(value))
            return w

    def save_and_close(self):
        """ Reconstruye el diccionario desde los widgets y guarda. """
        
        for path, widgets in self.widget_map.items():
            # 'path' es algo como "modes/Boquilla" o "resolution"
            keys = path.split('/')
            
            # Navegar hasta el contenedor padre en self.temp_settings
            # Ej: si path es "modes/Boquilla", target será el dict "modes"
            target = self.temp_settings
            for k in keys[:-1]:
                target = target[k]
            
            last_key = keys[-1]
            
            # Extraer valor(es)
            if isinstance(widgets, list): # Era una lista (coordenadas)
                new_values = []
                for w in widgets:
                    new_values.append(self._get_value_from_widget(w))
                target[last_key] = new_values
            else: # Era un valor simple
                target[last_key] = self._get_value_from_widget(widgets)
        
        # Actualizar el manager y guardar
        self.manager.settings = self.temp_settings
        self.manager.save()
        self.accept()

    def _get_value_from_widget(self, widget):
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            return widget.value()
        elif isinstance(widget, QLineEdit):
            # Intentar convertir a numero si es posible para mantener tipos
            text = widget.text()
            try:
                return int(text)
            except ValueError:
                try:
                    return float(text)
                except ValueError:
                    return text
        return None