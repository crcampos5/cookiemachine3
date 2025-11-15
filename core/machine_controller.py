"""
core/machine_controller.py
El 'Cerebro'. Entiende la lógica de FluidNC (JSON, estados).
Versión 2.0: Añade lógica de configuración y verificación.
"""

import json
from enum import Enum
from PySide6.QtCore import QObject, Signal, Slot

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONFIGURING = 1  # ¡Nuevo estado!
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
        
        # --- Banderas de verificación ---
        self._config_interval_ok = False
        self._config_fields_ok = False
        self._initial_status_ok = False
        
        print("MachineController (Cerebro v2.0) inicializado.")

    @Slot(str)
    def send_command(self, command: str):
        if self.connection_state == ConnectionState.CONNECTED:
            self.command_to_send.emit(command)
        else:
            self.log_message.emit("Máquina no lista. Comando no enviado.")

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
        Ahora también busca confirmaciones de configuración.
        """
        # 1. Buscar confirmaciones de configuración
        if self.connection_state == ConnectionState.CONFIGURING:
            if line == "[MSG:Report/Interval=100]":
                self._config_interval_ok = True
                self.log_message.emit("Verificado: Report/Interval=100")
            elif line == "[MSG:Report/Fields=State,MPos]":
                self._config_fields_ok = True
                self.log_message.emit("Verificado: Report/Fields=State,MPos")
        
        # 2. Buscar JSON de estado
        if line.startswith('{') and line.endswith('}'):
            try:
                status_json = json.loads(line)
                
                if "State" in status_json and "name" in status_json["State"]:
                    self._update_machine_state(status_json["State"]["name"])
                    if self.connection_state == ConnectionState.CONFIGURING:
                        self._initial_status_ok = True
                
                if "MPos" in status_json:
                    pos = status_json["MPos"]
                    if len(pos) >= 3:
                        self.position_updated.emit(pos[0], pos[1], pos[2])
                        
            except json.JSONDecodeError:
                self.log_message.emit(f"JSON corrupto: {line}")
        
        # 3. Comprobar si la configuración está completa
        if self.connection_state == ConnectionState.CONFIGURING:
            self._check_configuration_complete()

    @Slot(bool)
    def on_connection_changed(self, is_connected: bool):
        """
        Slot llamado por el Cartero. Inicia la configuración o limpia.
        """
        if is_connected:
            # ¡Conectado! Iniciar el proceso de configuración.
            self.connection_state = ConnectionState.CONFIGURING
            self.log_message.emit("Puerto conectado. Configurando FluidNC...")
            
            # Reiniciar banderas
            self._config_interval_ok = False
            self._config_fields_ok = False
            self._initial_status_ok = False
            
            # Enviar comandos de configuración
            self.command_to_send.emit("$Report/Interval=100")
            self.command_to_send.emit("$Report/Fields=State,MPos")
            self.command_to_send.emit("?") # Pedir estado inicial
            
        else:
            # Desconectado. Limpiar todo.
            self.connection_state = ConnectionState.DISCONNECTED
            self._update_machine_state("Desconectado")

    def _check_configuration_complete(self):
        """
        Comprueba si se han cumplido todos los pasos de configuración.
        """
        if (self._config_interval_ok and 
            self._config_fields_ok and 
            self._initial_status_ok):
            
            self.connection_state = ConnectionState.CONNECTED
            self.log_message.emit("¡Máquina configurada y lista!")
            
            # Forzar una actualización de estado (para emitir machine_ready)
            self._update_machine_state(self.machine_state)

    
    def _update_machine_state(self, new_state: str):
        """
        Centraliza la lógica de cambio de estado.
        """
        if self.machine_state == new_state and self.connection_state != ConnectionState.CONNECTED:
            # No emitir machine_ready si solo estamos parseando pero no listos
            return

        self.machine_state = new_state
        self.status_changed.emit(new_state)
        
        # Solo emitir 'machine_ready' si estamos totalmente conectados Y en Idle
        if self.connection_state == ConnectionState.CONNECTED and new_state == "Idle":
            self.machine_ready.emit(True)
        else:
            self.machine_ready.emit(False)