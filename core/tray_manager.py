"""
core/tray_manager.py
Gestiona la geometría de la bandeja de trabajo (Matriz de Galletas) 
y verifica los límites de seguridad usando la configuración global.
"""

import re
import numpy as np
from PySide6.QtCore import QObject
from settings.settings_manager import SettingsManager

class TrayManager(QObject):

    def __init__(self, settings_manager: SettingsManager) -> None:
        super().__init__()
        self.settings = settings_manager

    def generar_matriz_cuadrantes(self, tipo_mesa='Toda'):
        """
        Genera las coordenadas (X, Y) teóricas para cada galleta en la bandeja.
        Usa 'quadrant_size' y 'table_size' definidos en parameters.json.
        """
        
        # 1. Obtener dimensiones de la configuración
        # table_size: [filas, columnas], ej: [7, 5]
        table_size = self.settings.get("table_size", [7, 6]) 
        rows = int(table_size[0])
        cols = int(table_size[1])

        # quadrant_size: [ancho_mm, alto_mm], ej: [103, 103]
        q_size = self.settings.get("quadrant_size", [103.0, 103.0])
        base_w = float(q_size[0])
        base_h = float(q_size[1])

        # 2. Calcular espaciados según el modo seleccionado
        # Si es intercalado, saltamos un cuadrante (doble distancia)
        espaciado_x = base_w
        espaciado_y = base_h

        if tipo_mesa == 'Intercalado en Y':
            espaciado_y = base_h * 2
        elif tipo_mesa == 'Intercalado en X':
            espaciado_x = base_w * 2
        elif tipo_mesa == 'Intercalado en XY':
            espaciado_x = base_w * 2
            espaciado_y = base_h * 2
        
        # 3. Crear matriz numpy para guardar coordenadas [x, y]
        matriz_coordenadas = np.zeros((rows, cols, 2))

        for i in range(rows):  # Filas
            for j in range(cols):  # Columnas
                x = espaciado_x * j
                # Asumimos que las filas van hacia Y positivo,
                y = espaciado_y * i #* -1
                matriz_coordenadas[i, j] = [x, y]

        return matriz_coordenadas

    def verificar_limites_gcode(self, gcode_lines, x_min, x_max, y_min, y_max):
        """
        Verifica si algún movimiento en el G-code se sale de la zona segura.
        Retorna True si es seguro, False si se sale.
        """
        patron_x = re.compile(r'X([-\d.]+)')
        patron_y = re.compile(r'Y([-\d.]+)')

        for linea in gcode_lines:
            x_match = patron_x.search(linea)
            y_match = patron_y.search(linea)

            if x_match and y_match:
                x = float(x_match.group(1))
                y = float(y_match.group(1))
                if not (x_min <= x <= x_max and y_min <= y <= y_max):
                    return False

            elif x_match:
                x = float(x_match.group(1))
                if not (x_min <= x <= x_max): return False

            elif y_match:
                y = float(y_match.group(1))
                if not (y_min <= y <= y_max): return False

        return True