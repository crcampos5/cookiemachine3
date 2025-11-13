"""
gui/main_window.py
Define la ventana principal (QMainWindow) de la aplicación.
"""

from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout

# --- Importar el núcleo ---
from core.machine_controller import MachineController

# --- Importar los Widgets de la GUI ---
from gui.widgets.connect_panel import ConnectPanel
from gui.widgets.info_panel import InfoPanel
from gui.widgets.move_controls import MoveControls
from gui.widgets.camera_widget import CameraWidget
# (Próximos widgets a crear)
# from gui.widgets.laser_controls import LaserControls
# from gui.widgets.file_manager import FileManager


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Cookie Machine (FluidNC - PySide6)")
        self.setGeometry(100, 100, 1600, 900)

        self.setup_controller_and_thread()
        self.setup_ui_layout()
        self.connect_signals_and_slots()
        
        # Iniciar el hilo. Esto emitirá 'started',
        # que llamará a 'run_listener_loop'
        self.controller_thread.start()
        print("MainWindow inicializada. Hilo del controlador iniciado.")

    # --- 1. Configuración del Núcleo (Controller) ---

    def setup_controller_and_thread(self):
        """
        Crea el controlador de la máquina y lo mueve a un hilo
        separado (QThread) para no bloquear la GUI.
        """
        self.controller = MachineController()
        self.controller_thread = QThread(self)
        self.controller_thread.setObjectName("ControllerThread")
        
        # Mover el objeto 'controller' al hilo 'controller_thread'
        self.controller.moveToThread(self.controller_thread)
        
        # ¡NO MÁS QTIMER!
        print("Controlador movido a QThread.")

    # --- 2. Configuración de la Interfaz (Layout) ---
    
    def setup_ui_layout(self):
        # ... (Este método no cambia) ...
        main_layout = QHBoxLayout()
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.camera_widget = CameraWidget(camera_index=0)
        left_panel_layout.addWidget(self.camera_widget, stretch=1)
        self.laser_widget = CameraWidget(camera_index=1)
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

    # --- 3. Conexión de Señales y Slots ---

    def connect_signals_and_slots(self):
        """
        Conecta las señales (Signals) del controlador a los
        slots (funciones) de la GUI, y viceversa.
        """
        
        # --- A. Control de Hilos y Timer ---
        
        # Conectar la señal 'started' del hilo al 'run_listener_loop'
        # Esto inicia el bucle de escucha tan pronto como el hilo arranca.
        self.controller_thread.started.connect(self.controller.run_listener_loop)
        
        # --- B. Conexiones del Controlador (Backend) -> GUI (Frontend) ---
        
        # (El resto de las conexiones son las mismas)
        self.controller.connection_changed.connect(self.connect_panel.update_connection_status)
        self.controller.connection_changed.connect(self.info_panel.on_connection_changed)
        self.controller.status_changed.connect(self.info_panel.update_status)
        self.controller.position_updated.connect(self.info_panel.update_position)
        self.controller.log_message.connect(self.info_panel.add_log)
        
        # --- C. Conexiones de la GUI (Frontend) -> Controlador (Backend) ---
        
        # Actualizar el panel de conexión para buscar puertos al inicio
        self.connect_panel.refresh_button.clicked.connect(self.controller.find_ports)
        self.controller.port_list_updated.connect(self.connect_panel.update_port_list)
        
        self.connect_panel.connect_button.clicked.connect(self.on_connect_button_clicked)
        self.connect_panel.disconnect_button.clicked.connect(self.controller.disconnect_serial)
        self.connect_panel.home_button.clicked.connect(self.controller.home)
        
        self.move_controls.jog_command.connect(self.controller.send_command)
        
        # --- D. Conexión de inicio ---
        # Buscar puertos automáticamente al iniciar el hilo
        self.controller_thread.started.connect(self.controller.find_ports)

    # --- 4. Slots Personalizados (Funciones de pegamento) ---

    @Slot()
    def on_connect_button_clicked(self):
        """
        Slot personalizado que actúa como intermediario para leer
        el puerto COM del widget antes de llamar al controlador.
        """
        port = self.connect_panel.get_selected_port()
        if port:
            # Llama al slot del controlador (que está en otro hilo)
            self.controller.connect_serial(port_name=port, baud_rate=115200)
        else:
            self.info_panel.add_log("Error: No se seleccionó ningún puerto COM.")

    # --- 5. Manejo de Cierre ---

    def closeEvent(self, event):
        """
        Maneja el evento de cierre de la ventana para asegurar
        que el hilo del controlador se detenga limpiamente.
        """
        print("Cerrando aplicación...")
        
        # 1. Indicar al bucle del controlador que se detenga
        if hasattr(self, 'controller'):
            self.controller.stop_listener()
            
        # 2. Pedir al hilo que termine
        if hasattr(self, 'controller_thread') and self.controller_thread.isRunning():
            self.controller_thread.quit()
            # Esperar a que el hilo termine (con un timeout)
            if not self.controller_thread.wait(3000): # 3 seg
                print("El hilo del controlador no respondió. Forzando terminación.")
                self.controller_thread.terminate()
        
        print("Hilos detenidos. Adiós.")
        event.accept() # Aceptar el evento de cierre