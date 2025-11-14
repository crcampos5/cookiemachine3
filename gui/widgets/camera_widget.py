"""
gui/widgets/camera_widget.py
Widget para mostrar un feed de video de OpenCV (cámara) en un hilo 
separado usando el patrón QObject/QThread.

Versión 3: Simple. Sin botones. Se controla externamente.
"""

import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtGui import QImage, QPixmap
# Se eliminan imports de botones
from PySide6.QtWidgets import (QGroupBox, QLabel, QVBoxLayout, QSizePolicy)

# --- (CameraWorker no cambia) ---
#
class CameraWorker(QObject):
    """
    El 'trabajador' que vive en el hilo secundario.
    Se encarga de abrir la cámara y leer los fotogramas.
    """
    frame_ready = Signal(np.ndarray)
    log_message = Signal(str)
    
    def __init__(self, camera_index: int):
        super().__init__()
        self.camera_index = camera_index
        self.cap = None
        self.is_running = True

    @Slot()
    def run(self):
        """
        El bucle principal del trabajador. Se ejecuta en el QThread.
        """
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            self.log_message.emit(f"Error: No se pudo abrir la cámara {self.camera_index}.")
            return
            
        self.log_message.emit(f"Cámara {self.camera_index} iniciada.")

        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    self.log_message.emit(f"Cámara {self.camera_index} desconectada.")
                    self.is_running = False
                    break
                
                self.frame_ready.emit(frame)
                
            except Exception as e:
                self.log_message.emit(f"Error en cámara {self.camera_index}: {e}")
                self.is_running = False
                break
        
        if self.cap:
            self.cap.release()
        self.log_message.emit(f"Cámara {self.camera_index} detenida.")

    def stop(self):
        """
        Indica al bucle que debe detenerse.
        """
        self.is_running = False

# --- (CameraWidget SÍ cambia) ---
class CameraWidget(QGroupBox):
    """
    El 'widget' que vive en el hilo principal.
    Muestra los fotogramas. Se controla con start_feed() y stop_feed().
    """
    log_message = Signal(str)

    def __init__(self, camera_index: int, title: str = "Cámara", parent=None):
        super().__init__(f"{title} (ID: {camera_index})", parent)
        
        # --- 1. Widgets de la GUI (Simplificado) ---
        self.image_label = QLabel("Cámara detenida")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #000; color: #FFF;")
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        # --- 2. Layout (Simplificado) ---
        # Se eliminaron los botones y 'controls_layout'
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.image_label, stretch=1) # El label ocupa todo el espacio
        self.setLayout(layout)
        
        # --- 3. Configuración del Hilo y Trabajador ---
        self.worker_thread = QThread()
        self.worker_thread.setObjectName(f"CameraThread_{camera_index}")
        
        self.worker = CameraWorker(camera_index)
        self.worker.moveToThread(self.worker_thread)
        
        # --- 4. Conexiones ---
        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.finished.connect(self._on_feed_stopped) 
        self.worker.frame_ready.connect(self.set_image)
        self.worker.log_message.connect(self.log_message)
        
        # --- 5. Estado Inicial ---
        self._on_feed_stopped() # Poner la GUI en estado "detenido"

    @Slot(np.ndarray)
    def set_image(self, frame: np.ndarray):
        """
        Slot: Se ejecuta en el hilo principal.
        Convierte el fotograma de OpenCV (BGR) a un QPixmap (RGB)
        y lo muestra en el QLabel.
        """
        #
        try:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            q_pixmap = QPixmap.fromImage(q_image)
            self.image_label.setPixmap(q_pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            print(f"Error al actualizar imagen: {e}")

    @Slot()
    def start_feed(self):
        """
        Slot público para iniciar el feed de esta cámara.
        (Llamado por una función externa)
        """
        if not self.worker_thread.isRunning():
            print(f"Iniciando feed de cámara {self.worker.camera_index}...")
            self.worker.is_running = True 
            self.worker_thread.start()
            self.image_label.setText("Iniciando cámara...")

    @Slot()
    def stop_feed(self):
        """
        Slot público para detener el feed.
        (Llamado por una función externa o al cerrar)
        """
        if self.worker_thread.isRunning():
            print(f"Deteniendo feed de {self.worker.camera_index}...")
            self.worker.stop() # Le dice al bucle run() que pare
            self.worker_thread.quit() # Pide al hilo que termine
            
    @Slot()
    def _on_feed_stopped(self):
        """
        Slot privado llamado cuando el hilo 'finished' se emite.
        Limpia la GUI.
        """
        print(f"Feed de cámara {self.worker.camera_index} detenido.")
        self.image_label.setText("Cámara detenida")
        self.image_label.setStyleSheet("background-color: #000; color: #FFF;")
        self.image_label.clear() # Limpiar la imagen