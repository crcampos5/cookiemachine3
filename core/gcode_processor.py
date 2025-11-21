"""
core/gcode_processor.py
Módulo de procesamiento matemático puro para G-code.
Se encarga de leer archivos, aplicar offsets, deformaciones por altura y suavizado.
"""

import math
import re

class GcodeProcessor:

    def __init__(self):
        pass

    # --- LÓGICA DE LECTURA Y PARSEO (NUEVO) ---

    def parse_gcode_file(self, file_path):
        """
        Lee el archivo desde el disco y separa las líneas de dibujo 
        de los puntos de escaneo (marcados con 'point_scan').
        
        Retorna: (gcode_draw, gcode_scan)
        """
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return [], []

        gcode_draw = []
        gcode_scan = []
        
        # Regex para encontrar coordenadas (ej: X10.5)
        pattern = re.compile(r'([A-Z][^A-Z\s]*)')

        for line in lines:
            clean_line = line.strip()
            if not clean_line: continue
            
            # Caso A: Puntos de escaneo (comentario especial 'point_scan')
            if 'point_scan' in clean_line:
                # Extraer solo X e Y para el movimiento de escaneo
                parts = pattern.findall(clean_line)
                valid_parts = [p for p in parts if p.startswith('X') or p.startswith('Y')]
                if valid_parts:
                    # Creamos una línea de movimiento rápido G0
                    scan_line = "G0 " + " ".join(valid_parts)
                    gcode_scan.append(scan_line)
            
            # Caso B: Líneas de dibujo normales
            else:
                # Ignoramos comentarios puros de G-code
                if clean_line.startswith(';') or clean_line.startswith('('):
                    continue
                gcode_draw.append(clean_line)
        
        return gcode_draw, gcode_scan

    # --- LÓGICA DE DEFORMACIÓN Z (Ex-Scanner) ---

    def calcular_z_umbral(self, puntos_xyz, altura_piso, nozzle_spacing, porcentaje_umbral=0.6):
        """
        Calcula un umbral Z para filtrar puntos erróneos del sensor láser.
        """
        alturas_cercanas = [p[2] for p in puntos_xyz if abs(p[2] - altura_piso) <= nozzle_spacing]
        
        if not alturas_cercanas:
            alturas_z = [p[2] for p in puntos_xyz]
        else:
            alturas_z = alturas_cercanas # Corregido: usar las cercanas si existen

        if not alturas_z: return 0.0

        z_min = min(alturas_z)
        z_max = max(alturas_z)
        return z_min + porcentaje_umbral * (z_max - z_min)

    def find_closest_coordinate(self, x, y, coordinates, umbral=None):
        """ Encuentra el punto (x,y,z) más cercano en la nube de puntos escaneada. """
        candidatos = coordinates
        if umbral is not None:
            filtrados = [c for c in coordinates if c[2] > umbral]
            if filtrados:
                candidatos = filtrados
        
        if not candidatos: return (0,0,0)

        # Distancia Euclidiana
        return min(candidatos, key=lambda c: math.sqrt((c[0]-x)**2 + (c[1]-y)**2))

    def aplicar_mapa_alturas(self, gcode_origin, list_alturas, z_umbral):
        """
        Aplica la deformación en Z al G-code original.
        """
        updated_gcode = []
        prev_x, prev_y = None, None
        patron_xy = re.compile(r'X([-+]?\d*\.\d+)\s*Y([-+]?\d*\.\d+)')

        for line in gcode_origin:
            line = line.strip()
            match = patron_xy.search(line)
            
            if match:
                prev_x = float(match.group(1))
                prev_y = float(match.group(2))

            # G1: Trabajo -> Aplicar altura real
            if line.startswith('G1') and match:
                x, y = float(match.group(1)), float(match.group(2))
                closest = self.find_closest_coordinate(x, y, list_alturas, z_umbral)
                z_real = round(closest[2], 3)

                if 'F' in line:
                    parts = re.split(r'(F[-+]?\d*\.\d*)', line, maxsplit=1)
                    new_line = f"{parts[0]}Z{z_real}{parts[1]}"
                    if len(parts) > 2: new_line += parts[2]
                else:
                    new_line = f"{line}Z{z_real}"
                updated_gcode.append(new_line)

            # G0 Z11: Seguridad -> Aplicar Z seguro relativo
            elif line.startswith('G0') and 'Z11.000' in line:
                if prev_x is not None and prev_y is not None:
                    closest = self.find_closest_coordinate(prev_x, prev_y, list_alturas, z_umbral)
                    z_safe = round(closest[2] + 10, 3)
                    new_line = re.sub(r'Z11\.000', f'Z{z_safe}', line) + " ; z_safe"
                    updated_gcode.append(new_line)
                else:
                    updated_gcode.append(line)

            # G1 Z4: Aproximación -> Activar M8
            elif line.startswith('G1') and 'Z4.000' in line:
                if prev_x is not None and prev_y is not None:
                    closest = self.find_closest_coordinate(prev_x, prev_y, list_alturas, z_umbral)
                    z_real = round(closest[2], 3)
                    new_line = re.sub(r'Z4\.000', f'Z{z_real}', line) + " ; z_down"
                    
                    updated_gcode.append(new_line)
                    updated_gcode.append("M8") 
                else:
                    updated_gcode.append(line)
            else:
                updated_gcode.append(line)

        return updated_gcode

    def suavizar_z(self, gcode_lines, window_size=3):
        """ Aplica media móvil a Z. """
        z_values = []
        z_indices = []
    
        for idx, line in enumerate(gcode_lines):
            if 'G0' in line: continue
            match = re.search(r'Z([-+]?[0-9]*\.?[0-9]+)', line)
            if match:
                z_values.append(float(match.group(1)))
                z_indices.append(idx)
    
        if not z_values: return gcode_lines

        smoothed_z = []
        for i in range(len(z_values)):
            start = max(0, i - window_size // 2)
            end = min(len(z_values), i + window_size // 2 + 1)
            window = z_values[start:end]
            smoothed_z.append(sum(window) / len(window))
    
        for idx, z_idx in enumerate(z_indices):
            line = gcode_lines[z_idx]
            new_z = f"Z{smoothed_z[idx]:.3f}"
            gcode_lines[z_idx] = re.sub(r'Z[-+]?[0-9]*\.?[0-9]+', new_z, line)
    
        return gcode_lines

    def modificar_altura_activacion(self, gcode, altura_activacion):
        """ Ajusta la altura de disparo. """
        updated = []
        z_down_line = None

        for i, line in enumerate(gcode):
            if '; z_down' in line:
                z_down_line = line

            if 'M8' in line and z_down_line:
                prev_line = updated[-1]
                z_match = re.search(r'Z([-+]?\d*\.\d+)', prev_line)
                
                if z_match:
                    z_val = float(z_match.group(1))
                    new_z = z_val + altura_activacion
                    new_line = re.sub(r'Z([-+]?\d*\.\d+)', f'Z{new_z}', prev_line)
                    updated[-1] = new_line + " ; activation_height"
                
                updated.append(line)
                updated.append(z_down_line)
                z_down_line = None
            else:
                updated.append(line)
        return updated

    def sumar_offset_xy(self, gcode_list, offset_x, offset_y):
        """ Desplaza todo el G-code en X e Y. """
        new_gcode = []
        patron_x = re.compile(r'X([-\d.]+)')
        patron_y = re.compile(r'Y([-\d.]+)')

        for line in gcode_list:
            new_line = line
            x_match = patron_x.search(line)
            y_match = patron_y.search(line)
            
            if x_match:
                val = float(x_match.group(1)) + offset_x
                new_line = patron_x.sub(f'X{val:.3f}', new_line)
            
            if y_match:
                val = float(y_match.group(1)) + offset_y
                new_line = patron_y.sub(f'Y{val:.3f}', new_line)
                
            new_gcode.append(new_line)
        return new_gcode