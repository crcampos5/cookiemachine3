"""
core/sensor_head/lighting_controller.py
Controlador para el Arduino Nano (Sensor Head).
Se comunica con el firmware 'fastledlaser.ino'.
"""

from PySide6.QtCore import QObject, Signal, Slot, QTimer

class LightingController(QObject):
    """
    Cerebro del sistema de iluminación y láser.
    Genera los comandos textuales para enviar al Arduino Nano.
    """
    
    # Señales para comunicar con la GUI y el 'Cartero'
    log_message = Signal(str)
    command_to_send = Signal(str) # Se conecta a SerialConnection.send_line
    arduino_ready = Signal(bool)  # Indica cuando el Arduino termina de reiniciarse

    def __init__(self):
        super().__init__()
        self.is_connected = False
        print("LightingController (Sensor Arduino) inicializado.")

    # --- Gestión de Conexión e Inicialización ---

    @Slot(bool)
    def on_connection_changed(self, connected: bool):
        """
        Slot conectado a la señal connection_changed del SerialConnection.
        Maneja el reinicio automático del Arduino.
        """
        self.is_connected = connected
        if connected:
            self.log_message.emit("Arduino conectado. Esperando reinicio (2s)...")
            # Los Arduino Nano se reinician al abrir el puerto serial.
            # Esperamos 2 segundos antes de enviar cualquier comando.
            QTimer.singleShot(2000, self._mark_ready)
        else:
            self.arduino_ready.emit(False)

    def _mark_ready(self):
        """ Se llama pasados los 2 segundos de espera. """
        if self.is_connected:
            self.log_message.emit("Arduino listo para recibir comandos.")
            self.arduino_ready.emit(True)
            # Estado inicial seguro: Todo apagado
            self.apagar_todo()

    # --- Comandos de LEDs (Anillo WS2812) ---

    @Slot(int, int, int)
    def set_color_all(self, r: int, g: int, b: int):
        """
        Pinta todo el anillo de un color.
        Envía: RGB,r,g,b
        """
        cmd = f"RGB,{r},{g},{b}"
        self._send(cmd)

    @Slot(int, int, int, int)
    def set_pixel(self, index: int, r: int, g: int, b: int):
        """
        Pinta un LED individual.
        Envía: PIXEL,index,r,g,b
        """
        cmd = f"PIXEL,{index},{r},{g},{b}"
        self._send(cmd)

    @Slot(int)
    def set_brightness(self, level: int):
        """
        Ajusta el brillo global.
        Envía: BRIGHTNESS,level (0-255)
        """
        level = max(0, min(255, level)) # Asegurar rango
        cmd = f"BRIGHTNESS,{level}"
        self._send(cmd)

    @Slot()
    def leds_off(self):
        """
        Apaga todos los LEDs.
        Envía: CLEAR
        """
        self._send("CLEAR")

    # --- Comandos de Láser ---

    @Slot(int)
    def set_laser_power(self, power: int):
        """
        Ajusta la potencia del láser (PWM).
        Envía: LASER,power (0-255)
        """
        power = max(0, min(255, power))
        cmd = f"LASER,{power}"
        self._send(cmd)

    # --- Funciones de Alto Nivel (Convenience) ---

    @Slot()
    def laser_on_full(self):
        self.set_laser_power(255)

    @Slot()
    def laser_off(self):
        self.set_laser_power(0)

    @Slot()
    def apagar_todo(self):
        """ Apaga LEDs y Láser simultáneamente. """
        self.leds_off()
        self.laser_off()

    # --- Helper Interno ---

    def _send(self, cmd):
        """ Envía el comando al 'Cartero' si estamos conectados. """
        if self.is_connected:
            # SerialConnection añade el \n automáticamente
            self.command_to_send.emit(cmd)
        # else:
            # Opcional: Loguear si se intenta enviar desconectado
            # self.log_message.emit(f"Arduino desconectado. Cmd '{cmd}' ignorado.")