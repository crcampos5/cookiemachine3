"""
core/serial_connection.py
Maneja la capa física de la conexión serial usando QSerialPort.
Esta clase es 100% no bloqueante (asíncrona).

Versión 2.1: Corregido AttributeError 'isBusy'.
"""

from PySide6.QtCore import QObject, Signal, Slot, QIODevice, QTextStream
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
        self.serial = QSerialPort()
        
        # El TextStream para leer líneas fácilmente
        self.text_stream = None 
        
        # Conectar señales nativas de QSerialPort a nuestros slots
        self.serial.readyRead.connect(self.on_ready_read)
        self.serial.errorOccurred.connect(self.on_error)

    # --- Slots Públicos (Llamados desde la GUI o el Cerebro) ---

    @Slot()
    def find_ports(self):
        """ 
        Busca puertos y emite la lista con nombre Y descripción. 
        """
        print("--- DEBUG: Buscando puertos... ---")
        try:
            ports = QSerialPortInfo.availablePorts()
            port_list = []
            if not ports:
                self.log_message.emit("No se encontraron puertos COM.")
            
            for port in ports:
                # --- LÍNEA DE ERROR ELIMINADA ---
                # if port.isBusy():  <--- Esta línea causaba el error y fue eliminada.
                #     continue
                
                port_info = {
                    'name': port.portName(),
                    'description': port.description(),
                    'manufacturer': port.manufacturer()
                }
                port_list.append(port_info)
                print(f"--- DEBUG: Puerto encontrado: {port_info} ---")

            self.port_list_updated.emit(port_list)
            
        except Exception as e:
            # Captura cualquier otro error, incluido el que acabamos de corregir
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
            self.text_stream = QTextStream(self.serial)
            self.text_stream.setEncoding(QTextStream.Encoding.Utf8)

            self.log_message.emit(f"Conectado a {port_name}")
            self.connection_changed.emit(True)
            self.serial.write(b'\x18\n') # Reiniciar FluidNC
        else:
            # Si el puerto estaba ocupado, este es el lugar donde fallará
            self.log_message.emit(f"Error al abrir puerto: {self.serial.errorString()}")
            self.connection_changed.emit(False)

    @Slot()
    def disconnect_from(self):
        """ Cierra la conexión. """
        if self.serial.isOpen():
            self.serial.close()
            
        if self.text_stream:
            self.text_stream = None
            
        self.log_message.emit("Desconectado.")
        self.connection_changed.emit(False)

    @Slot(str)
    def send_line(self, line: str):
        """ Envía una línea de texto al puerto. """
        if self.serial.isOpen():
            self.serial.write((line + '\n').encode('utf-8'))
        else:
            self.log_message.emit("No conectado. No se envió comando.")

    # --- Slots Internos (Manejo Asíncrono) ---

    @Slot()
    def on_ready_read(self):
        """
        ¡La magia asíncrona! (Versión QTextStream)
        """
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
        """ Se activa si el puerto se desconecta o da error. """
        if error == QSerialPort.NoError:
            return
        
        if error == QSerialPort.ResourceError: # Desconexión
             self.log_message.emit(f"Error de puerto: {self.serial.errorString()} (Desconexión)")
             self.disconnect_from() # Gestionar la desconexión