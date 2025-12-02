"""
gui/widgets/camera_widget.py
Widget de visualización simple.
Solo muestra las imágenes que recibe. NO controla la cámara.
"""

import cv2
import numpy as np
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QImage, QPixmap

class CameraWidget(QGroupBox):
    """
    Widget 'tonto' que actúa solo como pantalla.
    Recibe frames (numpy array) y los dibuja en un QLabel.
    """
    
    def __init__(self, camera_index: int, title: str = "Cámara", parent=None):
        # Mantenemos camera_index en el título solo como referencia visual
        super().__init__(f"{title} (#{camera_index})", parent)
        
        # --- Interfaz Gráfica ---
        self.image_label = QLabel("Esperando video...")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #000; color: #666; font-size: 10pt;")
        
        # Política de tamaño para que se expanda y encoja libremente
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setScaledContents(False) # Lo escalamos manualmente para mantener aspecto

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        # Bandera para controlar si permitimos video en vivo
        self.updates_enabled = True

    @Slot(np.ndarray)
    def set_image(self, frame: np.ndarray):
        """
        Recibe frames del video en vivo.
        Solo actualiza si updates_enabled es True.
        """
        if self.updates_enabled:
            self._render_frame(frame)

    @Slot(np.ndarray)
    def show_static_image(self, frame: np.ndarray):
        """
        Muestra una imagen procesada (Debug) y BLOQUEA el video en vivo
        para que no se sobrescriba inmediatamente.
        """
        self.updates_enabled = False
        self._render_frame(frame)

    @Slot()
    def enable_video(self):
        """Reactiva el flujo de video en vivo."""
        self.updates_enabled = True

    def _render_frame(self, frame: np.ndarray):
        """Lógica interna de conversión y pintado en el QLabel."""
        if frame is None: return

        try:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            pixmap = QPixmap.fromImage(q_image)
            # Escalar si el label ya tiene tamaño
            if self.image_label.width() > 0 and self.image_label.height() > 0:
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setPixmap(pixmap)
                
        except Exception as e:
            print(f"Error visualizando frame: {e}")