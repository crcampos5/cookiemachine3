"""
core/template.py
Gestiona la geometría de la bandeja de trabajo (Matriz de Galletas) 
y verifica los límites de seguridad.
"""

import re
import numpy as np

class TrayManager:

    def __init__(self) -> None:
        pass

    def generar_matriz_coordenadas(self, tipo_mesa='Toda'):
        """
        Genera las coordenadas (X, Y) teóricas para cada galleta en la bandeja.
        Devuelve una matriz numpy de 7 filas x 6 columnas.
        """
        # Definir espaciados según el tipo de mesa configurado
        if tipo_mesa == 'Intercalado en Y':
            espaciado_x = 103
            espaciado_y = 206
        elif tipo_mesa == 'Intercalado en X':
            espaciado_x = 206
            espaciado_y = 103
        elif tipo_mesa == 'Intercalado en XY':
            espaciado_x = 206
            espaciado_y = 206
        else: # 'Toda' (Default)
            espaciado_x = 103
            espaciado_y = 103

        # Crear matriz 7x6 para guardar coordenadas [x, y]
        matriz_coordenadas = np.zeros((7, 6, 2))

        for i in range(7):  # Filas
            for j in range(6):  # Columnas
                x = espaciado_x * j
                # Asumimos que las filas van hacia Y negativo
                y = espaciado_y * i * -1 
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
                    # print(f"Fuera de límites: {linea.strip()}") # Debug
                    return False

            elif x_match:
                x = float(x_match.group(1))
                if not (x_min <= x <= x_max): return False

            elif y_match:
                y = float(y_match.group(1))
                if not (y_min <= y <= y_max): return False

        return True