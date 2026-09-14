"""Gestionnaire de connexion USB / GRBL."""
import time
import threading
import serial


class LaserUSBController:
    """Gestionnaire de connexion USB / GRBL"""
    def __init__(self):
        self.ser = None
        self._lock = threading.Lock()

    def is_connected(self):
        return bool(self.ser and self.ser.is_open)

    def connect(self, port, baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)
            self.ser.write(b"\r\n\r\n")
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            return True
        except Exception as e:
            print(f"Erreur connexion : {e}")
            self.ser = None
            return False

    def disconnect(self):
        with self._lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = None

    def send_command(self, cmd):
        with self._lock:
            if not (self.ser and self.ser.is_open):
                return "Non connecté"
            try:
                self.ser.write(f"{cmd.strip()}\n".encode('utf-8'))
                response_lines = []
                start_time = time.time()
                while True:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        if line == 'ok' or line.startswith('error') or line.startswith('ALARM'):
                            break
                    if time.time() - start_time > 2.0:
                        break
                return "\n".join(response_lines) if response_lines else "Pas de réponse"
            except Exception as e:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                return f"ERROR: Connexion perdue ({e})"

    def send_raw_byte(self, raw_bytes):
        with self._lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(raw_bytes)
                    self.ser.flush()
                except Exception as e:
                    print(f"Erreur envoi commande temps réel : {e}")
