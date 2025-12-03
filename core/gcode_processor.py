"""
core/gcode_processor.py
Módulo de procesamiento matemático puro para G-code.
Se encarga de leer archivos, aplicar offsets, deformaciones por altura y suavizado.
"""

import math
import re
import json

class GcodeProcessor:

    def __init__(self):
        pass

    def parse_custom_gcode(self, file_path):
        """
        Parsea el formato .cgc agrupando las operaciones por inyector.
        
        Retorna:
            - metadata (dict): Información del encabezado JSON.
            - injectors (dict): Configuración de cada inyector (color, nozzle, name).
            - operations (list): Lista de diccionarios, donde cada uno representa una
                                 sección continua de trabajo con un inyector específico.
                                 Formato: {'injector_id': int, 'gcode_lines': [str, str, ...]}
        """
        metadata = {}
        injectors = {}
        operations = []
        
        # Buffer para el JSON del header
        json_buffer = ""
        reading_json = False
        
        # Estado actual de la operación
        current_op = None 

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error leyendo archivo: {e}")
            return {}, {}, []

        for line in lines:
            original_line = line
            line = line.strip()
            if not line: continue

            # --- 1. PARSEO DEL HEADER (JSON) ---
            if "HEADER START" in line:
                reading_json = True
                continue
            if "HEADER END" in line:
                reading_json = False
                try:
                    metadata = json.loads(json_buffer)
                except json.JSONDecodeError as e:
                    print(f"Error parseando JSON header: {e}")
                continue
            
            if reading_json:
                # Quitamos el punto y coma inicial para reconstruir el JSON válido
                clean_part = line.lstrip(';').strip()
                json_buffer += clean_part
                continue

            # --- 2. PARSEO DE DEFINICIONES DE INYECTORES ---
            # Ejemplo: ; DEFINE_INJECTOR ID=0 COLOR="#000000ff" NAME="Borde Negro" NOZZLE="2.0mm"
            if "DEFINE_INJECTOR" in line:
                t_id = re.search(r'ID=(\d+)', line)
                t_color = re.search(r'COLOR="([^"]+)"', line)
                t_name = re.search(r'NAME="([^"]+)"', line)
                t_nozzle = re.search(r'NOZZLE="([^"]+)"', line)
                
                if t_id:
                    tid = str(t_id.group(1))
                    injectors[tid] = {
                        "color": t_color.group(1) if t_color else "#FFFFFF",
                        "name": t_name.group(1) if t_name else f"Injector {tid}",
                        "nozzle": t_nozzle.group(1) if t_nozzle else "generic"
                    }
                continue

            # --- 3. PARSEO DEL CUERPO (OPERACIONES POR BLOQUE) ---
            
            # Detectar cambio de inyector -> Inicia nueva operación
            if "CHANGE_INJECTOR" in line:
                # 1. Si ya había una operación en curso, la guardamos en la lista final
                if current_op is not None:
                    operations.append(current_op)
                
                # 2. Extraemos el ID del nuevo inyector
                t_id = re.search(r'ID=(\d+)', line)
                new_id = int(t_id.group(1)) if t_id else -1
                
                # 3. Creamos el nuevo bloque de operación
                current_op = {
                    'injector_id': new_id,
                    'gcode_lines': []
                }
                continue

            # Detectar líneas de G-code (G0, G1, M8, etc.) o coordenadas
            # Se asume que cualquier línea que no sea comentario de estructura es G-code
            if not line.startswith(';') or line.startswith('('):
                # Solo agregamos si tenemos una operación activa (un inyector seleccionado)
                if current_op is not None:
                    current_op['gcode_lines'].append(original_line.strip())
                else:
                    # Caso borde: G-code antes del primer CHANGE_INJECTOR
                    # Podríamos ignorarlo o crear una operación por defecto.
                    pass

        # --- FINALIZACIÓN ---
        # Al terminar de leer el archivo, si quedó una operación abierta, la agregamos
        if current_op is not None and current_op['gcode_lines']:
            operations.append(current_op)

        return metadata, injectors, operations

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
    
    # --- ESCANEO ---

    def resample_gcode_scan(self, gcode_text, step_distance):
        """
        1. G1: Se interpolan a distancia exacta (cuerda continua).
        2. G0: Se mantienen como desplazamientos (sin interpolar) y reinician el conteo.
        3. Z y F: Se eliminan por completo.
        """
        new_gcode = []
        
        # Regex para buscar coordenadas
        rx = re.compile(r'X([\d\.-]+)')
        ry = re.compile(r'Y([\d\.-]+)')

        # Estado actual de la máquina
        curr_x, curr_y = 0.0, 0.0
        
        # Acumulador de distancia sobrante (solo para movimientos G1 continuos)
        distance_overflow = 0.0 
        
        lines = gcode_text #.splitlines()
        
        for line in lines:
            upper_line = line.strip().upper()
            
            # Ignorar líneas vacías o comentarios
            if not upper_line or upper_line.startswith(';') or upper_line.startswith('('):
                continue

            # Detectar si hay coordenadas X o Y
            mx = rx.search(upper_line)
            my = ry.search(upper_line)
            
            # Si la línea no tiene X ni Y, la ignoramos (ej: cambios solo de Z o F)
            if not mx and not my:
                continue

            # Obtener destino
            target_x = float(mx.group(1)) if mx else curr_x
            target_y = float(my.group(1)) if my else curr_y

            # --- CASO 1: MOVIMIENTO RÁPIDO (G0) ---
            if upper_line.startswith('G0'):
                # 1. Escribimos el movimiento tal cual (pero limpio, solo X Y)
                new_gcode.append(f"G0 X{target_x:.3f} Y{target_y:.3f}")
                
                # 2. Actualizamos posición actual
                curr_x = target_x
                curr_y = target_y
                
                # 3. ¡IMPORTANTE! Reiniciamos el acumulador.
                # La próxima línea G1 empezará una trayectoria nueva desde 0.
                distance_overflow = 0.0
                
                continue

            # --- CASO 2: TRAYECTORIA DE TRABAJO (G1) ---
            elif upper_line.startswith('G1'):
                
                # Calcular longitud del segmento
                dx = target_x - curr_x
                dy = target_y - curr_y
                segment_length = math.sqrt(dx**2 + dy**2)
                
                # Ignorar segmentos de longitud 0
                if segment_length <= 0.00001:
                    continue

                # Vectores unitarios
                ux = dx / segment_length
                uy = dy / segment_length
                
                # Calcular dónde cae el primer punto usando lo que sobró del anterior
                current_dist_on_segment = step_distance - distance_overflow
                
                while current_dist_on_segment <= segment_length:
                    # Calcular punto
                    new_x = curr_x + (ux * current_dist_on_segment)
                    new_y = curr_y + (uy * current_dist_on_segment)
                    
                    # Escribir punto interpolado
                    new_gcode.append(f"G1 X{new_x:.3f} Y{new_y:.3f}")
                    
                    current_dist_on_segment += step_distance
                
                # Calcular el sobrante para el siguiente segmento G1
                distance_overflow = segment_length - (current_dist_on_segment - step_distance)
                
                # Actualizar posición "real" para el cálculo matemático
                curr_x = target_x
                curr_y = target_y

        return new_gcode