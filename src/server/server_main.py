import sys
import socket

# --- IMPORT MODULES ---
try:
    from src.server.server_worker import ServerWorker
except ImportError:
    try:
        from server_worker import ServerWorker
    except ImportError:
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from server_worker import ServerWorker

class Server:    
    """
    RTSP SERVER MAIN.
    Chịu trách nhiệm: Mở cổng lắng nghe, Chấp nhận kết nối, Tạo Worker.
    """
    def main(self):
        # 1. Kiểm tra tham số
        if len(sys.argv) < 2:
            print("[Usage: python server_main.py <Server_Port>]")
            print("Example: python server_main.py 8554")
            sys.exit(1)

        try:
            SERVER_PORT = int(sys.argv[1])
        except ValueError:
            print("[Error] Port must be a number.")
            sys.exit(1)

        # 2. Khởi tạo Socket
        rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rtspSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            rtspSocket.bind(('', SERVER_PORT))
            print(f"[*] Server is running & listening on port {SERVER_PORT}...")
        except Exception as e:
            print(f"[Error] Could not bind to port {SERVER_PORT}: {e}")
            return

        rtspSocket.listen(5)        

        # 3. Vòng lặp chính (Main Loop)
        try:
            while True:
                clientInfo = {}
                # Chờ kết nối mới
                clientInfo['rtspSocket'] = rtspSocket.accept()
                
                client_addr = clientInfo['rtspSocket'][1]
                print(f"[*] Accepted connection from {client_addr[0]}:{client_addr[1]}")
                
                # Tạo Worker xử lý riêng cho Client này
                ServerWorker(clientInfo).run()
                
        except KeyboardInterrupt:
            print("\n[!] Server stopped by user.")
            rtspSocket.close()
            sys.exit(0)

if __name__ == "__main__":
    (Server()).main()