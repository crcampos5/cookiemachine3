"""
gui/main_window.py
Versión Vertical (1360x768): Integra FluidNC + Sensores + Nueva GUI Modular.
Conexión Ajustada: Resume inicia el trabajo.
"""

from PySide6.QtCore import QThread, Slot, Signal, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtSerialPort import QSerialPortInfo

# --- Imports del Núcleo ---
from core.machine_controller import MachineController
from core.serial_connection import SerialConnection
from core.job_controller import JobController 
from core.sensor_head.lighting_controller import LightingController
from core.sensor_head.camera_driver import CameraDriver

# --- Widgets ---
from gui.widgets.connect_panel import ConnectPanel
from gui.widgets.top_bar import TopBar
from gui.widgets.led_control_panel import LedControlPanel
from gui.widgets.machine_control_panel import MachineControlPanel
from gui.widgets.info_panel import InfoPanel
from gui.widgets.move_controls import MoveControls
from gui.widgets.camera_widget import CameraWidget
from gui.widgets.action_panel import ActionPanel
from gui.widgets.file_panel import FilePanel
from gui.widgets.injector_panel import InjectorPanel

from settings.settings_manager import SettingsManager
from gui.dialogs.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):

    request_connect_fluidnc = Signal(str, int)
    request_connect_arduino = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings_manager = SettingsManager()
        
        # Configuración de pantalla vertical
        self.setWindowTitle("Cookie Machine Control")
        self.setGeometry(0, 0, 768, 1360) # Ancho x Alto

        self.setup_threads()
        self.setup_ui_layout()
        self.connect_signals_and_slots()
        
        # Iniciar hilos
        self.fluidnc_thread.start()
        self.fluidnc_conn_thread.start()
        self.arduino_conn_thread.start()
        self.cam1_thread.start()
        self.cam2_thread.start()
        self.job_thread.start() # <--- Importante: Iniciar hilo de trabajo
        
        QTimer.singleShot(500, self.perform_auto_connect)

    def setup_threads(self):
        # 1. FluidNC
        self.controller = MachineController()
        self.fluidnc_thread = QThread()
        self.controller.moveToThread(self.fluidnc_thread)
        
        self.connection = SerialConnection()
        self.fluidnc_conn_thread = QThread()
        self.connection.moveToThread(self.fluidnc_conn_thread)
        
        # 2. Sensor
        self.lighting = LightingController()
        self.arduino_conn = SerialConnection()
        self.arduino_conn_thread = QThread()
        self.arduino_conn.moveToThread(self.arduino_conn_thread)
        
        # 3. Cámaras
        self.cam1_driver = CameraDriver(0)
        self.cam1_thread = QThread()
        self.cam1_driver.moveToThread(self.cam1_thread)
        self.cam2_driver = CameraDriver(1)
        self.cam2_thread = QThread()
        self.cam2_driver.moveToThread(self.cam2_thread)

        # 4. JobController
        self.job = JobController()
        self.job_thread = QThread()
        self.job.moveToThread(self.job_thread)

    def setup_ui_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(5)
        
        self.top_bar = TopBar()
        main_layout.addWidget(self.top_bar)
        
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(5,0,5,5)
        
        # Columna Izquierda (Video)
        video_layout = QVBoxLayout()
        self.camera_widget = CameraWidget(0, "Cámara Principal")
        self.laser_widget = CameraWidget(1, "Cámara Láser")
        video_layout.addWidget(self.camera_widget)
        video_layout.addWidget(self.laser_widget)
        # AÑADIR INYECTORES
        self.injector_panel = InjectorPanel()
        video_layout.addWidget(self.injector_panel, stretch=0)
        
        # Columna Derecha (Controles)
        sidebar_layout = QVBoxLayout()

        self.connect_panel = ConnectPanel()
        sidebar_layout.addWidget(self.connect_panel)
        
        self.led_panel = LedControlPanel()
        sidebar_layout.addWidget(self.led_panel)
        
        self.machine_panel = MachineControlPanel()
        sidebar_layout.addWidget(self.machine_panel)
        
        self.file_panel = FilePanel()
        sidebar_layout.addWidget(self.file_panel)
        
        self.info_panel = InfoPanel()
        sidebar_layout.addWidget(self.info_panel)
        
        self.move_controls = MoveControls()
        sidebar_layout.addWidget(self.move_controls)
        
        self.action_panel = ActionPanel()
        sidebar_layout.addWidget(self.action_panel)
        
        sidebar_layout.addStretch() 
        
        body_layout.addLayout(video_layout, stretch=2) 
        body_layout.addLayout(sidebar_layout, stretch=1)
        
        main_layout.addLayout(body_layout)

    def connect_signals_and_slots(self):
        # --- TopBar ---
        self.top_bar.btn_params.clicked.connect(self.open_settings_dialog)

        # --- Connect Panel ---
        self.connect_panel.refresh_button.clicked.connect(self.connection.find_ports)
        self.connection.port_list_updated.connect(self.connect_panel.update_port_list)
        self.fluidnc_conn_thread.started.connect(self.connection.find_ports)

        self.request_connect_fluidnc.connect(self.connection.connect_to)
        self.connect_panel.btn_connect_machine.clicked.connect(self.emit_connect_fluidnc_signal)
        self.connect_panel.btn_disconnect_machine.clicked.connect(self.connection.disconnect_from)
        self.connection.connection_changed.connect(self.connect_panel.set_machine_status)

        self.request_connect_arduino.connect(self.arduino_conn.connect_to)
        self.connect_panel.btn_connect_arduino.clicked.connect(self.emit_connect_arduino_signal)
        self.connect_panel.btn_disconnect_arduino.clicked.connect(self.arduino_conn.disconnect_from)
        self.arduino_conn.connection_changed.connect(self.connect_panel.set_arduino_status)

        # --- LedPanel ---
        self.led_panel.request_led_brightness.connect(self.lighting.set_brightness)
        self.led_panel.request_led_on.connect(self.lighting.set_color_all)
        self.led_panel.request_led_off.connect(self.lighting.leds_off)
        self.led_panel.request_laser_power.connect(self.lighting.set_laser_power)
        self.led_panel.request_laser_off.connect(self.lighting.laser_off)

        # --- MachinePanel ---
        self.machine_panel.home_button.clicked.connect(self.controller.home)
        self.machine_panel.unlock_button.clicked.connect(self.controller.unlock)
        self.machine_panel.reset_button.clicked.connect(self.controller.reset)

        # --- JOB INTEGRATION (CAMBIOS CLAVE) ---
        # 1. Cargar archivo
        self.file_panel.file_selected.connect(self.job.load_file)
        
        # 2. Botones ActionPanel -> JobController
        self.action_panel.estop_button.clicked.connect(self.job.stop_job)
        self.action_panel.pause_button.clicked.connect(self.job.pause_job)
        # El botón Reanudar ahora llama a on_resume_request (que inicia o reanuda)
        self.action_panel.resume_button.clicked.connect(self.job.on_resume_request)
        
        # 3. JobController -> Hardware
        self.job.request_command.connect(self.connection.send_line)
        self.job.request_lighting_on.connect(lambda: self.lighting.set_color_all(255, 255, 255))
        self.job.request_lighting_off.connect(self.lighting.leds_off)
        self.job.request_laser_on.connect(self.lighting.laser_on_full)
        self.job.request_laser_off.connect(self.lighting.laser_off)
        
        # 4. Hardware -> JobController
        self.cam1_driver.frame_captured.connect(self.job.update_main_frame)
        self.cam2_driver.frame_captured.connect(self.job.update_laser_frame)
        self.controller.status_changed.connect(self.job.update_machine_status)

        # --- FluidNC Internals ---
        self.fluidnc_thread.started.connect(self.controller.initialize_thread)
        self.connection.line_received.connect(self.controller.parse_line)
        self.controller.command_to_send.connect(self.connection.send_line)
        self.connection.connection_changed.connect(self.controller.on_connection_changed)
        self.controller.status_changed.connect(self.info_panel.update_status)
        self.controller.position_updated.connect(self.info_panel.update_position)
        self.controller.machine_ready.connect(self.move_controls.set_controls_enabled)
        self.connection.connection_changed.connect(self.action_panel.set_enabled)

        # --- Arduino Internals ---
        self.lighting.command_to_send.connect(self.arduino_conn.send_line)
        self.arduino_conn.connection_changed.connect(self.lighting.on_connection_changed)

        # --- MoveControls ---
        self.move_controls.jog_command.connect(self.controller.send_command)

        # --- Cameras ---
        self.cam1_driver.frame_captured.connect(self.camera_widget.set_image)
        self.cam2_driver.frame_captured.connect(self.laser_widget.set_image)
        QTimer.singleShot(2000, self.cam1_driver.start)
        QTimer.singleShot(2000, self.cam2_driver.start)

        # --- Logs ---
        self.controller.log_message.connect(self.info_panel.add_log)
        self.connection.log_message.connect(self.info_panel.add_log)
        self.lighting.log_message.connect(self.info_panel.add_log)
        self.arduino_conn.log_message.connect(self.info_panel.add_log)
        self.job.log_message.connect(self.info_panel.add_log)

        # --- CONEXIONES INYECTORES ---
        
        # 1. Pistón y Presión -> Arduino (LightingController)
        self.injector_panel.request_piston.connect(self.lighting.set_piston)
        self.injector_panel.request_pressure.connect(self.lighting.set_pressure)
        
        # 2. Válvula -> Máquina (MachineController)
        self.injector_panel.request_valve.connect(self.controller.set_valve)

    @Slot()
    def emit_connect_fluidnc_signal(self):
        port = self.connect_panel.get_machine_port()
        if port: self.request_connect_fluidnc.emit(port, 115200)
        else: self.info_panel.add_log("⚠️ Seleccione puerto Máquina")

    @Slot()
    def emit_connect_arduino_signal(self):
        port = self.connect_panel.get_arduino_port()
        if port: self.request_connect_arduino.emit(port, 115200)
        else: self.info_panel.add_log("⚠️ Seleccione puerto LedLaser")
    
    @Slot()
    def open_settings_dialog(self):
        """ Abre la ventana de configuración modal. """
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.exec() 

    @Slot()
    def perform_auto_connect(self):
        ports = QSerialPortInfo.availablePorts()
        self.info_panel.add_log("--- Auto-Conexión ---")
        
        FLUIDNC_IDS = ["CP210", "Silicon Labs", "Espressif"]
        ARDUINO_IDS = ["CH340", "USB-SERIAL", "Arduino"]
        
        fluidnc_found = False
        arduino_found = False

        for port in ports:
            info = f"{port.description()} {port.manufacturer()}".upper()
            name = port.portName()
            
            if not fluidnc_found and any(x in info for x in FLUIDNC_IDS):
                self.info_panel.add_log(f"✅ Máquina detectada en {name}")
                self.request_connect_fluidnc.emit(name, 115200)
                fluidnc_found = True
                continue
            
            if not arduino_found and any(x in info for x in ARDUINO_IDS):
                self.info_panel.add_log(f"✅ LedLaser detectado en {name}")
                self.request_connect_arduino.emit(name, 115200)
                arduino_found = True

    def closeEvent(self, event):
        self.cam1_driver.stop()
        self.cam2_driver.stop()
        self.fluidnc_thread.quit()
        self.fluidnc_conn_thread.quit()
        self.arduino_conn_thread.quit()
        self.cam1_thread.quit()
        self.cam2_thread.quit()
        self.job_thread.quit()
        self.fluidnc_thread.wait(1000)
        event.accept()