"""
core/serial_connection.py
Maneja la capa física de la conexión serial usando QSerialPort.
Esta clase es 100% no bloqueante (asíncrona).

Versión 3.1: Sin QTextStream. Manejo manual de bytes para máxima estabilidad.
"""

from PySide6.QtCore import QObject, Signal, Slot, QIODevice, QByteArray
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

class SerialConnection(QObject):
    """
    El 'Cartero'. Maneja la conexión física y emite líneas de texto.
    """
    
    # Señales (Salida)
    port_list_updated = Signal(list)
    connection_changed = Signal(bool)
    log_message = Signal(str)
    line_received = Signal(str) # ¡La señal de datos clave!

    def __init__(self):
        super().__init__()
        # Creamos el puerto. Al darle (self), nos aseguramos de que
        # se mueva de hilo junto con esta clase.
        self.serial = QSerialPort(self)
        
        # Búfer para acumular fragmentos de datos hasta tener una línea completa
        self.read_buffer = QByteArray()
        
        # Conectar señales nativas de QSerialPort a nuestros slots
        self.serial.readyRead.connect(self.on_ready_read)
        self.serial.errorOccurred.connect(self.on_error)

    # --- Slots Públicos (Llamados desde la GUI o el Cerebro) ---

    @Slot()
    def find_ports(self):
        """ Busca puertos y emite la lista. """
        try:
            ports = QSerialPortInfo.availablePorts()
            port_list = []
            
            for port in ports:
                port_info = {
                    'name': port.portName(),
                    'description': port.description(),
                    'manufacturer': port.manufacturer()
                }
                port_list.append(port_info)
            
            if not port_list:
                self.log_message.emit("No se encontraron puertos COM.")
                
            self.port_list_updated.emit(port_list)
            
        except Exception as e:
            self.log_message.emit(f"Error al buscar puertos: {e}")

    @Slot(str, int)
    def connect_to(self, port_name: str, baud_rate: int = 115200):
        """ Intenta conectarse al puerto. """
        if self.serial.isOpen():
            self.log_message.emit("Ya conectado.")
            return

        self.serial.setPortName(port_name)
        self.serial.setBaudRate(baud_rate)
        
        if self.serial.open(QIODevice.ReadWrite):
            self.log_message.emit(f"Conectado a {port_name}")
            self.connection_changed.emit(True)
            # Limpiamos búferes previos
            self.read_buffer.clear()
            self.serial.clear()
            # Reiniciar FluidNC
            self.serial.write(b'\x18\n') 
        else:
            self.log_message.emit(f"Error al abrir puerto: {self.serial.errorString()}")
            self.connection_changed.emit(False)

    @Slot()
    def disconnect_from(self):
        """ Cierra la conexión. """
        if self.serial.isOpen():
            self.serial.close()
        self.log_message.emit("Desconectado.")
        self.connection_changed.emit(False)

    @Slot(str)
    def send_line(self, line: str):
        """ Envía una línea de texto al puerto. """
        if self.serial.isOpen():
            # Convertimos el string a bytes (utf-8) y añadimos nueva línea
            self.log_message.emit(line)
            self.serial.write((line + '\n').encode('utf-8'))
        else:
            self.log_message.emit("No conectado. No se envió comando.")

    # --- Slots Internos (Manejo Asíncrono Manual) ---

    @Slot()
    def on_ready_read(self):
        """
        Se activa cuando llegan nuevos datos brutos (bytes).
        Los acumulamos y buscamos saltos de línea.
        """
        data = self.serial.readAll()
        self.read_buffer.append(data)
        
        # Mientras encontremos un salto de línea ('\n') en el búfer...
        while b'\n' in self.read_buffer:
            # Encontrar la posición del salto de línea
            newline_index = self.read_buffer.indexOf(b'\n')
            
            # Extraer la línea (hasta el salto)
            line_data = self.read_buffer.left(newline_index)
            
            # Eliminar esa línea del búfer (incluyendo el \n)
            self.read_buffer = self.read_buffer.mid(newline_index + 1)
            
            # Procesar la línea extraída
            try:
                # .trimmed() elimina espacios y \r extra
                line_str = line_data.data().decode('utf-8').strip()
                if line_str: # Si no está vacía, emitirla
                    self.line_received.emit(line_str)
            except UnicodeDecodeError:
                # Esto puede pasar si llega basura al inicio de la conexión
                pass

    @Slot(QSerialPort.SerialPortError)
    def on_error(self, error: QSerialPort.SerialPortError):
        if error == QSerialPort.NoError:
            return
        
        if error == QSerialPort.ResourceError: # Desconexión física
             self.log_message.emit(f"Error de puerto: {self.serial.errorString()} (Desconexión)")
             self.disconnect_from()