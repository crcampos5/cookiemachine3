"""
core/machine_controller.py
Controlador de la máquina para FluidNC (versión robusta).

Gestiona una máquina de estados para la conexión, detecta caídas 
y monitorea el estado de FluidNC (Idle, Run, Alarm).
"""

import serial
import serial.tools.list_ports
import json
import threading
import time
from enum import Enum

from PySide6.QtCore import QObject, Signal, Slot, QThread

# 1. Definimos los estados de nuestra conexión
class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

class MachineController(QObject):
    """
    Controla la conexión y comunicación con la máquina FluidNC.
    Hereda de QObject para usar el sistema de Señales y Slots de Qt.
    """
    
    # --- Señales (Signals) ---
    connection_changed = Signal(bool)     # True si CONECTADO, False si DESCONECTADO
    port_list_updated = Signal(list)      # Lista de puertos COM
    status_changed = Signal(str)          # Estado de FluidNC (Idle, Run, Alarm)
    position_updated = Signal(float, float, float) # Posición MPos
    log_message = Signal(str)             # Mensajes para el log de la GUI
    machine_ready = Signal(bool)          # True si state == "Idle", False en otro caso

    def __init__(self):
        super().__init__()
        
        # 2. Variables de estado
        self.serial_connection = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.machine_state = "Desconectado"     # Almacena el último estado conocido
        self.run_listener = True                # Flag para mantener vivo el bucle
        self.serial_lock = threading.Lock()
        
        # 3. Configuración del Heartbeat
        self.HEARTBEAT_TIMEOUT = 5.0 # Segundos sin un JSON válido = Conexión perdida
        self.last_message_time = 0

        print("MachineController (Robusto) inicializado.")

    # --- Slots (para ser llamados desde la GUI) ---

    @Slot()
    def find_ports(self):
        print("--- DEBUG: Ejecutando find_ports()... ---")
        try:
            ports = serial.tools.list_ports.comports()
            port_list = [port.device for port in ports]
            print(f"--- DEBUG: Puertos encontrados: {port_list} ---")
            self.port_list_updated.emit(port_list)
        except Exception as e:
            print(f"--- DEBUG: ERROR en find_ports(): {e} ---")
            self.log_message.emit(f"Error al buscar puertos: {e}")

    @Slot(str, int)
    def connect_serial(self, port_name, baud_rate=115200):
        if self.connection_state != ConnectionState.DISCONNECTED:
            self.log_message.emit("Ya está conectado o conectando.")
            return

        self.connection_state = ConnectionState.CONNECTING
        self.log_message.emit(f"Conectando a {port_name}...")

        try:
            self.serial_connection = serial.Serial(
                port_name, baudrate=baud_rate, timeout=1.0
            )
            # Damos tiempo a que se estabilice y reiniciamos FluidNC
            QThread.msleep(100) # Espera corta
            self.serial_connection.write(b'\x18\n') # Ctrl+X para reiniciar
            QThread.msleep(100)
            
            self.connection_state = ConnectionState.CONNECTED
            self.last_message_time = time.time() # Iniciar el contador del heartbeat
            
            self.connection_changed.emit(True)
            self.log_message.emit(f"Conectado a {port_name}")
            
        except serial.SerialException as e:
            self.connection_state = ConnectionState.DISCONNECTED
            self.connection_changed.emit(False)
            self.log_message.emit(f"Error de conexión: {e}")

    @Slot()
    def disconnect_serial(self):
        """
        Inicia el proceso de desconexión. El bucle se encargará de cerrar.
        """
        if self.connection_state != ConnectionState.DISCONNECTED:
            self.log_message.emit("Desconectando...")
            self.connection_state = ConnectionState.DISCONNECTED

    @Slot(str)
    def send_command(self, command):
        """
        Envía un comando G-code.
        La GUI debería deshabilitar los botones si machine_ready es False.
        """
        if self.connection_state != ConnectionState.CONNECTED:
            self.log_message.emit("No conectado. Comando no enviado.")
            return

        with self.serial_lock:
            try:
                self.serial_connection.write((command + '\n').encode())
            except serial.SerialException as e:
                self.log_message.emit(f"Error al enviar: {e}")
                # El puerto murió. Declaramos la conexión como perdida.
                self.connection_state = ConnectionState.DISCONNECTED

    @Slot()
    def home(self):
        self.send_command("$H")

    @Slot()
    def unlock(self):
        self.send_command("$X")

    @Slot()
    def run_listener_loop(self):
        """
        El corazón del controlador. Escucha permanentemente el puerto serial.
        Este slot DEBE ser conectado a la señal 'started' del QThread.
        """
        while self.run_listener:
            
            # --- Gestión de estado de conexión ---
            if self.connection_state != ConnectionState.CONNECTED:
                # Si estamos desconectados, cerramos el puerto (si existe)
                if self.serial_connection:
                    with self.serial_lock:
                        self.serial_connection.close()
                    self.serial_connection = None
                    self.connection_changed.emit(False)
                    self._update_machine_state("Desconectado")
                    
                # Esperamos pasivamente hasta que se llame a connect_serial()
                QThread.msleep(250)
                continue

            # --- Lógica de Heartbeat ---
            if time.time() - self.last_message_time > self.HEARTBEAT_TIMEOUT:
                self.log_message.emit("Error: Timeout de Heartbeat. Conexión perdida.")
                self.connection_state = ConnectionState.DISCONNECTED
                continue # El bucle volverá al inicio y gestionará la desconexión

            # --- Lógica de Lectura ---
            try:
                with self.serial_lock:
                    # 'readline()' bloqueará MÁXIMO 1 segundo (el timeout)
                    response_line = self.serial_connection.readline().decode('utf-8').strip()

                if not response_line:
                    # Timeout de readline(). No es un error, solo estamos esperando.
                    continue

                if not response_line.startswith('{') or not response_line.endswith('}'):
                    # Ignorar 'ok' o mensajes de bienvenida
                    continue
                
                # ¡Recibimos datos! Reiniciamos el contador del heartbeat
                self.last_message_time = time.time()
                
                # Parsear el JSON
                status_json = json.loads(response_line)
                
                if "State" in status_json and "name" in status_json["State"]:
                    self._update_machine_state(status_json["State"]["name"])
                
                if "MPos" in status_json:
                    pos = status_json["MPos"]
                    if len(pos) >= 3:
                        self.position_updated.emit(pos[0], pos[1], pos[2])
            
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.log_message.emit("Recibido JSON corrupto. Ignorando.")
                pass
            except serial.SerialException as e:
                self.log_message.emit(f"Error de puerto: {e}. Desconectando.")
                self.connection_state = ConnectionState.DISCONNECTED
            except Exception as e:
                self.log_message.emit(f"Error inesperado en listener: {e}")
                self.connection_state = ConnectionState.DISCONNECTED

        # Fin del bucle (run_listener = False)
        if self.serial_connection:
            self.serial_connection.close()
        print("Hilo listener detenido limpiamente.")

    def _update_machine_state(self, new_state: str):
        """
        Función interna para centralizar la lógica de cambio de estado.
        """
        if self.machine_state == new_state:
            return # Sin cambios
            
        self.machine_state = new_state
        self.status_changed.emit(new_state)
        
        # 4. Emitir la señal de "listo"
        if new_state == "Idle":
            self.machine_ready.emit(True)
        else:
            self.machine_ready.emit(False)

    def stop_listener(self):
        """
        Llamado por la MainWindow al cerrar para detener el bucle.
        """
        self.run_listener = False
        self.disconnect_serial()