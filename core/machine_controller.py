"""
core/machine_controller.py
El 'Cerebro'. Entiende la lógica de FluidNC (JSON, estados).
Versión: Añade configuración automática al conectar.
"""

import json
import time # Importamos time por si necesitamos retardos (opcional)
from enum import Enum
from PySide6.QtCore import QObject, Signal, Slot, QTimer

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

class MachineController(QObject):
    """
    Maneja el estado de la máquina FluidNC.
    """
    
    status_changed = Signal(str)
    position_updated = Signal(float, float, float)
    log_message = Signal(str)
    machine_ready = Signal(bool)
    command_to_send = Signal(str) 

    def __init__(self):
        super().__init__()
        self.machine_state = "Desconectado"
        self.connection_state = ConnectionState.DISCONNECTED
        print("MachineController (Cerebro) inicializado.")

    @Slot()
    def initialize_thread(self):
        """ Slot llamado una vez por 'started' del QThread. """
        print("Cerebro (Controller) inicializado en su hilo.")

    @Slot(str)
    def send_command(self, command: str):
        """ Slot llamado por los botones (ej. Jog). """
        if self.connection_state == ConnectionState.CONNECTED:
            self.command_to_send.emit(command)
        else:
            self.log_message.emit("No conectado. Comando no enviado.")

    @Slot()
    def home(self):
        self.send_command("$H")

    @Slot()
    def unlock(self):
        self.send_command("$X")

    @Slot(str)
    def parse_line(self, line: str):
        """
        Recibe una línea del Cartero (SerialConnection) y la parsea.
        """
        # A veces FluidNC envía mensajes de texto plano al inicio o "ok"
        if not line.startswith('{'):
            # Podríamos loguear mensajes de inicio si son importantes
            if "FluidNC" in line or "Grbl" in line:
                self.log_message.emit(f"Firmware: {line}")
            return 

        try:
            status_json = json.loads(line)
            
            if "State" in status_json and "name" in status_json["State"]:
                self._update_machine_state(status_json["State"]["name"])
            
            if "MPos" in status_json:
                pos = status_json["MPos"]
                if len(pos) >= 3:
                    self.position_updated.emit(pos[0], pos[1], pos[2])
            
            # Detectar mensajes de error o alarma en el JSON
            if "Msg" in status_json:
                self.log_message.emit(f"Mensaje máquina: {status_json['Msg']}")

        except json.JSONDecodeError:
            # Ignoramos líneas que parecen JSON pero están corruptas
            pass
        except Exception as e:
            self.log_message.emit(f"Error al parsear: {e}")

    @Slot(bool)
    def on_connection_changed(self, is_connected: bool):
        """ 
        Actualiza el estado interno cuando el Cartero le informa.
        Aquí realizamos la inicialización de FluidNC.
        """
        if is_connected:
            self.connection_state = ConnectionState.CONNECTED
            self.log_message.emit("Conexión física establecida. Configurando FluidNC...")
            
            # --- SECUENCIA DE INICIALIZACIÓN ---
            
            # 1. Forzar reporte automático cada 200ms
            # Esto asegura que recibamos actualizaciones sin pedir '?' constantemente
            self.command_to_send.emit("$Report/Interval=200")
            
            # 2. Pedir estado inmediato (para no esperar los primeros 200ms)
            self.command_to_send.emit("?")
            
            # 3. (Opcional) Pedir configuración actual para confirmar
            # self.command_to_send.emit("$S") 
            
        else:
            self.connection_state = ConnectionState.DISCONNECTED
            self._update_machine_state("Desconectado")
    
    def _update_machine_state(self, new_state: str):
        if self.machine_state == new_state:
            return
        self.machine_state = new_state
        self.status_changed.emit(new_state)
        self.machine_ready.emit(new_state == "Idle")