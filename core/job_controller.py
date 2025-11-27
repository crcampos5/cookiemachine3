"""
core/job_controller.py
Controlador principal del trabajo (Job).
Versión: Soporta carga previa y botón inteligente Start/Resume.
"""

import time
import re
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, QThread

from core.template import Template
from core.gcode_processor import GcodeProcessor
import core.vision_utils as vision

class JobController(QObject):
    
    # Señales GUI
    log_message = Signal(str)
    progress_updated = Signal(int, int)
    job_finished = Signal()
    job_stopped = Signal()
    
    # Señales Hardware
    request_command = Signal(str)      
    request_lighting_on = Signal()     
    request_lighting_off = Signal()
    request_laser_on = Signal()        
    request_laser_off = Signal()

    def __init__(self):
        super().__init__()
        
        self.machine_is_connected = False
        self.machine_is_homed = False
        self._is_running = False
        self._is_paused = False
        self._machine_state = "Unknown"
        
        # Archivo cargado listo para ejecutarse
        self._loaded_file = None
        
        self._last_main_frame = None
        self._last_laser_frame = None
        
        self.template = Template()
        self.processor = GcodeProcessor()
        self.rows = 7
        self.cols = 6

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
        """ Solo guarda el archivo en memoria, listo para iniciar. """
        self._loaded_file = file_path
        self.log_message.emit(f"Archivo preparado: {file_path.split('/')[-1]}")
        self.log_message.emit("Presione 'Reanudar' para iniciar el trabajo.")

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
        try:
            self._run_process(file_path)
        except Exception as e:
            self.log_message.emit(f"🛑 Error crítico: {e}")
            self.stop_job()

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
        
        # 1. PARSEO
        gcode_draw, gcode_scan_pattern = self.processor.parse_gcode_file(file_path)
        
        if not gcode_scan_pattern:
            self.log_message.emit("⚠️ No se encontraron puntos de escaneo.")

        # 2. MATRIZ
        matrix = self.template.generar_matriz_coordenadas(tipo_mesa='Toda')
        total_cookies = self.rows * self.cols
        count = 0
        
        self.log_message.emit("🚀 Iniciando ciclo.")
        self.request_lighting_on.emit() 

        for i in range(self.rows):
            col_iter = range(self.cols) if i % 2 == 0 else range(self.cols - 1, -1, -1)
            
            for j in col_iter:
                if not self._is_running: return
                self._check_pause()
                
                count += 1
                pos_teorica = matrix[i, j]
                self.progress_updated.emit(count, total_cookies)
                self.log_message.emit(f"🍪 Procesando Galleta {count}")

                # --- PASO 1: VISIÓN ---
                self._move_and_wait(pos_teorica[0], pos_teorica[1])
                time.sleep(0.5)
                
                img = self._get_main_frame_sync()
                if img is None:
                    self.log_message.emit("❌ Error cámara. Saltando.")
                    continue

                centroids, _ = vision.find_cookie_centroids(img)
                if not centroids:
                    self.log_message.emit("⚠️ No se detectó galleta. Saltando.")
                    continue
                
                centro_img = (320, 240) 
                sorted_centroids = vision.sort_points_by_distance(centroids, centro_img)
                pixel_galleta = sorted_centroids[0]
                
                pos_real = vision.convert_pixel_to_mm(pixel_galleta, pos_teorica)
                self.log_message.emit(f"🎯 Galleta en: {pos_real}")

                # --- PASO 2: ESCANEO ---
                offset_x = pos_real[0]
                offset_y = pos_real[1]
                
                scan_route_real = self.processor.sumar_offset_xy(gcode_scan_pattern, offset_x, offset_y)
                
                self.request_lighting_off.emit()
                self.request_laser_on.emit()
                time.sleep(0.2)
                
                alturas_leidas = self._run_scan_routine(scan_route_real)
                
                self.request_laser_off.emit()
                self.request_lighting_on.emit()

                if not alturas_leidas:
                    self.log_message.emit("⚠️ Fallo escaneo. Usando altura base.")
                
                # --- PASO 3: PROCESAMIENTO ---
                z_umbral = self.processor.calcular_z_umbral(alturas_leidas, 0, 10)
                
                gcode_draw_moved = self.processor.sumar_offset_xy(gcode_draw, offset_x, offset_y)
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
        cmd = f"G0 X{x:.3f} Y{y:.3f}"
        self.request_command.emit(cmd)
        time.sleep(0.1) 
        self._wait_for_idle()

    def _wait_for_idle(self):
        while self._machine_state != "Idle":
            if not self._is_running: break
            self._check_pause()
            time.sleep(0.05)

    def _check_pause(self):
        while self._is_paused:
            time.sleep(0.1)
            if not self._is_running: break

    def _get_main_frame_sync(self):
        self._last_main_frame = None
        timeout = 0
        while self._last_main_frame is None:
            time.sleep(0.05)
            timeout += 0.05
            if timeout > 3.0 or not self._is_running: return None
        return self._last_main_frame

    def _run_scan_routine(self, gcode_scan):
        puntos_leidos = []
        patron = re.compile(r'X([-+]?\d*\.\d+)\s*Y([-+]?\d*\.\d+)')
        
        for line in gcode_scan:
            if not self._is_running: break
            
            self.request_command.emit(line)
            time.sleep(0.05)
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