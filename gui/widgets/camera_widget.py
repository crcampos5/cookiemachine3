"""
gui/widgets/camera_widget.py
Widget para mostrar un feed de video de OpenCV (cámara) en un hilo 
separado usando el patrón QObject/QThread.
"""

import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QSizePolicy

# --- Paso 1: El "Trabajador" (Worker) ---

class CameraWorker(QObject):
    """
    El 'trabajador' que vive en el hilo secundario.
    Se encarga de abrir la cámara y leer los fotogramas.
    """
    # Señal que emite el fotograma (como un array numpy)
    frame_ready = Signal(np.ndarray)
    # Señal para enviar mensajes de log a la GUI
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
                
                # Emitir el fotograma para que la GUI lo muestre
                self.frame_ready.emit(frame)
                
            except Exception as e:
                self.log_message.emit(f"Error en cámara {self.camera_index}: {e}")
                self.is_running = False
                break
        
        # Limpieza
        if self.cap:
            self.cap.release()
        self.log_message.emit(f"Cámara {self.camera_index} detenida.")

    def stop(self):
        """
De        Indica al bucle que debe detenerse.
        """
        self.is_running = False

# --- Paso 2: El "Widget" (GUI) ---

class CameraWidget(QGroupBox):
    """
    El 'widget' que vive en el hilo principal.
    Muestra los fotogramas recibidos del CameraWorker.
    """
    # Señal para pasar los logs del worker a MainWindow
    log_message = Signal(str)

    def __init__(self, camera_index: int, title: str = "Cámara", parent=None):
        super().__init__(f"{title} (ID: {camera_index})", parent)
        
        self.image_label = QLabel("Iniciando cámara...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #000;")
        # Política de tamaño para que el label pueda crecer y encogerse
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        # Configurar el layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        # --- Configuración del Hilo y Trabajador ---
        self.worker_thread = QThread()
        self.worker_thread.setObjectName(f"CameraThread_{camera_index}")
        
        self.worker = CameraWorker(camera_index)
        self.worker.moveToThread(self.worker_thread)
        
        # --- Conexiones ---
        # 1. Iniciar el worker cuando el hilo arranque
        self.worker_thread.started.connect(self.worker.run)
        
        # 2. Conectar la señal de fotograma al slot de actualización de imagen
        self.worker.frame_ready.connect(self.set_image)
        
        # 3. Pasar los mensajes de log hacia arriba (a MainWindow)
        self.worker.log_message.connect(self.log_message)
        
        # 4. Limpieza: Detener el worker y salir del hilo
        # (MainWindow llamará a self.stop_feed() en su closeEvent)
        
        # Iniciar el hilo
        self.worker_thread.start()

    @Slot(np.ndarray)
    def set_image(self, frame: np.ndarray):
        """
        Slot: Se ejecuta en el hilo principal.
        Convierte el fotograma de OpenCV (BGR) a un QPixmap (RGB)
        y lo muestra en el QLabel.
        """
        try:
            # 1. Convertir BGR (OpenCV) a RGB (Qt)
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 2. Convertir array numpy a QImage
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # 3. Convertir QImage a QPixmap
            q_pixmap = QPixmap.fromImage(q_image)
            
            # 4. Mostrar el pixmap, escalándolo para que quepa en el QLabel
            self.image_label.setPixmap(q_pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        except Exception as e:
            print(f"Error al actualizar imagen: {e}") # Usar print para evitar bucles de log

    def stop_feed(self):
        """
        Detiene el trabajador y el hilo de la cámara.
        MainWindow llamará a esto al cerrar.
        """
        print(f"Deteniendo feed de {self.worker.camera_index}...")
        self.worker.stop()
        self.worker_thread.quit()
        if not self.worker_thread.wait(1000): # Esperar 1 seg
            print(f"Hilo de cámara {self.worker.camera_index} no respondió. Terminando.")
            self.worker_thread.terminate()