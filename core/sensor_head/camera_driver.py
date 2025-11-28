"""
core/sensor_head/camera_driver.py
Maneja la captura de video configurándose automáticamente desde el JSON de parámetros.
"""
import cv2
import numpy as np
import os
from PySide6.QtCore import QObject, Signal, Slot, QThread

from settings.settings_manager import SettingsManager

class CameraDriver(QObject):
    frame_captured = Signal(np.ndarray)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self, camera_name: str, settings_manager: SettingsManager):
        super().__init__()
        self.camera_name = camera_name
        self.settings = settings_manager
        
        # --- 1. Leer configuración del JSON ---
        # Obtenemos el diccionario completo de la cámara (ej. todo lo que está dentro de "cam_central")
        self.config = self.settings.get(camera_name, {})
        
        # --- 2. Buscar Index y Resolución Dinámicamente ---
        # Esto permite que funcione con "cam_laser_index" o "cam_central_index" sin cambiar código
        self.camera_index = 0
        self.req_width = 640
        self.req_height = 480
        
        self._parse_config()

        self.cap = None
        self.is_running = False
        
        # --- 3. Cargar Calibración Automáticamente ---
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_enabled = False
        self._auto_load_calibration()

    def _parse_config(self):
        """Busca las llaves de índice y resolución dentro del diccionario de configuración."""
        if not self.config:
            print(f"Advertencia: No se encontró configuración para '{self.camera_name}'")
            return

        # Buscar índice (busca cualquier llave que contenga "index")
        for key, value in self.config.items():
            if "index" in key and isinstance(value, int):
                self.camera_index = value
                
            # Buscar resolución (busca cualquier llave que contenga "resolution")
            if "resolution" in key and isinstance(value, list) and len(value) == 2:
                self.req_width = value[0]
                self.req_height = value[1]

        #print(f"Configurando {self.camera_name}: Index={self.camera_index}, Res={self.req_width}x{self.req_height}")

    def _auto_load_calibration(self):
        """
        Deduce la ruta de los archivos de calibración basándose en el nombre.
        Ejemplo: Si nombre es 'cam_central', busca en 'parameters/camcentral/'
        """
        # Tu carpeta física es 'camcentral' pero el json dice 'cam_central'.
        # Quitamos el guion bajo para que coincida con la carpeta.
        folder_name = self.camera_name.replace("_", "") 
        base_path = f"parameters/{folder_name}"
        
        matrix_path = f"{base_path}/CameraMatrix.npy"
        dist_path = f"{base_path}/DistMatrix.npy"
        
        self.load_calibration_matrices(matrix_path, dist_path)

    def load_calibration_matrices(self, matrix_path: str, dist_path: str):
        if os.path.exists(matrix_path) and os.path.exists(dist_path):
            try:
                self.camera_matrix = np.load(matrix_path)
                self.dist_coeffs = np.load(dist_path)
                self.calibration_enabled = True
                self.status_changed.emit(f"Calibración cargada para {self.camera_name}")
                print(f"Calibración cargada desde: {matrix_path}")
            except Exception as e:
                self.calibration_enabled = False
                print(f"Error cargando matrices para {self.camera_name}: {e}")
        else:
            self.calibration_enabled = False
            # Opcional: imprimir aviso solo si se esperaba calibración
            # print(f"No se encontraron archivos de calibración en {matrix_path}")

    @Slot()
    def start(self):
        if self.is_running: return
        
        # Inicializar cámara con el índice obtenido del JSON
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            self.error_occurred.emit(f"Error al abrir cámara {self.camera_name} (idx: {self.camera_index})")
            return

        # Aplicar resolución obtenida del JSON
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.req_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.req_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.is_running = True
        
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # Aplicar distorsión si se cargaron las matrices
                if self.calibration_enabled and self.camera_matrix is not None:
                    frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
                
                self.frame_captured.emit(frame)
            else:
                break
            QThread.msleep(10)
        
        self.cap.release()

    @Slot()
    def stop(self):
        self.is_running = False