from IrobotControl.IrobotControl import Irobot
from Core.utility import setup_logging, get_logger
import time
import threading
import socket
import json

class RobotTCPClient(threading.Thread):
    def __init__(self, irobot, server_ip, server_port):
        super().__init__(daemon=True)
        self.irobot = irobot
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.running = True

    def run(self):
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.server_ip, self.server_port))
                print("Connected to Home Assistant")
                while self.running:
                    data = self.sock.recv(1024)
                    if not data:
                        break
                    try:
                        msg = data.decode()
                        cmd = json.loads(msg)
                        if cmd['type'] == 'move':
                            self.irobot.PushMoveCommand(cmd['command'])
                        elif cmd['type'] == 'car':
                            self.irobot.PushCarCommand(cmd['command'])
                    except Exception as e:
                        print("Error processing command:", e)
            except Exception as e:
                print("TCP connection failed, retrying in 5s:", e)
                time.sleep(5)
            finally:
                if self.sock:
                    self.sock.close()
                    self.sock = None

    def send_status(self, status):
        try:
            if self.sock:
                self.sock.sendall(json.dumps(status).encode())
        except Exception as e:
            print("Failed to send status:", e)

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    robot = Irobot()
    tcp_client = RobotTCPClient(robot, server_ip='192.168.0.236', server_port=9000)  # Set correct IP/port
    tcp_client.start()

    try:
        robot.EnterMode('Passive')
        last_status_update_time = 0
        while True:
            robot.UpdateMoveStatus()
            now = time.time()
            if now - last_status_update_time > 1:
                status = robot.GetKeyValueStatus()
                tcp_client.send_status(status)
                last_status_update_time = now
            time.sleep(0.33)
    except Exception as e:
        logger.info("Robot control stopped due to an error: %s", e)