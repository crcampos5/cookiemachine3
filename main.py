"""
main.py
Punto de entrada principal para la aplicación Cookie Machine con PySide6.
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow  # Importa la ventana principal

def main():
    """
    Función principal para inicializar y ejecutar la aplicación.
    """
    
    # 1. Crear la instancia de la aplicación
    # sys.argv es necesario para manejar argumentos de línea de comandos
    app = QApplication(sys.argv)
    
    # 2. Instanciar la ventana principal
    window = MainWindow()
    
    # 3. Mostrar la ventana
    window.show()
    
    # 4. Iniciar el bucle de eventos de la aplicación
    # sys.exit() asegura que el proceso se cierre limpiamente
    sys.exit(app.exec())

if __name__ == "__main__":
    main()