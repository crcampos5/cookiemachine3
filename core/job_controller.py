"""
core/job_controller.py
Controlador principal del trabajo (Job).
Versión: Soporta carga previa y botón inteligente Start/Resume.
"""

import time
import re
import numpy as np
import cv2 as cv
from PySide6.QtCore import QObject, Signal, Slot, QThread, QCoreApplication

from core.tray_manager import TrayManager
from core.gcode_processor import GcodeProcessor
import core.vision_utils as vision
from settings.settings_manager import SettingsManager

class JobController(QObject):
    
    # Señales GUI
    log_message = Signal(str)
    progress_updated = Signal(int, int)
    job_finished = Signal()
    job_stopped = Signal()
    gcode_loaded_info = Signal(dict)
    processed_image_ready = Signal(np.ndarray)

    
    # Señales Hardware
    request_command = Signal(str)
    request_move_tool = Signal(int,int,str)      
    request_lighting_on = Signal()     
    request_lighting_off = Signal()
    request_laser_on = Signal()        
    request_laser_off = Signal()

    def __init__(self, settings_manager: SettingsManager):
        super().__init__()

        self.settings = settings_manager
        self.machine_is_connected = False
        self.machine_is_homed = False
        self._is_running = False
        self._is_paused = False
        self._machine_state = "Unknown"
        
        # Archivo cargado listo para ejecutarse
        self._loaded_file = None
        
        self._last_main_frame = None
        self._last_laser_frame = None
        self._loaded_operations = []
        self._injectors_data = None
        self._metadata_gcode = None
        self._centro_camera = [117.5,122]
        
        self.tray_manager = TrayManager(self.settings)
        self.processor = GcodeProcessor()
        table_size = self.settings.get("table_size")
        self.rows = table_size[0]
        self.cols = table_size[1]
        self.valor_pixel_to_mm = self.settings.get("valor_pixel_to_mm")

    # --- SLOTS DE ENTRADA ---

    @Slot(str)
    def update_machine_status(self, status: str):
        self._machine_state = status

    @Slot(np.ndarray)
    def update_main_frame(self, frame):
        self._last_main_frame = frame

    @Slot(np.ndarray)
    def update_laser_frame(self, frame):
        self._last_laser_frame = frame

    @Slot(bool)
    def update_connection_status(self, is_connected):
        self.machine_is_connected = is_connected

    @Slot(bool)
    def update_homing_status(self, is_homed):
        self.machine_is_homed = is_homed

    # --- CONTROL INTELIGENTE DEL TRABAJO ---

    @Slot(str)
    def load_file(self, file_path):
        """ 
        Parsea el archivo, extrae metadata para la GUI y prepara las operaciones.
        """
        self.log_message.emit(f"📂 Cargando: {file_path.split('/')[-1]}...")
        
        # 1. Usar el procesador para leer TODO
        try:
            self._metadata_gcode, self._injectors_data, self._loaded_operations = self.processor.parse_custom_gcode(file_path)
            
            # 2. Guardar operaciones para cuando se pulse RUN
            self._loaded_file = file_path # Mantener por compatibilidad

            if self._metadata_gcode:
                self._centro_camera = self._metadata_gcode["centro"]
            
            # 3. Emitir datos a la GUI (InjectorPanel)
            if self._injectors_data:
                self.gcode_loaded_info.emit(self._injectors_data)
                self.log_message.emit("✅ Inyectores configurados según archivo.")
            else:
                self.log_message.emit("⚠️ Archivo sin definición de inyectores.")

            
        except Exception as e:
            self.log_message.emit(f"❌ Error leyendo archivo: {e}")

    @Slot()
    def on_resume_request(self):
        """ 
        Lógica inteligente para el botón 'RUN':
        1. Si no está corriendo y hay archivo -> INICIA
        2. Si está pausado -> REANUDA
        3. Si ya está corriendo normal -> Ignorar
        """
        # VERIFICACIÓN ANTES DE INICIAR
        ready, msg = self.verify_ready_to_run()
        if not ready:
            self.log_message.emit(f"Error de inicio: {msg}")
            # Opcional: emitir señal de error para un popup
            return
        
        if not self._is_running:
            if self._loaded_file:
                self.start_job(self._loaded_file)
            else:
                self.log_message.emit("⚠️ No hay archivo cargado. Cargue un G-code primero.")
        elif self._is_paused:
            self.resume_job()
        else:
            # Si ya está corriendo, enviar '~' igual por si FluidNC está pausado a nivel firmware
            self.request_command.emit("~")

    # --- MÉTODOS INTERNOS DE CONTROL ---
       

    def start_job(self, file_path):
        self._is_running = True
        self._is_paused = False
        self._run_process(file_path)
        #try:
        #    self._run_process(file_path)
        #except Exception as e:
        #    self.log_message.emit(f"🛑 Error crítico: {e}")
        #    self.stop_job()

    @Slot()
    def stop_job(self):
        self._is_running = False
        self.log_message.emit("🛑 Trabajo detenido.")
        self.request_command.emit("!") 
        self.request_lighting_off.emit()
        self.request_laser_off.emit()
        self.job_stopped.emit()

    def pause_job(self):
        self._is_paused = True
        self.request_command.emit("!")

    def resume_job(self):
        self._is_paused = False
        self.request_command.emit("~")

    # --- LÓGICA PRINCIPAL ---

    def _run_process(self, file_path):
        self.log_message.emit("📂 Procesando archivo...")
        
        # 1. Obtener gcode de escaneo 
        operation = self._loaded_operations[0]
        injector_id = operation["gcode_lines"]
        gcode_operation = operation["gcode_lines"]
        gcode_scan = self.processor.resample_gcode_scan(gcode_operation, 2)
        
        if not gcode_scan:
            self.log_message.emit("⚠️ No se encontraron puntos de escaneo.")

        # 2. MATRIZ DE CUADRANTES
        matriz_cuadrantes = self.tray_manager.generar_matriz_cuadrantes(tipo_mesa='Toda')
        total_cookies = self.rows * self.cols
        count = 0
        
        self.log_message.emit("🚀 Iniciando ciclo.")
        #self.request_lighting_on.emit() 

        for i in range(self.rows):
            col_iter = range(self.cols) if i % 2 == 0 else range(self.cols - 1, -1, -1)
            
            for j in col_iter:
                if not self._is_running: return
                self._check_pause()
                
                count += 1
                pos_camara = np.array(matriz_cuadrantes[i, j]) + np.array(self._centro_camera)
                self.progress_updated.emit(count, total_cookies)
                self.log_message.emit(f"🍪 Procesando Galleta {count}")

                # --- PASO 1: VISIÓN ---
                self.request_lighting_on.emit()
                time.sleep(2)
                self._move_and_wait(pos_camara[0], pos_camara[1])
                time.sleep(2)
                
                img = self._get_main_frame_sync()
                if img is None:
                    self.log_message.emit("❌ Error cámara. Saltando.")
                    continue

                cv.imwrite("test_img.jpg", img)

                centroids, debug_img = vision.find_cookie_pose(img)

                if debug_img is not None:
                    self.processed_image_ready.emit(debug_img)

                if not centroids:
                    self.log_message.emit("⚠️ No se detectó galleta. Saltando.")
                    continue

                cx, cy, angle = centroids[0]
                
                pos_real = vision.convert_pixel_to_mm((cx, cy), pos_camara, (640, 480), self.valor_pixel_to_mm)
                self.log_message.emit(f"🎯 Galleta en: {pos_real}")

                # --- PASO 2: ESCANEO ---
                offset_x = pos_real[0] - self._centro_camera[0]
                offset_y = pos_real[1] - self._centro_camera[1]
                
                scan_route_real = self.processor.sumar_offset_xy(gcode_scan, offset_x, offset_y)
                
                self.request_lighting_off.emit()
                time.sleep(0.3)
                self.request_laser_on.emit()
                time.sleep(0.5)
                
                alturas_leidas = self._run_scan_routine(scan_route_real)
                
                self.request_laser_off.emit()
                #self.request_lighting_on.emit()

                if not alturas_leidas:
                    self.log_message.emit("⚠️ Fallo escaneo. Usando altura base.")
                
                # --- PASO 3: PROCESAMIENTO ---
                z_umbral = self.processor.calcular_z_umbral(alturas_leidas, 0, 10)
                
                gcode_draw_moved = self.processor.sumar_offset_xy(gcode_operation, offset_x, offset_y)
                gcode_final = self.processor.aplicar_mapa_alturas(gcode_draw_moved, alturas_leidas, z_umbral)
                gcode_final = self.processor.suavizar_z(gcode_final)
                
                # --- PASO 4: EJECUCIÓN ---
                self.log_message.emit("🎨 Decorando...")
                self._execute_gcode_block(gcode_final)
                self.log_message.emit("✅ Terminada.")

        self.log_message.emit("🏁 Trabajo completado.")
        self.request_command.emit("$H")
        self.request_lighting_off.emit()
        self._is_running = False
        self.job_finished.emit()

    # --- RUTINAS DE AYUDA ---

    def verify_ready_to_run(self):
        """
        Realiza comprobaciones de seguridad antes de mover la máquina.
        Retorna: (bool, str) -> (Éxito, Mensaje de error)
        """
        # 1. Verificar Conexión
        # Asumiendo que machine_controller tiene acceso a la conexión o un método is_connected()
        if not self.machine_is_connected:
            return False, "La máquina está desconectada. Verifique la conexion de la maquina."

        # 2. Verificar Home (Referenciado)
        # Necesitamos que machine_controller tenga una bandera 'is_homed'
        if not self.machine_is_homed:
            return False, "La máquina no ha realizado Home. Ejecute el homing primero."

        # 3. Futuras verificaciones (Espacio para tu implementación)
        # Ejemplo: if not self.check_air_pressure(): return False, "Presión de aire baja"
        
        return True, "Sistema listo"

    def _move_and_wait(self, x, y):
        self.request_move_tool.emit(x,y,"camera")
        self._wait_for_idle()

    def _wait_for_idle(self):
        while self._machine_state != "Idle":
            if not self._is_running: break
            self._check_pause()

    def _check_pause(self):
        while self._is_paused:
            if not self._is_running: break

    def _get_main_frame_sync(self):
        self._last_main_frame = None
        timeout = 0
        while self._last_main_frame is None:
            QCoreApplication.processEvents()
            time.sleep(0.05)
            timeout += 0.05
            if timeout > 3.0 or not self._is_running: return None
        return self._last_main_frame

    def _run_scan_routine(self, gcode_scan):
        puntos_leidos = []
        patron = re.compile(r'X([-+]?\d*\.\d+)\s*Y([-+]?\d*\.\d+)')
        self.request_command.emit("F500")
        
        for line in gcode_scan:
            if not self._is_running: break
            
            self.request_command.emit(line)
            #time.sleep(0.05)
            self._wait_for_idle()
            
            match = patron.search(line)
            if match:
                x = float(match.group(1))
                y = float(match.group(2))
                img = self._get_laser_frame_sync()
                if img is not None:
                    z = 0.0 
                    puntos_leidos.append((x, y, z))
        
        return puntos_leidos

    def _get_laser_frame_sync(self):
        self._last_laser_frame = None
        timeout = 0
        while self._last_laser_frame is None:
            time.sleep(0.05)
            timeout += 0.05
            if timeout > 1.0 or not self._is_running: return None
        return self._last_laser_frame

    def _execute_gcode_block(self, gcode_lines):
        for line in gcode_lines:
            if not self._is_running: break
            self._check_pause()
            self.request_command.emit(line)
            time.sleep(0.02)
        self._wait_for_idle()