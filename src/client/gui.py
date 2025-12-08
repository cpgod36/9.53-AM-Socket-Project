import sys
import os
import io
import datetime
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, QLabel,
                             QGraphicsDropShadowEffect, QFrame, QVBoxLayout, QTextEdit,
                             QSizePolicy, QFileDialog, QProgressBar)
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPixmap, QImage, QPainter, QPainterPath 
from PyQt6.QtCore import Qt, QTimer

from PIL import Image

# --- IMPORT LOGIC CORE ---
try:
    from src.client.rtsp_core import RtspCore
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from src.client.rtsp_core import RtspCore

class ModernClient(QMainWindow):
    # =========================================================================
    # INITIALIZATION (KHỞI TẠO)
    # =========================================================================
    
    def __init__(self, server_addr, server_port, rtp_port, file_name):
        super().__init__()
        
        # 1. Lưu tham số
        self.server_addr = server_addr
        self.server_port = int(server_port)
        self.rtp_port = int(rtp_port)
        self.file_name = file_name
        
        # 2. Cấu hình giao diện cơ bản
        self.font_family = self.load_custom_fonts()
        self.current_status_w = 285
        self.DESIGN_WIDTH = 1920
        self.DESIGN_HEIGHT = 1080 
        
        self.setWindowTitle(f"9:53 AM Socket Project - {file_name}")
        self.resize(960, 540)
        
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        self.setup_background()
        
        self.frame_update_counter = 0
        
        # --- BIẾN TÍNH TOÁN FPS ---
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # --- BIẾN BUFFERING ---
        self.empty_buffer_count = 0
        self.is_buffering = True 
        self.BUFFER_THRESHOLD = 60
        self.last_buf_size = -1
        self.stuck_buffer_count = 0
        
        # KHỞI TẠO CORE TRƯỚC KHI SETUP UI
        try:
            self.core = RtspCore(self.server_addr, self.server_port, self.rtp_port, self.file_name, self.handle_log)
        except Exception as e:
            print(f"[GUI] Không thể khởi tạo Core: {e}")
            self.core = None
            
        # SETUP UI  
        self.setup_ui()
        
        # Cập nhật trạng thái icon ban đầu
        self.change_status("connecting")

        # Timer cập nhật Video
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_frame)
        self.timer.start(40)
     
    # Hàm load font tùy chỉnh
    def load_custom_fonts(self):
        """ Nạp font từ file assets """
        # 1. Inter Bold
        font_path = "assets/fonts/Inter-Bold.ttf"
        self.font_inter = "Segoe UI"
        if os.path.exists(font_path):
            fid = QFontDatabase.addApplicationFont(font_path)
            if fid >= 0: self.font_inter = QFontDatabase.applicationFontFamilies(fid)[0]

        # 2. Poppins ExtraBold
        poppins_path = "assets/fonts/Poppins-ExtraBold.ttf"
        self.font_poppins = "Segoe UI"
        if os.path.exists(poppins_path):
            fid = QFontDatabase.addApplicationFont(poppins_path)
            if fid >= 0: self.font_poppins = QFontDatabase.applicationFontFamilies(fid)[0]
            
        # 3. Science Gothic (Cho khung Chat)
        code_font_path = "assets/fonts/ScienceGothic.ttf"
        self.font_code = "Consolas" 
        if os.path.exists(code_font_path):
            fid = QFontDatabase.addApplicationFont(code_font_path)
            if fid >= 0: self.font_code = QFontDatabase.applicationFontFamilies(fid)[0]
            
        return self.font_inter
    
    # =========================================================================
    # UI CONSTRUCTION (DỰNG GIAO DIỆN)
    # =========================================================================
    
    # Thiết lập background cho cửa sổ
    def setup_background(self):
        """ Thiết lập hình nền """
        bg_path = "assets/ui_packs/background/mainbg.svg"
        if os.path.exists(bg_path):
            self.setStyleSheet(f"#CentralWidget {{ border-image: url('{bg_path}') 0 0 0 0 stretch stretch; }}")
        else:
            self.setStyleSheet("#CentralWidget { background-color: #1a1c2c; }")
    
    # Thiết lập các thành phần UI        
    def setup_ui(self):
        """ Khởi tạo toàn bộ Widget """ 
        
        # --- LOGO ---
        self.lbl_logo = QLabel(self.central_widget)
        self.lbl_logo.setObjectName("lbl_logo")
        logo_path = "assets/ui_packs/background/logo.svg"
        if os.path.exists(logo_path):
            self.lbl_logo.setStyleSheet(f"border-image: url('{logo_path}') 0 0 0 0 stretch stretch; background: transparent;")
        else:
            # Fallback
            self.lbl_logo.setText("LOGO NOT FOUND")
            self.lbl_logo.setStyleSheet("color: red; font-weight: bold;")     
        
        # --- NEON LINES ---
        self.line_left = QFrame(self.central_widget)
        shadow_l = QGraphicsDropShadowEffect(); shadow_l.setBlurRadius(20); shadow_l.setColor(QColor(107, 226, 190, 188)); shadow_l.setOffset(0, 0)
        self.line_left.setGraphicsEffect(shadow_l)
        self.line_left.setStyleSheet("background-color: #49FF3E; border: none;")

        self.line_right = QFrame(self.central_widget)
        shadow_r = QGraphicsDropShadowEffect(); shadow_r.setBlurRadius(20); shadow_r.setColor(QColor(107, 226, 190, 188)); shadow_r.setOffset(0, 0)
        self.line_right.setGraphicsEffect(shadow_r)
        self.line_right.setStyleSheet("background-color: #49FF3E; border: none;")
        
        # --- BUTTONS ---
        btn_path = "assets/ui_packs/button/"
        
        self.btn_setup = QPushButton(self.central_widget)
        self.btn_setup.setObjectName("btn_setup")
        self.style_button(self.btn_setup, btn_path + "setup button.svg")
        
        self.btn_play = QPushButton(self.central_widget)
        self.btn_play.setObjectName("btn_play")
        self.style_button(self.btn_play, btn_path + "play button.svg")
        
        self.btn_pause = QPushButton(self.central_widget)
        self.btn_pause.setObjectName("btn_pause")
        self.style_button(self.btn_pause, btn_path + "pause button.svg")
        
        self.btn_teardown = QPushButton(self.central_widget)
        self.btn_teardown.setObjectName("btn_teardown")
        self.style_button(self.btn_teardown, btn_path + "teardown button.svg")
        
        self.btn_replay = QPushButton(self.central_widget)
        self.btn_replay.setObjectName("btn_replay")
        self.style_button(self.btn_replay, btn_path + "replay button.svg")
        
        self.btn_switch = QPushButton(self.central_widget)
        self.btn_switch.setObjectName("btn_switch")
        self.style_button(self.btn_switch, btn_path + "switch button.svg")

        # Gắn sự kiện cho nút
        if self.core:
            self.btn_setup.clicked.connect(self.core.sendSetup)
            self.btn_play.clicked.connect(self.core.sendPlay)
            self.btn_pause.clicked.connect(self.core.sendPause)
            self.btn_teardown.clicked.connect(self.on_teardown)
            self.btn_replay.clicked.connect(self.on_replay)
            self.btn_switch.clicked.connect(self.open_file_dialog)
        
        for btn in [self.btn_setup, self.btn_play, self.btn_pause, self.btn_teardown, self.btn_replay, self.btn_switch]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- LABELS ---
        
        # Buffer label
        self.lbl_buffer = QLabel(self.central_widget)
        self.lbl_buffer.setObjectName("lbl_buffer")
        self.load_svg_label(self.lbl_buffer, "assets/ui_packs/text/BUFFER_.svg")
        self.lbl_status_icon = QLabel(self.central_widget)
        self.set_status_image("assets/ui_packs/icon/is connecting icon.svg")
        
        # IP and PORT label
        info_text = (
            f"<html><head/><body>"
            f"<p style='line-height: 69%; margin-top: 0px; margin-bottom: 0px;'>"
            f"IP: {self.server_addr}<br>"
            f"PORT: {self.server_port}"
            f"</p></body></html>"
        )
        
        self.lbl_connection_info = QLabel(info_text, self.central_widget)
        self.lbl_connection_info.setObjectName("lbl_connection_info")
        self.lbl_connection_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_connection_info.setStyleSheet("color: #FFFFFF; background-color: transparent;")
        
        # FPS & LOSS label
        stats_text = (
            "<html><head/><body>"
            "<p style='line-height: 85%; margin-top: 0px; margin-bottom: 0px;'>"
            "<span style='color:#3EFF5A;'>FPS:</span> <span style='color:#FFFFFF;'>0</span><br>"
            "<span style='color:#3EFF5A;'>LOSS:</span> <span style='color:#FFFFFF;'>0.0%</span>"
            "</p></body></html>"
        )
        self.lbl_stats = QLabel(stats_text, self.central_widget)
        self.lbl_stats.setObjectName("lbl_stats")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        shadow_stats = QGraphicsDropShadowEffect()
        shadow_stats.setBlurRadius(10)
        shadow_stats.setOffset(0, 4)
        shadow_stats.setColor(QColor(62, 255, 90, 97)) 
        self.lbl_stats.setGraphicsEffect(shadow_stats)
        self.lbl_stats.setStyleSheet("background-color: transparent;")
        
        # Buffering label (OVERLAY)
        self.lbl_loading = QLabel("BUFFERING... 0%", self.central_widget)
        self.lbl_loading.setObjectName("lbl_loading")
        self.lbl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_loading.setStyleSheet("""
            QLabel {
                color: #FFFFFF; 
                border-radius: 15px;
                padding: 10px;
            }
        """)
        shadow_load = QGraphicsDropShadowEffect()
        shadow_load.setBlurRadius(35)
        shadow_load.setOffset(0, 0)
        shadow_load.setColor(QColor(255, 255, 255, 180)) 
        self.lbl_loading.setGraphicsEffect(shadow_load)

        self.lbl_loading.hide()
        
        # --- VIDEO FRAME ---
        self.video_container = QLabel(self.central_widget)
        shadow_vid = QGraphicsDropShadowEffect()
        shadow_vid.setBlurRadius(30) 
        shadow_vid.setOffset(0, 0)  
        shadow_vid.setColor(QColor(255, 255, 255, 180)) 
        
        self.video_container.setGraphicsEffect(shadow_vid)
        self.video_container.setStyleSheet("background-color: #1C2025; border: 1px solid #49FF3E; border-radius: 20px;")
        self.video_container.setScaledContents(True)
        
        # --- CHAT FRAME ---
        self.chat_container = QFrame(self.central_widget)
        shadow_chat = QGraphicsDropShadowEffect()
        shadow_chat.setBlurRadius(30) 
        shadow_chat.setOffset(0, 0)  
        shadow_chat.setColor(QColor(255, 255, 255, 180))
        self.chat_container.setGraphicsEffect(shadow_chat)
        self.chat_container.setStyleSheet("background-color: #1C2025; border: 1px solid #49FF3E; border-radius: 20px;")

        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(5, 25, 5, 15)
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        # self.log_box.setPlaceholderText("System initialized...")
        self.log_box.setStyleSheet("border: none; background-color: transparent; color: #00ff99; font-family: 'Consolas', monospace; font-size: 12px;")
        self.chat_layout.addWidget(self.log_box)
        
        self.lbl_chat_title = QLabel(self.central_widget)
        self.load_svg_label(self.lbl_chat_title, "assets/ui_packs/text/CHAT.svg")
        
        # --- BUFFER PROGRESS BAR ---
        self.buffer_bar = QProgressBar(self.central_widget)
        self.buffer_bar.setObjectName("buffer_bar")
        
        self.buffer_bar.setRange(0, 100) 
        self.buffer_bar.setValue(0)
        self.buffer_bar.setTextVisible(False)
        self.buffer_bar.setStyleSheet("""
            QProgressBar {
                background-color: transparent; /* Nền trong suốt */
                border: none;
            }
            QProgressBar::chunk {
                background-color: #FFFFFF; /* Màu Trắng */
                width: 8px; 
                margin-right: 2px; /* Khoảng cách giữa các vạch */
            }
        """)
    
    # =========================================================================
    # 3. UI HELPERS (HÀM PHỤ TRỢ GIAO DIỆN)
    # =========================================================================   
    
    # Hàm load SVG vào QLabel
    def load_svg_label(self, label, path):
        """ Tải ảnh SVG vào QLabel """
        if os.path.exists(path):
            label.setStyleSheet(f"border-image: url('{path}') 0 0 0 0 stretch stretch; background: transparent;")
        else:
            label.setText("ERR"); label.setStyleSheet("color: red;")
    
    # Hàm style nút bấm
    def style_button(self, button, img_path):
        """ Áp dụng style cho nút bấm từ ảnh SVG """
        if os.path.exists(img_path):
            button.setStyleSheet(f"""
                QPushButton {{ border-image: url("{img_path}") 0 0 0 0 stretch stretch; border: none; background: transparent; padding: 8px; }}
                QPushButton:hover {{ padding: 0px; }}
                QPushButton:pressed {{ padding: 4px; background-color: rgba(255, 255, 255, 0.3); border-radius: 10px; }}
            """)
        else:
            button.setStyleSheet("background-color: red;")
    
    # Hàm set ảnh trạng thái
    def set_status_image(self, img_path):
        """ Đặt ảnh cho lbl_status_icon """
        if os.path.exists(img_path):
            self.lbl_status_icon.setStyleSheet(f"border-image: url('{img_path}') 0 0 0 0 stretch stretch; background: transparent;")
    
    # Hàm thay đổi trạng thái kết nối
    def change_status(self, state):
        """
        Thay đổi biểu tượng trạng thái kết nối.
        Các trạng thái: "connecting", "streaming"
        """
        path, width = "", 0
        if state == "connecting":
            path = "assets/ui_packs/icon/is connecting icon.svg"
            width = 259
        elif state == "streaming":
            path = "assets/ui_packs/icon/is streaming icon.svg"
            width = 259
        self.current_status_w = width
        self.set_status_image(path)
        self.update_responsive_layout()    
    
    # =========================================================================
    # RESPONSIVE LAYOUT (TỰ ĐỘNG CO GIÃN)
    # =========================================================================
    
    # Sự kiện resize cửa sổ
    def resizeEvent(self, event):
        """ Bắt sự kiện thay đổi kích thước cửa sổ để duy trì tỉ lệ 16:9 và cập nhật layout."""
        target_ratio = 16 / 9
        curr_w = event.size().width()
        curr_h = event.size().height()
        expected_h = int(curr_w / target_ratio)
        if abs(curr_h - expected_h) > 2: self.resize(curr_w, expected_h)
        self.update_responsive_layout()
        super().resizeEvent(event)
      
    # Hàm set geometry với tỉ lệ scale  
    def set_geometry(self, widget, x, y, w, h, sx, sy):
        """ Đặt vị trí và kích thước của widget dựa trên tỉ lệ scale. """
        new_x, new_y, new_w, new_h = int(x * sx), int(y * sy), int(w * sx), int(h * sy)
        if h > 0 and new_h < 1: new_h = 1
        if w > 0 and new_w < 1: new_w = 1
        widget.setGeometry(new_x, new_y, new_w, new_h)
    
    # Cập nhật layout theo tỉ lệ cửa sổ
    def update_responsive_layout(self):
        """
        Cập nhật vị trí và kích thước của các thành phần UI dựa trên kích thước cửa sổ hiện tại.
        Sử dụng tỉ lệ scale dựa trên kích thước thiết kế gốc (1920x1080)
        """
        scale_x = self.width() / self.DESIGN_WIDTH
        scale_y = self.height() / self.DESIGN_HEIGHT
        
        # --- Logo & Lines ---
        self.set_geometry(self.lbl_logo, 215, 29, 475, 160, scale_x, scale_y)
        self.set_geometry(self.line_left, 0, 89, 196, 2, scale_x, scale_y)
        self.set_geometry(self.line_right, 647, 89, 1273, 2, scale_x, scale_y)
        
        # --- Buttons ---
        self.set_geometry(self.btn_setup, 215, 859, 193, 65, scale_x, scale_y)  
        self.set_geometry(self.btn_play, 436, 859, 193, 65, scale_x, scale_y)        
        self.set_geometry(self.btn_pause, 657, 859, 193, 65, scale_x, scale_y)      
        self.set_geometry(self.btn_teardown, 878, 859, 284, 65, scale_x, scale_y) 
        self.set_geometry(self.btn_replay, 1190, 859, 227, 65, scale_x, scale_y)
        self.set_geometry(self.btn_switch, 1445, 859, 258, 65, scale_x, scale_y)
        
        # --- Labels & Frames ---
        self.set_geometry(self.lbl_buffer, 215, 972, 197, 56, scale_x, scale_y) 
        self.set_geometry(self.lbl_stats, 1515, 949, 200, 80, scale_x, scale_y)
        self.set_geometry(self.video_container, 215, 232, 1054, 593, scale_x, scale_y)
        self.set_geometry(self.chat_container, 1279, 230, 425, 593, scale_x, scale_y)
        self.set_geometry(self.lbl_chat_title, 1300, 250, 87, 25, scale_x, scale_y)
        self.set_geometry(self.lbl_status_icon, 1419, 189, self.current_status_w, 29, scale_x, scale_y)
        self.set_geometry(self.lbl_connection_info, 1455, 142, 200, 50, scale_x, scale_y)
        
        # Cấu hình Font cho lbl_connection_info(IP & PORT)
        font_size = int(13 * scale_y) 
        font = QFont(self.font_poppins, font_size)
        font.setWeight(QFont.Weight.ExtraBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.3) 
        self.lbl_connection_info.setFont(font)

        
        # Cấu hình Font cho lbl_stats (FPS & LOSS)
        stats_size = int(19 * scale_y)
        font = QFont(self.font_poppins, stats_size)
        font.setWeight(QFont.Weight.ExtraBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        self.lbl_stats.setFont(font)
        
        # Buffer Bar
        self.set_geometry(self.buffer_bar, 424, 972, 1061, 48, scale_x, scale_y)
        
        # Loading Overlay Center
        VID_X = int(215 * scale_x)
        VID_Y = int(232 * scale_y)
        VID_W = int(1054 * scale_x)
        VID_H = int(593 * scale_y)
        LBL_W = int(400 * scale_x)
        LBL_H = int(80 * scale_y)
        
        new_x = VID_X + (VID_W - LBL_W) // 2
        new_y = VID_Y + (VID_H - LBL_H) // 2
        self.lbl_loading.setGeometry(new_x, new_y, LBL_W, LBL_H)
        
        font_size = int(32 * scale_y)
        font = QFont(self.font_poppins, font_size)
        font.setWeight(QFont.Weight.ExtraBold)
        self.lbl_loading.setFont(font)
    
    # =========================================================================
    # LOGIC & EVENT HANDLERS (LOGIC CHÍNH)
    # =========================================================================       
    
    # Hàm nhận log từ Core
    def handle_log(self, message, tag):
        """ Nhận log từ Core và in ra khung Chat. """
        if not hasattr(self, 'log_box'): return
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Color Coding
        color = "#00ff99" # SYSTEM
        if tag == "CLIENT": color = "#ffcc00"
        if tag == "SERVER": color = "#00ccff"
        if tag == "ERROR":  color = "#ff3366"
        
        formatted_message = message.replace("\n", "<br>")
        
        html = (
            f"<div style='font-family: \"{self.font_code}\"; font-size: 7px; line-height: 100%; margin-bottom: 5px;'>"
            f"<span style='color:#666666'>[{timestamp}]</span> "
            f"<b style='color:{color}'>[{tag}]</b><br>"
            f"<span style='color:#eeeeee'>{formatted_message}</span>"
            f"</div>"
        )        
        self.log_box.append(html)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    # Hàm cập nhật khung video
    def update_video_frame(self):
        """ Cập nhật khung video từ Jitter Buffer và xử lý logic Buffering/Playing. """
        if not self.core: return
        
        current_buf_size = self.core.jitter_buffer.qsize()
        self.buffer_bar.setValue(current_buf_size)
        
        # Chỉ xử lý khi đang ở trạng thái PLAYING
        if self.core.state != self.core.PLAYING:
            return
        
        # --- LOGIC PRE-BUFFERING ---
        if self.is_buffering:
            if current_buf_size > 0 and current_buf_size == self.last_buf_size:
                self.stuck_buffer_count += 1
            else:
                self.stuck_buffer_count = 0 
                self.last_buf_size = current_buf_size

            if current_buf_size > 0:
                threshold = self.BUFFER_THRESHOLD if self.BUFFER_THRESHOLD > 0 else 1
                percent = int((current_buf_size / threshold) * 100)
                if percent > 100: percent = 100
                
                self.lbl_loading.setText(f"BUFFERING... {percent}%")
                self.lbl_loading.show()
                self.lbl_loading.raise_()
            else:
                self.lbl_loading.hide()
            
            # Kiểm tra ngưỡng nạp
            if current_buf_size < self.BUFFER_THRESHOLD:
                return 
            else:
                self.is_buffering = False
                self.lbl_loading.hide()
                self.stuck_buffer_count = 0

        # --- LOGIC PLAYING ---
        item = self.core.jitter_buffer.get()
        
        if item:
            # Reset biến đếm buffer rỗng/stuck
            self.empty_buffer_count = 0
            self.stuck_buffer_count = 0

            frame_data, pkt_count, loss_rate = item
            try:
                # VẼ ẢNH LÊN KHUNG VIDEO
                
                # Xử lý ảnh từ bytes sang QPixmap
                image = Image.open(io.BytesIO(frame_data))
                im_data = image.convert("RGBA").tobytes("raw", "RGBA")
                qim = QImage(im_data, image.size[0], image.size[1], QImage.Format.Format_RGBA8888)
                original_pixmap = QPixmap.fromImage(qim)
                
                # Resize và Bo góc 
                target_size = self.video_container.size()
                scaled_pixmap = original_pixmap.scaled(target_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                final_pixmap = QPixmap(target_size); 
                final_pixmap.fill(QColor("transparent"))
                painter = QPainter(final_pixmap); 
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                path = QPainterPath(); 
                rect = self.video_container.rect().adjusted(1, 1, -1, -1)
                path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 20, 20)
                
                painter.setClipPath(path); 
                painter.drawPixmap(0, 0, scaled_pixmap); 
                painter.end()
                
                self.video_container.setPixmap(final_pixmap)
                
                if self.core.state == self.core.PLAYING:
                    self.change_status("streaming")

                # Cập nhật FPS/LOSS
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    self.current_fps = self.fps_counter
                    self.fps_counter = 0
                    self.last_fps_time = current_time
                    html_text = f"<html><head/><body><p style='line-height: 85%; margin:0;'><span style='color:#3EFF5A;'>FPS:</span> <span style='color:#FFFFFF;'>{self.current_fps}</span><br><span style='color:#3EFF5A;'>LOSS:</span> <span style='color:#FFFFFF;'>{loss_rate:.1f}%</span></p></body></html>"
                    self.lbl_stats.setText(html_text)

            except Exception:
                pass
        
        else:
            # Buffer rỗng
            if self.core.state == self.core.PLAYING:
                self.empty_buffer_count += 1
                if self.empty_buffer_count > 50:
                    self.handle_log("🛑 STREAM_STATUS: End of video stream.", "SYSTEM")
                    self.reset_ui_to_idle()
   
    # Hàm đặt lại giao diện về trạng thái nghỉ
    def reset_ui_to_idle(self):
        """Đưa giao diện về trạng thái nghỉ (Connecting)"""
        self.change_status("connecting") 
        self.buffer_bar.setValue(0)
        self.lbl_loading.hide() 
        
        reset_html = (
            "<html><head/><body>"
            "<p style='line-height: 85%; margin:0;'>"
            "<span style='color:#3EFF5A;'>FPS:</span> <span style='color:#FFFFFF;'>0</span><br>"
            "<span style='color:#3EFF5A;'>LOSS:</span> <span style='color:#FFFFFF;'>0.0%</span>"
            "</p></body></html>"
        )
        self.lbl_stats.setText(reset_html)
        
        self.is_buffering = True 
        self.fps_counter = 0
        self.current_fps = 0
        self.stuck_buffer_count = 0
                 
    # Xử lý nút Teardown        
    def on_teardown(self):
        """ Xử lý nút Teardown: Gửi lệnh dừng và đặt lại giao diện. """
        self.is_buffering = True 
        self.buffer_bar.setValue(0)
        self.close()
       
    # Hàm xử lý sự kiện đóng cửa sổ 
    def closeEvent(self, event):
        """
        Hàm này TỰ ĐỘNG chạy khi người dùng bấm nút X hoặc gọi self.close().
        Đây là nơi tập trung logic dọn dẹp hiện trường.
        """
        print("[GUI] Application is closing...")
        
        if self.core:
            # Force gửi teardown dù đang ở trạng thái nào
            self.core.sendTeardown()
            
        # 2. Đồng ý cho đóng cửa sổ
        event.accept()
      
    # Xử lý nút Replay  
    def on_replay(self):
        """
        Xử lý nút Replay: Reset giao diện về chế độ Nạp trước khi gọi Core.
        """
        print("[GUI] Replay requested -> Resetting Buffer State.")
        if self.core:
                self.core.jitter_buffer.clear() 
        self.is_buffering = True
        self.buffer_bar.setValue(0)
        self.lbl_loading.hide() 

        if self.core:
            threading.Thread(target=self.core.sendReplay).start()
        
    def open_file_dialog(self):
        """ Mở hộp thoại chọn file video và yêu cầu Core chuyển kênh. """
        default_dir = os.path.join(os.getcwd(), "assets", "video")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select MJPEG Video", 
            default_dir, 
            "MJPEG Files (*.Mjpeg);;All Files (*)"
        )
        
        if file_path:
            new_filename = os.path.basename(file_path)
            
            if new_filename == self.file_name:
                print(f"[GUI] File {new_filename} is already playing.")
                return

            print(f"[GUI] User selected new file: {new_filename}")
            
            self.file_name = new_filename
            self.setWindowTitle(f"9:53 AM Socket Project - {new_filename}")
            self.video_container.clear()

            if self.core:
                self.core.jitter_buffer.clear() 
                
            self.is_buffering = True  
            self.buffer_bar.setValue(0) 
            self.lbl_loading.hide()  
            
            reset_html = (
                "<html><head/><body>"
                "<p style='line-height: 85%; margin:0;'>"
                "<span style='color:#3EFF5A;'>FPS:</span> <span style='color:#FFFFFF;'>0</span><br>"
                "<span style='color:#3EFF5A;'>LOSS:</span> <span style='color:#FFFFFF;'>0.0%</span>"
                "</p></body></html>"
            )
            self.lbl_stats.setText(reset_html)
            self.fps_counter = 0
            self.current_fps = 0

            if self.core:
                threading.Thread(target=self.core.switch_media, args=(new_filename,)).start()    
    
# TESTING THE GUI     
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernClient("127.0.0.1", "3636", "25000", "movie_hd.Mjpeg")
    window.show()
    sys.exit(app.exec())