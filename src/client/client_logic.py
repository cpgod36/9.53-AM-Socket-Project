import sys
import os
import io
from tkinter import *
from tkinter import messagebox as tkMessageBox
from tkinter import simpledialog 
from PIL import Image, ImageTk

# --- IMPORT CORE LOGIC ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    from src.client.rtsp_core import RtspCore
except ImportError:
    print("[Error] Core not found")
    sys.exit(1)

class Client:
    """
    LEGACY GUI: Giao diện kiểm thử sử dụng thư viện Tkinter.
    Dùng để test nhanh các chức năng cốt lõi trước khi đưa sang Modern UI.
    """
    # =========================================================================
    # INITIALIZATION (KHỞI TẠO)
    # =========================================================================
    
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        
        # Khởi tạo Core và truyền hàm log_to_console
        self.core = RtspCore(serveraddr, serverport, rtpport, filename, self.log_to_console)
        
        # Dựng giao diện
        self.createWidgets()
        
        # Bắt đầu vòng lặp cập nhật video
        self.check_buffer()

    def log_to_console(self, msg, tag):
        """ Hàm callback để nhận log từ Core và in ra Terminal. """
        print(f"[Tkinter Log] [{tag}] {msg}")

    # =========================================================================
    # UI CONSTRUCTION (DỰNG HÌNH)
    # =========================================================================
    
    def createWidgets(self):
        """ Tạo các nút bấm và khung hiển thị. """
        # --- Hàng nút 1: Các chức năng cơ bản ---
        self.setup = Button(self.master, width=15, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.core.sendSetup
        self.setup.grid(row=1, column=0, padx=2, pady=2)
        
        self.start = Button(self.master, width=15, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.core.sendPlay
        self.start.grid(row=1, column=1, padx=2, pady=2)
        
        self.pause = Button(self.master, width=15, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.core.sendPause
        self.pause.grid(row=1, column=2, padx=2, pady=2)
        
        self.teardown = Button(self.master, width=15, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)
        
        # --- Hàng nút 2: Các chức năng nâng cao (Replay, Switch) ---
        self.replay = Button(self.master, width=15, padx=3, pady=3, bg="yellow")
        self.replay["text"] = "Replay"
        self.replay["command"] = self.core.sendReplay
        self.replay.grid(row=2, column=0, padx=2, pady=2)
        
        self.switch = Button(self.master, width=15, padx=3, pady=3, bg="cyan")
        self.switch["text"] = "Switch File"
        self.switch["command"] = self.switchFileHandler
        self.switch.grid(row=2, column=1, padx=2, pady=2)

        # --- Màn hình hiển thị Video ---
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
        self.label.configure(text="Ready...")

    # =========================================================================
    # LOGIC HANDLERS (XỬ LÝ DỮ LIỆU)
    # =========================================================================
    
    def check_buffer(self):
        """
        Vòng lặp lấy dữ liệu từ Buffer (Polling Loop).
        Thay thế cho while True để không chặn giao diện.
        """
        item = self.core.jitter_buffer.get()
        if item:
            frame_data = item[0]  # Lấy phần dữ liệu khung hình
            self.updateMovie(frame_data)

        # Gọi lại hàm này sau 10ms
        self.master.after(10, self.check_buffer)

    def updateMovie(self, imageBytes):
        """ Chuyển đổi bytes thành ảnh và hiển thị lên Tkinter Label. """
        try:
            image_stream = io.BytesIO(imageBytes)
            image = Image.open(image_stream)
            # Resize nhẹ cho vừa khung Tkinter
            image = image.resize((380, 280)) 
            photo = ImageTk.PhotoImage(image)
            self.label.configure(image=photo, height=280) 
            self.label.image = photo
        except:
            pass
       
    # =========================================================================
    # EVENT HANDLERS (SỰ KIỆN)
    # =========================================================================
     
    def switchFileHandler(self):
        """Hỏi người dùng tên file mới và gọi Core switch"""
        new_file = simpledialog.askstring("Switch File", "Nhập tên file (VD: movie.Mjpeg):", parent=self.master)
        if new_file:
            # Chạy trong thread riêng để không đơ giao diện khi kết nối lại
            import threading
            threading.Thread(target=self.core.switch_media, args=(new_file,)).start()
    
    def exitClient(self):
        """ Gửi Teardown và đóng cửa sổ. """
        self.core.sendTeardown()
        self.master.destroy()

    def handler(self):
        """ Xử lý khi bấm nút X trên cửa sổ. """
        self.core.sendTeardown()
        self.master.destroy()
        
        