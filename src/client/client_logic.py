import sys
import os
import io
from tkinter import *
from tkinter import messagebox as tkMessageBox
from PIL import Image, ImageTk

# Thêm đường dẫn để tìm thấy module src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

try:
    from src.client.rtsp_core import RtspCore
except ImportError:
    # Fallback import
    try:
        from rtsp_core import RtspCore
    except:
        print("Lỗi: Không tìm thấy RtspCore. Hãy chắc chắn bạn đang chạy từ thư mục gốc.")
        sys.exit(1)

class Client:
    """
    GUI Tkinter (Legacy) - Đã cập nhật để dùng JitterBuffer
    """
    
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        
        # [Role B] Khởi tạo Core mới
        self.core = RtspCore(serveraddr, serverport, rtpport, filename)
        
        # [Role B] Bắt đầu vòng lặp lấy ảnh từ Buffer ra giao diện
        self.check_buffer()

    def createWidgets(self):
        """Build GUI."""
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)
        
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)
        
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)
        
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)
        
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
        self.label.configure(text="Ready to connect...")
    
    def setupMovie(self):
        self.core.sendSetup()
    
    def playMovie(self):
        self.core.sendPlay()
    
    def pauseMovie(self):
        self.core.sendPause()
    
    def exitClient(self):
        self.core.sendTeardown()
        self.master.destroy()

    def check_buffer(self):
        """
        [Role B New Logic] Kiểm tra buffer và cập nhật UI
        """
        frame = self.core.jitter_buffer.get()
        if frame:
            self.updateMovie(frame)
        
        # Gọi lại sau 10ms
        self.master.after(10, self.check_buffer)

    def updateMovie(self, imageBytes):
        """Hiển thị ảnh lên Label"""
        try:
            image_stream = io.BytesIO(imageBytes)
            image = Image.open(image_stream)
            photo = ImageTk.PhotoImage(image)
            self.label.configure(image=photo, height=288) 
            self.label.image = photo
        except Exception as e:
            pass

    def handler(self):
        self.core.sendPause()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:
            self.core.sendPlay()

# -------------------------------------------------------
# PHẦN KHỞI CHẠY (MAIN)
# -------------------------------------------------------
if __name__ == "__main__":
    print("--- CLIENT STARTING ---") # Dòng debug để biết code đã chạy
    
    # Thiết lập tham số mặc định nếu không nhập
    serverAddr = '127.0.0.1'
    serverPort = 3636
    rtpPort = 25000
    fileName = 'movie.Mjpeg'

    # Nếu có tham số dòng lệnh thì lấy đè lên
    if len(sys.argv) > 1: serverAddr = sys.argv[1]
    if len(sys.argv) > 2: serverPort = int(sys.argv[2])
    if len(sys.argv) > 3: rtpPort = int(sys.argv[3])
    if len(sys.argv) > 4: fileName = sys.argv[4]

    root = Tk()
    root.title(f"Client Legacy (Test Role B) - Port {rtpPort}")
    
    # Căn giữa màn hình
    w = 600; h = 380
    ws = root.winfo_screenwidth(); hs = root.winfo_screenheight()
    x = (ws/2) - (w/2); y = (hs/2) - (h/2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))
    
    # Khởi tạo Client
    app = Client(root, serverAddr, serverPort, rtpPort, fileName)
    root.mainloop()