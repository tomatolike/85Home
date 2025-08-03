import socket
import threading
import json
from Core.utility import get_logger

class RobotTCPServer(threading.Thread):
    def __init__(self, host='0.0.0.0', port=9000, callback=None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.conn = None
        self.addr = None
        self.running = True
        self.status_callback = callback  # Optional: function to call with new status
        self.logger = get_logger(__name__)
        self.is_connected = False

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen(1)
            self.conn, self.addr = s.accept()
            self.is_connected = True
            while self.running:
                try:
                    data = self.conn.recv(4096)
                    if not data:
                        break
                    try:
                        status = json.loads(data.decode())
                        if self.status_callback:
                            self.status_callback(status)
                    except Exception as e:
                        self.logger.error(f"Error parsing status: {e}")
                except Exception as e:
                    self.logger.error(f"Connection error:{e}")
                    break
            self.is_connected = False

    def send_command(self, cmd_type, command):
        if self.conn:
            try:
                msg = json.dumps({'type': cmd_type, 'command': command})
                self.conn.sendall(msg.encode())
            except Exception as e:
                self.logger.error(f"Failed to send command: {e}")