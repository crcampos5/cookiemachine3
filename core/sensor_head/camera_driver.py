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
    parameters_loaded = Signal(dict)

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
        self.target_brightness = 130  # Valor ideal de brillo (calibrar con una foto buena)
        self.auto_exposure_active = False
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

        # --- TRUCO: "Calentar" la cámara ---
        # Muchas cámaras ignoran la configuración si no están transmitiendo.
        # Leemos un frame vacío para forzar al driver a iniciar el stream.
        self.cap.read()
        QThread.msleep(200) # Esperamos 200ms a que el hardware despierte

        # ---------------------------------------------------------
        # 3. APLICAR PARÁMETROS DEL JSON (Si existen)
        # ---------------------------------------------------------
        # Buscamos 'exposure' o la errata 'expositure'
        req_exp = self.config.get("exposure", None)
        req_focus = self.config.get("focus", None)
        req_af = self.config.get("autofocus", None)

        # PASO A: Desactivar Autofocus (CRÍTICO: Hacerlo primero y esperar)
        if req_af is not None:
            val_af = 1 if (req_af is True or req_af == 1) else 0
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, val_af)
            # Esperar a que la lente mecánica se detenga o el driver cambie de modo
            QThread.msleep(300) 

        # PASO B: Configurar Exposición
        if req_exp is not None:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, float(req_exp))
            QThread.msleep(100)

        # PASO C: Configurar Foco Manual (Con reintento)
        if req_focus is not None:
            target_focus = float(req_focus)
            
            # Primer intento
            self.cap.set(cv2.CAP_PROP_FOCUS, target_focus)
            QThread.msleep(100)
            
            # Verificación: ¿Hizo caso?
            current_focus = self.cap.get(cv2.CAP_PROP_FOCUS)
            
            # Si el foco actual difiere del deseado (con un margen de error de 1)
            # O si se quedó "pegado" en un valor por defecto (como 144)
            if abs(current_focus - target_focus) > 2:
                print(f"[{self.camera_name}] Foco rebelde ({current_focus}). Reintentando poner a {target_focus}...")
                
                # A veces ayuda moverlo a 0 y luego al valor deseado para "despegarlo"
                self.cap.set(cv2.CAP_PROP_FOCUS, 0) 
                QThread.msleep(50)
                self.cap.set(cv2.CAP_PROP_FOCUS, target_focus)
                QThread.msleep(100)

        # ---------------------------------------------------------
        # 4. LEER VALORES REALES DEL HARDWARE (LO QUE PIDE EL USUARIO)
        # ---------------------------------------------------------
        

        self.is_running = True
        
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # --- LOGICA DE COMPENSACIÓN DE LUZ ---
                if self.auto_exposure_active:
                    # 1. Medir brillo actual
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    current_brightness = np.mean(gray)
                    
                    # 2. Obtener exposición actual
                    current_exp = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                    
                    # 3. Ajustar si estamos lejos del objetivo (Histéresis para que no parpadee)
                    error = self.target_brightness - current_brightness
                    
                    if abs(error) > 15: # Si la diferencia es notable
                        step = 1 if error > 0 else -1
                        new_exp = current_exp + step
                        
                        # Límites de seguridad (ej: entre -13 y -1)
                        if -13 <= new_exp <= -1:
                            self.cap.set(cv2.CAP_PROP_EXPOSURE, new_exp)
                            # Esperar un poco a que el hardware reaccione
                            QThread.msleep(200) 
                # -------------------------------------
                # Aplicar distorsión si se cargaron las matrices
                if self.calibration_enabled and self.camera_matrix is not None:
                    frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
                
                real_exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                real_focus = self.cap.get(cv2.CAP_PROP_FOCUS)
                real_af = self.cap.get(cv2.CAP_PROP_AUTOFOCUS)

                # Empaquetar para la GUI
                # Nota: real_exposure suele dar valores negativos en Windows (ej: -6)
                
                hardware_params = {
                    "exposure": f"{real_exposure:.1f}",
                    "focus": f"{real_focus:.1f}",
                    "autofocus": "ON" if real_af == 1 else "OFF"
                }
                
                # Emitir señal
                self.parameters_loaded.emit(hardware_params)
                
                self.frame_captured.emit(frame)
            else:
                break
            QThread.msleep(10)
        
        self.cap.release()

    @Slot(bool)
    def set_auto_exposure_logic(self, active: bool):
        self.auto_exposure_active = active

    @Slot()
    def stop(self):
        self.is_running = False