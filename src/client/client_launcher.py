import sys
import os
from PyQt6.QtWidgets import QApplication 

# Thêm đường dẫn src vào hệ thống để import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# -------------------------------------------------------------
# CẤU HÌNH GIAO DIỆN
# 'legacy': Giao diện Tkinter cũ
# 'modern': Giao diện PyQt5/6 hiện đại (Cyberpunk)
# -------------------------------------------------------------
GUI_MODE = 'modern'  
# -------------------------------------------------------------

def run_legacy_gui(serverAddr, serverPort, rtpPort, fileName):
    """ Chạy giao diện Tkinter cũ (Để test logic cơ bản). """
    try:
        from src.client.client_logic import Client
        from tkinter import Tk
        root = Tk()
        app = Client(root, serverAddr, serverPort, rtpPort, fileName)
        app.master.title(f"RTSP Client (Legacy) - {fileName}")    
        root.mainloop()
    except Exception as e:
        print(f"[Legacy Error] {e}")

def run_modern_gui(server_ip, server_port, rtp_port, filename):
    """ Chạy giao diện PyQt hiện đại (Final Product). """
    print(f"[*] Launching Modern UI...")
    print(f"    Target: {server_ip}:{server_port} | File: {filename}")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        from src.client.gui import ModernClient
        
        # Khởi tạo cửa sổ giao diện
        window = ModernClient(server_ip, server_port, rtp_port, filename)
        window.show()
        
        # Chạy vòng lặp sự kiện
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"[CRITICAL ERROR] Không thể khởi động GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        # Kiểm tra tham số đầu vào
        if len(sys.argv) < 5:
            # Chế độ test nhanh (nếu lười gõ tham số)
            print("[Info] Thiếu tham số -> Chạy chế độ mặc định (Test Mode)")
            server_ip = "127.0.0.1"
            server_port = "3636"
            rtp_port = "25000"
            filename = "movie_hd.Mjpeg"
        else:
            server_ip = sys.argv[1]
            server_port = sys.argv[2]
            rtp_port = sys.argv[3]
            filename = sys.argv[4]

        # Chọn chế độ chạy
        if GUI_MODE == 'modern':
            run_modern_gui(server_ip, server_port, rtp_port, filename)
        else:
            run_legacy_gui(server_ip, server_port, rtp_port, filename)
            
    except Exception as e:
        print(f"[Lỗi] {e}")
        sys.exit(1)