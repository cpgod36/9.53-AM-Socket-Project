import sys
import socket

# --- SỬA LẠI IMPORT ---
try:
    from src.server.server_worker import ServerWorker
except ImportError:
    try:
        from server_worker import ServerWorker
    except ImportError:
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from server_worker import ServerWorker
# ----------------------

class Server:    
    
    def main(self):
        if len(sys.argv) < 2:
            print("[Usage: python server_main.py <Server_Port>]")
            print("Example: python server_main.py 8554")
            sys.exit(1)

        try:
            SERVER_PORT = int(sys.argv[1])
        except ValueError:
            print("[Error] Port must be a number.")
            sys.exit(1)

        rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        rtspSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            rtspSocket.bind(('', SERVER_PORT))
            print(f"[*] Server is running & listening on port {SERVER_PORT}...")
        except Exception as e:
            print(f"[Error] Could not bind to port {SERVER_PORT}: {e}")
            return

        rtspSocket.listen(5)        

        # Receive client info (address,port) through RTSP/TCP session
        try:
            while True:
                clientInfo = {}
                clientInfo['rtspSocket'] = rtspSocket.accept()
                
                client_addr = clientInfo['rtspSocket'][1]
                print(f"[*] Accepted connection from {client_addr[0]}:{client_addr[1]}")
                
                ServerWorker(clientInfo).run()
                
        except KeyboardInterrupt:
            # Cho phép bấm Ctrl+C để tắt Server nhẹ nhàng
            print("\n[!] Server stopped by user.")
            rtspSocket.close()
            sys.exit(0)

if __name__ == "__main__":
    (Server()).main()