"""
gui/main_window.py
Define la ventana principal (QMainWindow) de la aplicación.
(Versión refactorizada: Conecta el Cerebro y el Cartero)
"""

from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout

# --- Importar el núcleo ---
from core.machine_controller import MachineController
from core.serial_connection import SerialConnection # ¡NUEVO!

# --- Importar los Widgets de la GUI ---
from gui.widgets.connect_panel import ConnectPanel
from gui.widgets.info_panel import InfoPanel
from gui.widgets.move_controls import MoveControls
from gui.widgets.camera_widget import CameraWidget


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Cookie Machine (FluidNC - PySide6)")
        self.setGeometry(100, 100, 1600, 900)

        self.setup_threads() # ¡ACTUALIZADO!
        self.setup_ui_layout()
        self.connect_signals_and_slots()
        
        # Iniciar AMBOS hilos
        self.controller_thread.start()
        self.connection_thread.start()
        print("MainWindow inicializada. Hilos iniciados.")

    # --- 1. Configuración del Núcleo (ACTUALIZADO) ---

    def setup_threads(self):
        """
        Crea el Cerebro (Controller) y el Cartero (Connection)
        y los mueve a sus propios hilos.
        """
        # 1. Crear el Cerebro (Controller)
        self.controller = MachineController()
        self.controller_thread = QThread(self)
        self.controller_thread.setObjectName("ControllerThread")
        self.controller.moveToThread(self.controller_thread)
        print("Cerebro (Controller) movido a QThread.")
        
        # 2. Crear el Cartero (Connection)
        self.connection = SerialConnection()
        self.connection_thread = QThread(self)
        self.connection_thread.setObjectName("ConnectionThread")
        self.connection.moveToThread(self.connection_thread)
        print("Cartero (Connection) movido a QThread.")

    # --- 2. Configuración de la Interfaz (sin cambios) ---

    def setup_ui_layout(self):
        # ... (Este método es idéntico al anterior) ...
        main_layout = QHBoxLayout()
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.camera_widget = CameraWidget(camera_index=0, title="Cámara Principal")
        left_panel_layout.addWidget(self.camera_widget, stretch=1)
        self.laser_widget = CameraWidget(camera_index=1, title="Cámara Láser")
        left_panel_layout.addWidget(self.laser_widget, stretch=1)
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.connect_panel = ConnectPanel()
        right_panel_layout.addWidget(self.connect_panel)
        self.info_panel = InfoPanel()
        right_panel_layout.addWidget(self.info_panel)
        self.move_controls = MoveControls()
        right_panel_layout.addWidget(self.move_controls)
        right_panel_layout.addStretch(1)
        main_layout.addLayout(left_panel_layout, stretch=3)
        main_layout.addLayout(right_panel_layout, stretch=1)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    # --- 3. Conexión de Señales y Slots (ACTUALIZADO) ---

    def connect_signals_and_slots(self):
        """
        Conecta todos los componentes: GUI <-> Cerebro <-> Cartero.
        """
        
        # --- A. GUI -> Cerebro (Controller) ---
        self.connect_panel.home_button.clicked.connect(self.controller.home)
        self.connect_panel.unlock_button.clicked.connect(self.controller.unlock)
        self.move_controls.jog_command.connect(self.controller.send_command)
        
        # --- B. GUI -> Cartero (Connection) ---
        self.connect_panel.connect_button.clicked.connect(self.on_connect_button_clicked)
        self.connect_panel.disconnect_button.clicked.connect(self.connection.disconnect_from)
        self.connect_panel.refresh_button.clicked.connect(self.connection.find_ports)
        
        # Buscar puertos automáticamente al iniciar el hilo del Cartero
        self.connection_thread.started.connect(self.connection.find_ports)

        # --- C. Cerebro -> GUI ---
        self.controller.status_changed.connect(self.info_panel.update_status)
        self.controller.position_updated.connect(self.info_panel.update_position)
        self.controller.machine_ready.connect(self.move_controls.set_controls_enabled)
        
        # --- D. Cartero -> GUI ---
        self.connection.port_list_updated.connect(self.connect_panel.update_port_list)
        self.connection.connection_changed.connect(self.connect_panel.update_connection_status)

        # --- E. Cerebro <-> Cartero (El enlace clave) ---
        self.connection.line_received.connect(self.controller.parse_line) # Cartero -> Cerebro
        self.controller.command_to_send.connect(self.connection.send_line) # Cerebro -> Cartero
        
        # Sincronizar estado de conexión (Cartero -> Cerebro)
        self.connection.connection_changed.connect(self.controller.on_connection_changed)

        # --- F. Logging (Todos -> GUI) ---
        self.controller.log_message.connect(self.info_panel.add_log)
        self.connection.log_message.connect(self.info_panel.add_log)
        self.camera_widget.log_message.connect(self.info_panel.add_log)
        self.laser_widget.log_message.connect(self.info_panel.add_log)

    # --- 4. Slots Personalizados (sin cambios) ---

    @Slot()
    def on_connect_button_clicked(self):
        port = self.connect_panel.get_selected_port()
        if port:
            # ¡ACTUALIZADO! Llama al Cartero (Connection), no al Cerebro
            self.connection.connect_to(port_name=port, baud_rate=115200)
        else:
            self.info_panel.add_log("Error: No se seleccionó ningún puerto COM.")

    # --- 5. Manejo de Cierre (ACTUALIZADO) ---

    def closeEvent(self, event):
        print("Cerrando aplicación...")
        
        # 1. Detener cámaras
        self.camera_widget.stop_feed()
        self.laser_widget.stop_feed()
            
        # 2. Detener hilos del Cerebro y Cartero
        self.controller_thread.quit()
        self.connection_thread.quit()
        
        # Esperar a que terminen
        if not self.controller_thread.wait(2000):
            print("Hilo del Cerebro no respondió. Terminando.")
            self.controller_thread.terminate()
        
        if not self.connection_thread.wait(2000):
            print("Hilo del Cartero no respondió. Terminando.")
            self.connection_thread.terminate()
        
        print("Hilos detenidos. Adiós.")
        event.accept()