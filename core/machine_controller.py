"""
core/machine_controller.py
El 'Cerebro'. Entiende la lógica de FluidNC (Protocolo GRBL <...>).
Versión 3.0: Parser nativo para <Estado|MPos:...|...>
"""

from enum import Enum
from PySide6.QtCore import QObject, Signal, Slot

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
    log_message = Signal(str)              # Mensajes para el usuario
    machine_ready = Signal(bool)           # True si está en Idle
    command_to_send = Signal(str)          # Para enviar al puerto serial

    def __init__(self):
        super().__init__()
        self.machine_state = "Desconectado"
        self.connection_state = ConnectionState.DISCONNECTED
        print("MachineController (Parser GRBL) inicializado.")

    @Slot()
    def initialize_thread(self):
        """ Slot de inicio del hilo. """
        print("Cerebro listo.")

    @Slot(str)
    def parse_line(self, line: str):
        """
        Analiza la línea recibida del puerto serial.
        Maneja:
        1. Reportes de estado: <Run|MPos:...>
        2. Mensajes de información: [GC:...] o [MSG:...]
        3. Respuestas simples: ok
        """
        line = line.strip()
        if not line:
            return

        # --- CASO 1: Reporte de Estado (<...>) ---
        if line.startswith('<') and line.endswith('>'):
            # Quitamos los < > y separamos por tuberías |
            # Ej: "Run|MPos:0,0,0|FS:0,0" -> ["Run", "MPos:0,0,0", "FS:0,0"]
            content = line[1:-1]
            parts = content.split('|')
            
            # 1.1 El Estado (Siempre es el primero)
            # A veces viene como "Hold:0", tomamos solo la parte antes de los dos puntos
            state_raw = parts[0]
            state = state_raw.split(':')[0] 
            self._update_machine_state(state)

            # 1.2 Los Campos (MPos, WPos, FS, WCO, etc.)
            for part in parts[1:]:
                # Buscamos Posición de Máquina (MPos)
                if part.startswith('MPos:'):
                    coords_str = part.split(':')[1] # "0.000,0.000,0.000"
                    self._emit_coordinates(coords_str)
                
                # O Posición de Trabajo (WPos) si MPos no está
                elif part.startswith('WPos:'):
                    coords_str = part.split(':')[1]
                    self._emit_coordinates(coords_str)

                # Aquí puedes capturar WCO si lo necesitas
                # elif part.startswith('WCO:'): ...
            return

        # --- CASO 2: Información ([...]) ---
        if line.startswith('[') and line.endswith(']'):
            # Ej: [GC:G0 G54...] o [MSG:INFO...]
            msg_content = line[1:-1]
            if msg_content.startswith('MSG:'):
                self.log_message.emit(f"Mensaje: {msg_content[4:]}")
            elif msg_content.startswith('GC:'):
                self.log_message.emit(f"Config GC: {msg_content[3:]}")
            return

        # --- CASO 3: Errores y Alarmas ---
        if line.startswith('ALARM'):
            self.log_message.emit(f"¡ALARMA!: {line}")
            self._update_machine_state("Alarm")
        elif line.startswith('error'):
            self.log_message.emit(f"Error: {line}")

    def _emit_coordinates(self, coords_str):
        """ Helper para convertir string "x,y,z" a floats y emitir señal. """
        try:
            parts = coords_str.split(',')
            if len(parts) >= 3:
                x = float(parts[0])
                y = float(parts[1])
                z = float(parts[2])
                self.position_updated.emit(x, y, z)
        except ValueError:
            pass # Error de conversión, ignorar

    def _update_machine_state(self, new_state: str):
        if self.machine_state == new_state:
            return
        self.machine_state = new_state
        self.status_changed.emit(new_state)
        # La máquina está lista solo si está en Idle
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
    def unlock(self): self.send_command("$X")

    @Slot()
    def reset(self):
        """ Envía Ctrl+X para reiniciar FluidNC (Soft Reset). """
        self.log_message.emit("Enviando RESET (Ctrl+X)...")
        # \x18 es el carácter ASCII para Ctrl+X
        self.send_command("\x18")
    
    @Slot()
    def hold(self):
        """ Envía '!' para pausar el movimiento (Feed Hold). """
        self.log_message.emit("Enviando PAUSA (!)...")
        self.send_command("!")

    @Slot()
    def resume(self):
        """ Envía '~' para reanudar el movimiento (Cycle Start). """
        self.log_message.emit("Enviando REANUDAR (~)...")
        self.send_command("~")

    @Slot(bool)
    def on_connection_changed(self, is_connected: bool):
        if is_connected:
            self.connection_state = ConnectionState.CONNECTED
            self.log_message.emit("Conectado. Iniciando reportes...")
            # Forzar reporte de MPos ($10=1) y auto-reporte ($Report/Interval=200)
            
            self.command_to_send.emit("$10=1")
            self.command_to_send.emit("$Report/Interval=100")
            self.command_to_send.emit("?")
        else:
            self.connection_state = ConnectionState.DISCONNECTED
            self._update_machine_state("Desconectado")