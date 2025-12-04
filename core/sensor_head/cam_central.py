"""
core/sensor_head/cam_central.py
Driver COMPLETO e INDEPENDIENTE para la Cámara Central (Visión Artificial).
"""
import cv2
import numpy as np
import os
from PySide6.QtCore import QObject, Signal, Slot, QThread
from settings.settings_manager import SettingsManager

class CamCentral(QObject):
    # Señales
    frame_captured = Signal(np.ndarray)
    error_occurred = Signal(str)
    parameters_loaded = Signal(dict)

    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.camera_name = "cam_central" # Nombre fijo
        self.settings = settings_manager
        
        # Valores por defecto
        self.camera_index = 0
        self.req_width = 640
        self.req_height = 480
        
        self.cap = None
        self.is_running = False
        
        # Cargar configuración específica de cam_central
        self.config = self.settings.get(self.camera_name, {})
        self._parse_config()
        
        # Calibración
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_enabled = False
        self._auto_load_calibration()
        
        self.target_brightness = 130
        self.auto_exposure_active = False

    def _parse_config(self):
        if not self.config: return
        for key, value in self.config.items():
            if "index" in key and isinstance(value, int):
                self.camera_index = value
            if "resolution" in key and isinstance(value, list) and len(value) == 2:
                self.req_width = value[0]
                self.req_height = value[1]

    def _auto_load_calibration(self):
        # Busca en parameters/camcentral/
        folder_name = self.camera_name.replace("_", "") 
        base_path = f"parameters/{folder_name}"
        matrix_path = f"{base_path}/CameraMatrix.npy"
        dist_path = f"{base_path}/DistMatrix.npy"
        
        if os.path.exists(matrix_path) and os.path.exists(dist_path):
            try:
                self.camera_matrix = np.load(matrix_path)
                self.dist_coeffs = np.load(dist_path)
                self.calibration_enabled = True
            except Exception:
                self.calibration_enabled = False

    @Slot()
    def start(self):
        if self.is_running: return
        
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.error_occurred.emit(f"Error al abrir {self.camera_name}")
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.req_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.req_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Calentamiento
        self.cap.read()
        QThread.msleep(200)

        # Configurar Hardware
        req_exp = self.config.get("exposure", None)
        req_focus = self.config.get("focus", None)
        req_af = self.config.get("autofocus", None)

        if req_af is not None:
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1 if req_af else 0)
        
        if req_exp is not None:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, float(req_exp))

        if req_focus is not None:
            tgt = float(req_focus)
            self.cap.set(cv2.CAP_PROP_FOCUS, tgt)
            # Reintento de foco si falla
            QThread.msleep(100)
            if abs(self.cap.get(cv2.CAP_PROP_FOCUS) - tgt) > 2:
                self.cap.set(cv2.CAP_PROP_FOCUS, 0)
                QThread.msleep(50)
                self.cap.set(cv2.CAP_PROP_FOCUS, tgt)

        self.is_running = True
        
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # 1. Auto-Exposición Soft
                if self.auto_exposure_active:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    curr_b = np.mean(gray)
                    err = self.target_brightness - curr_b
                    if abs(err) > 15:
                        curr_exp = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                        step = 1 if err > 0 else -1
                        new_exp = curr_exp + step
                        if -13 <= new_exp <= -1:
                            self.cap.set(cv2.CAP_PROP_EXPOSURE, new_exp)
                            QThread.msleep(150)

                # 2. Corregir Distorsión
                if self.calibration_enabled and self.camera_matrix is not None:
                    frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
                
                # 3. Emitir
                params = {
                    "exposure": f"{self.cap.get(cv2.CAP_PROP_EXPOSURE):.1f}",
                    "focus": f"{self.cap.get(cv2.CAP_PROP_FOCUS):.1f}",
                    "autofocus": "ON" if self.cap.get(cv2.CAP_PROP_AUTOFOCUS) == 1 else "OFF"
                }
                self.parameters_loaded.emit(params)
                self.frame_captured.emit(frame)
            else:
                self.error_occurred.emit(f"Fallo lectura {self.camera_name}")
                break
            QThread.msleep(10)
        
        self.cap.release()

    @Slot()
    def stop(self):
        self.is_running = False