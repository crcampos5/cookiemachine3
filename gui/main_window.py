"""
gui/main_window.py
Define la ventana principal (QMainWindow) de la aplicación.
Versión: Usa señales para comunicarse con los hilos (Thread-Safe).
"""

from PySide6.QtCore import QThread, Slot, Signal # <--- ¡Importamos Signal!
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout

from core.machine_controller import MachineController
from core.serial_connection import SerialConnection

from gui.widgets.connect_panel import ConnectPanel
from gui.widgets.info_panel import InfoPanel
from gui.widgets.move_controls import MoveControls
from gui.widgets.camera_widget import CameraWidget
from gui.widgets.action_panel import ActionPanel


class MainWindow(QMainWindow):

    # --- ¡NUEVA SEÑAL! ---
    # Esta señal llevará la orden de conexión al hilo del Cartero de forma segura.
    request_connect = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Cookie Machine (FluidNC - PySide6)")
        self.setGeometry(100, 100, 1600, 900)

        self.setup_threads()
        self.setup_ui_layout()
        self.connect_signals_and_slots()
        
        self.controller_thread.start()
        self.connection_thread.start()
        print("MainWindow inicializada. Hilos iniciados.")

    def setup_threads(self):
        self.controller = MachineController()
        self.controller_thread = QThread(self)
        self.controller_thread.setObjectName("ControllerThread")
        self.controller.moveToThread(self.controller_thread)
        
        self.connection = SerialConnection()
        self.connection_thread = QThread(self)
        self.connection_thread.setObjectName("ConnectionThread")
        self.connection.moveToThread(self.connection_thread)

    def setup_ui_layout(self):
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
        self.action_panel = ActionPanel()
        right_panel_layout.addWidget(self.action_panel)
        
        right_panel_layout.addStretch(1)
        main_layout.addLayout(left_panel_layout, stretch=3)
        main_layout.addLayout(right_panel_layout, stretch=1)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def connect_signals_and_slots(self):
        """ Conecta todos los componentes. """
        
        # --- A. GUI -> Cerebro (Controller) ---
        self.connect_panel.home_button.clicked.connect(self.controller.home)
        self.connect_panel.unlock_button.clicked.connect(self.controller.unlock)
        self.connect_panel.reset_button.clicked.connect(self.controller.reset)
        self.move_controls.jog_command.connect(self.controller.send_command)
        
        # --- B. GUI -> Cartero (Connection) ---
        
        # ¡CAMBIO IMPORTANTE AQUÍ!
        # Conectamos nuestra señal SEGURA 'request_connect' al slot 'connect_to' del Cartero.
        # Qt se encarga de pasar la llamada de un hilo a otro.
        self.request_connect.connect(self.connection.connect_to)
        
        # El botón llama a un slot local que EMITE la señal
        self.connect_panel.connect_button.clicked.connect(self.emit_connect_signal)
        
        self.connect_panel.disconnect_button.clicked.connect(self.connection.disconnect_from)
        self.connect_panel.refresh_button.clicked.connect(self.connection.find_ports)
        self.connection_thread.started.connect(self.connection.find_ports)
        self.controller_thread.started.connect(self.controller.initialize_thread)

        # --- C. Cerebro -> GUI ---
        self.controller.status_changed.connect(self.info_panel.update_status)
        self.controller.position_updated.connect(self.info_panel.update_position)
        self.controller.machine_ready.connect(self.move_controls.set_controls_enabled)
        
        # --- D. Cartero -> GUI ---
        self.connection.port_list_updated.connect(self.connect_panel.update_port_list)
        self.connection.connection_changed.connect(self.connect_panel.update_connection_status)

        # --- E. Cerebro <-> Cartero ---
        self.connection.line_received.connect(self.controller.parse_line)
        self.controller.command_to_send.connect(self.connection.send_line)
        self.connection.connection_changed.connect(self.controller.on_connection_changed)

        # --- F. Logging ---
        self.controller.log_message.connect(self.info_panel.add_log)
        self.connection.log_message.connect(self.info_panel.add_log)
        self.camera_widget.log_message.connect(self.info_panel.add_log)
        self.laser_widget.log_message.connect(self.info_panel.add_log)

        # --- Conexiones del ActionPanel (NUEVO) ---
        # 1. Conectar estado de conexión para habilitar/deshabilitar botones
        self.connection.connection_changed.connect(self.action_panel.set_enabled)
        
        # 2. Conectar botones a los slots del controlador
        self.action_panel.estop_button.clicked.connect(self.controller.reset) # E-Stop es Reset
        self.action_panel.pause_button.clicked.connect(self.controller.hold)
        self.action_panel.resume_button.clicked.connect(self.controller.resume)

    @Slot()
    def emit_connect_signal(self):
        """
        Recoge los datos de la GUI y emite la señal para el hilo.
        NO llama a self.connection directamente.
        """
        port = self.connect_panel.get_selected_port()
        if port:
            # Emitir la señal. Qt la llevará al hilo correcto.
            self.request_connect.emit(port, 115200)
        else:
            self.info_panel.add_log("Error: No se seleccionó ningún puerto COM.")

    def closeEvent(self, event):
        print("Cerrando aplicación...")
        self.camera_widget.stop_feed()
        self.laser_widget.stop_feed()
        self.controller_thread.quit()
        self.connection_thread.quit()
        self.controller_thread.wait(2000)
        self.connection_thread.wait(2000)
        event.accept()