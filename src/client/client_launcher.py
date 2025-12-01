import sys
import os
from tkinter import Tk

# -------------------------------------------------------------
# CẤU HÌNH CHỌN GIAO DIỆN TẠI ĐÂY
# 'legacy': Giao diện Tkinter cũ (Cho Nhật test logic)
# 'modern': Giao diện PyQt/Figma mới (Cao làm)
GUI_MODE = 'legacy' 
# -------------------------------------------------------------

def run_legacy_gui(serverAddr, serverPort, rtpPort, fileName):
    """Chạy giao diện Tkinter cũ."""
    try:
        from src.client.client_logic import Client
    except ImportError:
        # Fallback import nếu chạy tại root
        try:
            from client_logic import Client
        except ImportError:
            # Fallback import nếu chạy trong src/client
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from client_logic import Client

    root = Tk()
    app = Client(root, serverAddr, serverPort, rtpPort, fileName)
    app.master.title(f"RTSP Client (Legacy) - {fileName}")    
    root.mainloop()
    
    # Dọn dẹp
    try:
        app.exitClient()
    except:
        pass

def run_modern_gui(serverAddr, serverPort, rtpPort, fileName):
    """Chạy giao diện PyQt hiện đại (Sẽ implement sau)."""
    print("[Launcher] Đang khởi động Modern UI...")
    
    try:
        # Giả sử file giao diện mới tên là gui_modern.py
        from src.client.gui import ModernClient
        # PyQt cần QApplication, code cụ thể sẽ nằm trong gui_modern.py
        app = ModernClient(serverAddr, serverPort, rtpPort, fileName)
        app.run()
    except ImportError:
        print("[LỖI] Chưa tìm thấy file 'src/client/gui_modern.py'.")
        print("Hãy tạo file này và import RtspClientCore vào đó.")
    except Exception as e:
        print(f"[LỖI] Không thể chạy Modern UI: {e}")

# -------------------------------------------------------------

if __name__ == "__main__":
    try:
        if len(sys.argv) < 5:
            # Hỗ trợ chạy default để đỡ gõ nhiều khi test
            # python client_launcher.py -> Sẽ tự điền tham số mặc định
            print("[Warning] Thiếu tham số, dùng tham số mặc định để test nhanh.")
            serverAddr = "127.0.0.1"
            serverPort = 8554 # Lưu ý: Port này phải khớp với Server
            rtpPort = 25000
            fileName = "movie.Mjpeg"
        else:
            serverAddr = sys.argv[1]
            serverPort = sys.argv[2]
            rtpPort = sys.argv[3]
            fileName = sys.argv[4]    
    except:
        print("[!] Error parsing arguments.")
        sys.exit(1)
    
    print(f"[*] Launcher started. Mode: {GUI_MODE}")
    print(f"[*] Target: {serverAddr}:{serverPort} | Video: {fileName}")

    if GUI_MODE == 'legacy':
        run_legacy_gui(serverAddr, serverPort, rtpPort, fileName)
    elif GUI_MODE == 'modern':
        run_modern_gui(serverAddr, serverPort, rtpPort, fileName)
    else:
        print("Unknown GUI Mode.")
    
    sys.exit(0)