"""
core/machine_controller.py
El 'Cerebro'. Entiende la lógica de FluidNC (JSON, estados).
No sabe NADA sobre puertos seriales, solo recibe y envía texto.
"""

import json
from enum import Enum
from PySide6.QtCore import QObject, Signal, Slot

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

class MachineController(QObject):
    """
    Maneja el estado de la máquina FluidNC.
    """
    
    # --- Señales (Salida) ---
    status_changed = Signal(str)
    position_updated = Signal(float, float, float)
    log_message = Signal(str)
    machine_ready = Signal(bool)
    
    # ¡Nueva señal! Le "ordena" al Cartero que envíe un comando.
    command_to_send = Signal(str)

    def __init__(self):
        super().__init__()
        self.machine_state = "Desconectado"
        self.connection_state = ConnectionState.DISCONNECTED
        print("MachineController (Cerebro) inicializado.")

    # --- Slots Públicos (Llamados desde la GUI) ---

    @Slot(str)
    def send_command(self, command: str):
        """
        Slot llamado por los botones (ej. Jog).
        Simplemente re-emite el comando para el Cartero.
        """
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

    # --- Slots Internos (Conectados al 'Cartero') ---

    @Slot(str)
    def parse_line(self, line: str):
        """
        ¡El corazón del cerebro! Recibe una línea del Cartero (SerialConnection)
        y la parsea.
        """
        if not line.startswith('{') or not line.endswith('}'):
            # Ignorar 'ok' o mensajes que no sean JSON
            return

        try:
            status_json = json.loads(line)
            
            if "State" in status_json and "name" in status_json["State"]:
                self._update_machine_state(status_json["State"]["name"])
            
            if "MPos" in status_json:
                pos = status_json["MPos"]
                if len(pos) >= 3:
                    self.position_updated.emit(pos[0], pos[1], pos[2])
                    
        except json.JSONDecodeError:
            self.log_message.emit(f"JSON corrupto: {line}")
        except Exception as e:
            self.log_message.emit(f"Error al parsear: {e}")

    @Slot(bool)
    def on_connection_changed(self, is_connected: bool):
        """
        Actualiza el estado interno cuando el Cartero le informa.
        """
        if is_connected:
            self.connection_state = ConnectionState.CONNECTED
        else:
            self.connection_state = ConnectionState.DISCONNECTED
            self._update_machine_state("Desconectado")

    # --- Lógica Interna ---
    
    def _update_machine_state(self, new_state: str):
        """
        Centraliza la lógica de cambio de estado.
        """
        if self.machine_state == new_state:
            return # Sin cambios
            
        self.machine_state = new_state
        self.status_changed.emit(new_state)
        
        if new_state == "Idle":
            self.machine_ready.emit(True)
        else:
            self.machine_ready.emit(False)