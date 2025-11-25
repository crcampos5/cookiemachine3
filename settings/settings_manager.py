"""
core/settings_manager.py
Gestor centralizado para cargar y guardar configuraciones en JSON.
"""

import json
import os
from PySide6.QtCore import QObject, Signal

class SettingsManager(QObject):
    
    # Señal para avisar a la app si algo cambió (opcional, para recarga en caliente)
    settings_changed = Signal()

    def __init__(self, filepath="parameters/parameters.json"):
        super().__init__()
        self.filepath = filepath
        self.settings = {}
        self.load()

    def load(self):
        """ Carga el archivo JSON. Si falla, inicia valores por defecto. """
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                print(f"Configuración cargada desde {self.filepath}")
            except Exception as e:
                print(f"Error cargando JSON: {e}. Usando vacíos.")
                self.settings = {}
        else:
            print("Archivo de configuración no encontrado. Creando nuevo.")
            self.settings = {
                "puerto_maquina": "COM3",
                "puerto_sensor": "COM7",
                "velocidad_jog": 1000,
                "paso_jog": 10.0,
                "camara_indice": 0
            }
            self.save()

    def save(self):
        """ Guarda el diccionario actual en el archivo JSON. """
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            
            self.settings_changed.emit()
            print("Configuración guardada exitosamente.")
        except Exception as e:
            print(f"Error guardando configuración: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value