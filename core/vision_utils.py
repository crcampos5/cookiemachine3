"""
core/vision_utils.py
Funciones de procesamiento de imágenes (OpenCV) y geometría para la Cookie Machine.
No mantiene estado ni depende del hardware.
"""

import math
import cv2 as cv
import numpy as np

def find_cookie_centroids(image):
    """
    Detecta los centros de las galletas (objetos amarillos/dorados) en la imagen.
    Retorna:
        - list_centroides: Lista de tuplas (x, y) con los centros encontrados.
        - processed_image: La imagen con los contornos dibujados (para debug).
    """
    # Configuración de rangos de color (Amarillo/Dorado)
    # Adaptado de tu 'find_yellow' original
    color_bajos = np.array([20, 131, 0], np.uint8)
    color_altos = np.array([40, 255, 255], np.uint8)
    
    # Pre-procesamiento
    # Usamos un kernel de 5x5 para operaciones morfológicas
    kernel = np.ones((5,5), np.uint8)
    
    # Convertir a HSV
    imageHSV = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    
    # Máscara de color
    mask = cv.inRange(imageHSV, color_bajos, color_altos)
    
    # Erosionar para eliminar ruido
    erode_image = cv.erode(mask, kernel, iterations=1)

    # Encontrar contornos
    cnts, _ = cv.findContours(erode_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    
    list_centroides = []
    debug_image = image.copy() # Copia para no modificar la original si no se quiere
    
    for contour in cnts:
        area = cv.contourArea(contour)
        # Filtro de área para ignorar ruido pequeño o objetos muy grandes
        if 1000 < area < 2000000:
            M = cv.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                list_centroides.append((cx, cy))
                
                # Dibujar visualización (opcional, útil para debug)
                cv.drawContours(debug_image, [contour], -1, (0, 255, 0), 2)
                cv.circle(debug_image, (cx, cy), 5, (0, 0, 255), -1)

    return list_centroides, debug_image

def find_cookie_pose(image):
    """
    Detecta los centros y la orientación de las galletas.
    Retorna:
        - list_poses: Lista de tuplas (cx, cy, angle_degrees).
        - debug_image: Imagen con cajas rotadas dibujadas.
    """
    # 1. Configuración de color (Amarillo/Dorado)
    color_bajos = np.array([0, 0, 0], np.uint8)
    color_altos = np.array([24, 255, 255], np.uint8)
    
    # 2. Pre-procesamiento
    kernel = np.ones((5,5), np.uint8)
    imageHSV = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    mask = cv.inRange(imageHSV, color_bajos, color_altos)
    erode_image = cv.erode(mask, kernel, iterations=1)

    # 3. Encontrar contornos
    cnts, _ = cv.findContours(erode_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    
    list_poses = []
    debug_image = image.copy()
    
    for contour in cnts:
        area = cv.contourArea(contour)
        
        if 80000 < area < 100000:
            # --- Cálculo de Momentos (Centroide) ---
            M = cv.moments(contour)
            if M["m00"] == 0: continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            # --- Cálculo de Orientación (Bounding Box Rotado) ---
            # rect = ((center_x, center_y), (width, height), angle)
            rect = cv.minAreaRect(contour)
            box = cv.boxPoints(rect)
            box = np.int32(box)
            
            # Obtener el ángulo. En OpenCV 4.x el ángulo está entre [0, 90]
            # Ajustamos según el lado más largo para obtener la dirección principal
            (w_rect, h_rect) = rect[1]
            angle = rect[2]
            
            # Ajuste de lógica de ángulo para alinear el eje largo
            if w_rect < h_rect:
                angle = angle + 90
            
            # Convertir a lógica cartesiana estándar si es necesario (ajuste fino según cámara)
            # Aquí retornamos el ángulo tal cual para rotar el G-code.
            
            list_poses.append((cx, cy, angle))
            
            # Visualización
            cv.drawContours(debug_image, [box], 0, (0, 255, 0), 2)
            cv.circle(debug_image, (cx, cy), 5, (0, 0, 255), -1)
            # Dibujar texto de ángulo
            cv.putText(debug_image, f"{int(angle)} deg", (cx, cy - 20), 
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    return list_poses, debug_image

def sort_points_by_distance(points, reference_point):
    """
    Ordena una lista de puntos (x,y) según su cercanía a un punto de referencia.
    Útil para encontrar la galleta más cercana al centro de la cámara.
    """
    def distance(p1, p2):    
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    return sorted(points, key=lambda point: distance(point, reference_point))

def convert_pixel_to_mm(pixel, machine_pos, resolution=(640, 480), factor=3.2):
    """
    Convierte una coordenada de pixel (en la imagen) a una coordenada real de máquina (mm).
    
    Args:
        pixel: Tupla (x, y) detectada en la cámara.
        machine_pos: Tupla (X, Y) donde estaba la máquina al tomar la foto.
        resolution: Resolución de la cámara (ancho, alto).
        factor: Píxeles por milímetro (Calibración).
    
    Returns:
        (new_x, new_y): Coordenada absoluta en la máquina donde está el objeto.
    """
    centro_cam_x = resolution[0] / 2
    centro_cam_y = resolution[1] / 2

    # Distancia en píxeles desde el centro de la imagen
    delta_px_x = pixel[0] - centro_cam_x
    delta_px_y = pixel[1] - centro_cam_y

    # Convertir a milímetros
    # Nota: Los ejes de la cámara pueden estar rotados o invertidos respecto a la CNC.
    # En tu código original:
    # pixel_mm_x se sumaba a Y de máquina (?)
    # pixel_mm_y se sumaba a X de máquina (?)
    # Mantengo tu lógica original de intercambio de ejes/inversión:
    
    offset_mm_x = delta_px_y / factor
    offset_mm_y = delta_px_x / factor

    new_x = round(machine_pos[0] + offset_mm_x, 3)
    new_y = round(machine_pos[1] + offset_mm_y, 3)

    return (new_x, new_y)

def is_point_near(point1, point2, threshold=2.5):
    """
    Determina si dos puntos están lo suficientemente cerca para considerarse el mismo.
    """
    dist = math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    return dist <= threshold

def is_point_near_list(point, point_list, threshold=2.5):
    """
    Verifica si un punto está cerca de cualquiera de los puntos en una lista.
    """
    for p in point_list:
        if is_point_near(point, p, threshold):
            return True
    return False

def get_image_brightness(image):
    """
    Calcula el brillo promedio de la imagen.
    Retorna un valor float entre 0 (negro absoluto) y 255 (blanco absoluto).
    """
    if image is None: return 0.0
    
    # Convertimos a espacio de color HSV y extraemos el canal V (Value/Brillo)
    # Es más preciso que usar escala de grises para visión por color.
    hsv = cv.cvtColor(image, cv.COLOR_BGR2HSV)
    v_channel = hsv[:,:,2]
    
    return np.mean(v_channel)