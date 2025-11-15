"""
core/serial_connection.py
Maneja la capa física de la conexión serial usando QSerialPort.
Esta clase es 100% no bloqueante (asíncrona).

Versión 3.0: Lógica de configuración eliminada.
"""

from PySide6.QtCore import QObject, Signal, Slot, QIODevice, QTextStream
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

class SerialConnection(QObject):
    """
    El 'Cartero'. Maneja la conexión física y emite líneas de texto.
    """
    
    port_list_updated = Signal(list)
    connection_changed = Signal(bool)
    log_message = Signal(str)
    line_received = Signal(str)

    def __init__(self):
        super().__init__()
        self.serial = QSerialPort()
        self.text_stream = None 
        
        self.serial.readyRead.connect(self.on_ready_read)
        self.serial.errorOccurred.connect(self.on_error)

    @Slot()
    def find_ports(self):
        """ 
        Busca puertos y emite la lista con nombre Y descripción. 
        """
        try:
            ports = QSerialPortInfo.availablePorts()
            port_list = []
            if not ports:
                self.log_message.emit("No se encontraron puertos COM.")
            
            for port in ports:
                port_info = {
                    'name': port.portName(),
                    'description': port.description(),
                    'manufacturer': port.manufacturer()
                }
                port_list.append(port_info)

            self.port_list_updated.emit(port_list)
            
        except Exception as e:
            self.log_message.emit(f"Error al buscar puertos: {e}")

    @Slot(str, int)
    def connect_to(self, port_name: str, baud_rate: int = 115200):
        """ 
        Intenta conectarse al puerto. No envía configuración.
        """
        if self.serial.isOpen():
            self.log_message.emit("Ya conectado.")
            return

        self.serial.setPortName(port_name)
        self.serial.setBaudRate(baud_rate)
        
        if self.serial.open(QIODevice.ReadWrite):
            self.text_stream = QTextStream(self.serial)
            self.text_stream.setEncoding(QTextStream.Encoding.Utf8)

            self.log_message.emit(f"Puerto {port_name} abierto. Esperando al 'Cerebro' para configurar.")
            self.connection_changed.emit(True)
            # --- TODA LA LÓGICA DE CONFIGURACIÓN HA SIDO ELIMINADA ---
            
        else:
            self.log_message.emit(f"Error al abrir puerto: {self.serial.errorString()}")
            self.connection_changed.emit(False)

    @Slot()
    def disconnect_from(self):
        if self.serial.isOpen():
            self.serial.close()
        if self.text_stream:
            self.text_stream = None
        self.log_message.emit("Desconectado.")
        self.connection_changed.emit(False)

    @Slot(str)
    def send_line(self, line: str):
        if self.serial.isOpen():
            self.serial.write((line + '\n').encode('utf-8'))
        else:
            self.log_message.emit("No conectado. No se envió comando.")

    @Slot()
    def on_ready_read(self):
        if not self.text_stream:
            return
        while not self.text_stream.atEnd():
            line_str = self.text_stream.readLine()
            if line_str is None:
                break 
            line_str = line_str.strip()
            if line_str:
                self.line_received.emit(line_str)

    @Slot(QSerialPort.SerialPortError)
    def on_error(self, error: QSerialPort.SerialPortError):
        if error == QSerialPort.NoError:
            return
        if error == QSerialPort.ResourceError:
             self.log_message.emit(f"Error de puerto: {self.serial.errorString()} (Desconexión)")
             self.disconnect_from()