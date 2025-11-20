"""
core/sensor_head/camera_driver.py
Maneja la captura de video de una cámara USB específica.
"""
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, QThread

class CameraDriver(QObject):
    frame_captured = Signal(np.ndarray)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(self, camera_index: int):
        super().__init__()
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False

    @Slot()
    def start(self):
        if self.is_running: return
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.error_occurred.emit(f"Error al abrir cámara {self.camera_index}")
            return
        self.is_running = True
        
        while self.is_running:
            ret, frame = self.cap.read()
            if ret: self.frame_captured.emit(frame)
            else: break
            QThread.msleep(10) # Pequeña pausa
        
        self.cap.release()

    @Slot()
    def stop(self):
        self.is_running = False