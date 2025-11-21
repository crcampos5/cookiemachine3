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

    @Slot(np.ndarray)
    def set_image(self, frame: np.ndarray):
        """
        Recibe un frame de OpenCV (BGR), lo convierte a Qt (RGB) y lo muestra.
        """
        if frame is None:
            return

        try:
            # 1. Convertir color BGR -> RGB
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 2. Obtener dimensiones
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # 3. Crear imagen Qt
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # 4. Escalar al tamaño actual del label manteniendo proporción
            # Esto evita que la imagen se deforme al estirar la ventana
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Error visualizando frame: {e}")

    # Nota: Ya no necesitamos start_feed ni stop_feed aquí,
    # porque el control lo tiene el CameraDriver en el núcleo.