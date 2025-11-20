"""
core/machine_controller.py
El 'Cerebro'. Entiende la lógica de FluidNC (Protocolo GRBL <...>).
Versión Final v2: Gestión de errores completa sin popups.
"""

from enum import Enum
from PySide6.QtCore import QObject, Signal, Slot

# Importar los códigos de error/alarma
from core.fluidnc_codes import FLUIDNC_ALARMS, FLUIDNC_ERRORS

class ConnectionState(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2

class MachineController(QObject):
    """
    Maneja el estado de la máquina FluidNC.
    Parsea reportes tipo: <Run|MPos:0.000,0.000,0.000|FS:2880,0>
    """
    
    # Señales para la GUI
    status_changed = Signal(str)           # Ej: "Run", "Idle", "Alarm"
    position_updated = Signal(float, float, float) # X, Y, Z
    log_message = Signal(str)              # Mensajes para el usuario (Registro)
    machine_ready = Signal(bool)           # True si está en Idle
    command_to_send = Signal(str)          # Para enviar al puerto serial

    def __init__(self):
        super().__init__()
        self.machine_state = "Desconectado"
        self.connection_state = ConnectionState.DISCONNECTED
        print("MachineController (Cerebro GRBL + Logs) inicializado.")

    @Slot()
    def initialize_thread(self):
        """ Slot de inicio del hilo. """
        print("Cerebro (Controller) inicializado en su hilo.")

    @Slot(str)
    def parse_line(self, line: str):
        """
        Analiza la línea recibida. Maneja Alarms, Errors y Status.
        """
        line = line.strip()
        if not line:
            return

        # --- 1. Detección de ALARMAS (Crítico) ---
        # Formato esperado: ALARM:1
        if line.startswith('ALARM:'):
            try:
                code_part = line.split(':')[1]
                # Limpiar posibles espacios extra
                code = code_part.strip()
                
                # Buscar descripción en nuestro archivo fluidnc_codes.py
                description = FLUIDNC_ALARMS.get(code, "Alarma desconocida")
                
                # Formato visual fuerte para el log (pero sin popup)
                log_msg = f"🛑 [ALARMA {code}] {description}"
                self.log_message.emit(log_msg)
                
                # Forzar estado de alarma visualmente en la GUI
                self._update_machine_state("Alarm")
                
            except IndexError:
                self.log_message.emit(f"🛑 [ALARMA MALFORMADA] {line}")
            return

        # --- 2. Detección de ERRORES (Advertencia) ---
        # Formato esperado: error:20
        if line.startswith('error:'):
            try:
                code_part = line.split(':')[1]
                code = code_part.strip()
                
                description = FLUIDNC_ERRORS.get(code, "Error desconocido")
                
                log_msg = f"⚠️ [ERROR {code}] {description}"
                self.log_message.emit(log_msg)
                
            except IndexError:
                self.log_message.emit(f"⚠️ [ERROR MALFORMADO] {line}")
            return

        # --- 3. Reporte de Estado (<...>) ---
        if line.startswith('<') and line.endswith('>'):
            content = line[1:-1]
            parts = content.split('|')
            
            # 3.1 Estado (Idle, Run, Alarm, etc.)
            state_raw = parts[0]
            state = state_raw.split(':')[0] 
            self._update_machine_state(state)

            # 3.2 Coordenadas (MPos/WPos)
            for part in parts[1:]:
                if part.startswith('MPos:'):
                    coords_str = part.split(':')[1]
                    self._emit_coordinates(coords_str)
                elif part.startswith('WPos:'):
                    coords_str = part.split(':')[1]
                    self._emit_coordinates(coords_str)
            return

        # --- 4. Mensajes informativos ---
        if line.startswith('[MSG:'):
            self.log_message.emit(f"ℹ️ {line}")
            return
        elif "FluidNC" in line or "Grbl" in line:
            self.log_message.emit(f"🔌 {line}")

    def _emit_coordinates(self, coords_str):
        try:
            parts = coords_str.split(',')
            if len(parts) >= 3:
                x = float(parts[0])
                y = float(parts[1])
                z = float(parts[2])
                self.position_updated.emit(x, y, z)
        except ValueError:
            pass 

    def _update_machine_state(self, new_state: str):
        if self.machine_state == new_state:
            return
        self.machine_state = new_state
        self.status_changed.emit(new_state)
        self.machine_ready.emit(new_state == "Idle")

    # --- Comandos Públicos ---

    @Slot(str)
    def send_command(self, command: str):
        if self.connection_state == ConnectionState.CONNECTED:
            self.command_to_send.emit(command)
        else:
            self.log_message.emit("No conectado.")

    @Slot()
    def home(self): self.send_command("$H")
    
    @Slot()
    def unlock(self): 
        self.log_message.emit("Enviando Desbloqueo ($X)...")
        self.send_command("$X")
    
    @Slot()
    def reset(self): 
        self.log_message.emit("🛑 Enviando RESET (Ctrl+X)...")
        self.send_command("\x18")
    
    @Slot()
    def hold(self): self.send_command("!")
    
    @Slot()
    def resume(self): self.send_command("~")

    @Slot(bool)
    def on_connection_changed(self, is_connected: bool):
        if is_connected:
            self.connection_state = ConnectionState.CONNECTED
            self.log_message.emit("✅ Conexión establecida.")
            self.command_to_send.emit("$10=1") # Forzar MPos
            self.command_to_send.emit("$Report/Interval=200") # Auto-reporte
            self.command_to_send.emit("?") # Estado inicial
        else:
            self.connection_state = ConnectionState.DISCONNECTED
            self._update_machine_state("Desconectado")