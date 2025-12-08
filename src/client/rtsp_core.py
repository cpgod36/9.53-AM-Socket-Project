import socket
import threading
import sys
import traceback
import os
import time

# --- IMPORT MODULES ---
try:
    from src.common.rtp_packet import RtpPacket
    from src.client.buffer import JitterBuffer
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from src.common.rtp_packet import RtpPacket
    from src.client.buffer import JitterBuffer

class RtspCore:
    """
    CORE LOGIC: Xử lý toàn bộ giao thức mạng (RTSP/RTP).
    Chịu trách nhiệm: Kết nối, Gửi lệnh, Nhận dữ liệu, Ghép gói tin, Tính toán Loss.
    """
    
    # --- CONSTANTS: RTSP STATES ---
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT
    
    # --- CONSTANTS: RTSP METHODS ---
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    
    def __init__(self, server_addr, server_port, rtp_port, file_name, on_log_callback=None):
        """ Khởi tạo Core và kết nối ngay lập tức. """
        # Thông số kết nối
        self.serverAddr = server_addr
        self.serverPort = int(server_port)
        self.rtpPort = int(rtp_port)
        self.fileName = file_name
        
        # Callback để gửi Log ra UI (Giao diện)
        self.on_log = on_log_callback 
        
        # Trạng thái phiên làm việc
        self.state = self.INIT
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        
        # Socket RTSP & RTP
        self.rtspSocket = None
        self.rtpSocket = None
        
        # Cấu hình Log (True: In chi tiết, False: Im lặng khi chạy tự động)
        self.verbose = True
        
        # Bộ đệm dữ liệu & Điều khiển luồng
        self.jitter_buffer = JitterBuffer()
        self.playEvent = threading.Event()
        
        # KẾT NỐI NGAY LẬP TỨC
        self.connectToServer()

    # =========================================================================
    # SECTION 1: SYSTEM UTILITIES (LOGGING & CONNECTION)
    # =========================================================================
    
    # Hàm log hệ thống và gửi callback ra GUI
    def log(self, message, tag="SYSTEM"):
        """ Gửi log ra GUI thông qua callback. """
        print(f"[{tag}] {message}")
        if self.on_log:
            self.on_log(message, tag)

    # Hàm kết nối TCP tới server RTSP 
    def connectToServer(self):
        """ Thiết lập kết nối TCP tới Server. """
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            if self.verbose:
                self.log(f"Connected to {self.serverAddr}:{self.serverPort}", "SYSTEM")
        except:
            self.log(f"Failed to connect to {self.serverAddr}", "ERROR")

    # =========================================================================
    # SECTION 2: ADVANCED FEATURES (RECONNECT, SWITCH, REPLAY)
    # =========================================================================
    
    # Hàm kết nối lại với thông số mới (Dùng cho nút Switch/Connect)
    def reconnect(self, new_ip, new_port, new_file):
        """
        Quy trình tái kết nối sạch sẽ (Clean Reconnect).
        Dùng cho cả tính năng Switch File và Replay.
        """
        # Log thông báo
        action_log = ""
        if new_file == self.fileName:
            action_log = f"↺ REPLAY_SEQ: Resetting buffer for [{new_file}]..."
        else:
            action_log = f"📂 MEDIA_SWITCH: Target target >> [{new_file}]"

        self.verbose = False
        self.log(action_log, "SYSTEM")
        
        # 1. Dọn dẹp phiên cũ
        self.playEvent.set()
        
        if self.state != self.INIT:
            self.sendTeardown()
            time.sleep(0.1)
            
        # 2. Đóng Socket (TCP & UDP) để giải phóng Port
        if self.rtspSocket:
            try: self.rtspSocket.close()
            except: pass
            self.rtspSocket = None 
            
        if self.rtpSocket:
            try: self.rtpSocket.close()
            except: pass
            self.rtpSocket = None 
            
        # 3. Cập nhật thông số mới
        self.serverAddr = new_ip
        self.serverPort = int(new_port)
        self.fileName = new_file
        
        # 4. Reset trạng thái về ban đầu
        self.state = self.INIT
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.jitter_buffer.clear()
        
        # 5. Kết nối lại (TCP)
        self.connectToServer()
        
        # 6. Tự động SETUP -> PLAY (Auto-stream)
        time.sleep(0.1)
        self.sendSetup()
        
        # Chạy thread riêng để chờ Setup xong rồi mới Play
        def delayed_play():
            time.sleep(0.2)
            self.sendPlay()
            
            self.verbose = True 
            self.log("✅ SYNC_COMPLETE: Stream active & stable.", "SYSTEM")
            
        threading.Thread(target=delayed_play).start()
       
    # Hàm phụ trợ đổi file   
    def switch_media(self, filename):
        """ Hàm phụ trợ đổi file (giữ nguyên IP/Port) """
        self.reconnect(self.serverAddr, self.serverPort, filename)\
         
    # Hàm phát lại video hiện tại
    def sendReplay(self):
        """ Phát lại video hiện tại. """
        self.switch_media(self.fileName)

    # =========================================================================
    # SECTION 3: RTSP PROTOCOL HANDLERS (SEND COMMANDS)
    # ========================================================================
    
    # Hàm gửi lệnh SETUP
    def sendSetup(self):
        """ Gửi lệnh SETUP. """
        if self.state == self.INIT:
            self.rtspSeq += 1
            request = f"SETUP {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nTransport: RTP/UDP; client_port={self.rtpPort}\r\n\r\n"
            self.requestSent = self.SETUP
            self.sendRtspRequest(request)

    # Hàm gửi lệnh PLAY
    def sendPlay(self):
        """ Gửi lệnh PLAY. """
        if self.state == self.READY:
            self.rtspSeq += 1
            request = f"PLAY {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nSession: {self.sessionId}\r\n\r\n"
            self.requestSent = self.PLAY
            self.sendRtspRequest(request)

    # Hàm gửi lệnh PAUSE
    def sendPause(self):
        """ Gửi lệnh PAUSE. """
        if self.state == self.PLAYING:
            self.rtspSeq += 1
            request = f"PAUSE {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nSession: {self.sessionId}\r\n\r\n"
            self.requestSent = self.PAUSE
            self.sendRtspRequest(request)

    # Hàm gửi lệnh TEARDOWN
    def sendTeardown(self):
        """ Gửi lệnh TEARDOWN. """
        self.rtspSeq += 1
        request = f"TEARDOWN {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nSession: {self.sessionId}\r\n\r\n"
        self.requestSent = self.TEARDOWN
        self.sendRtspRequest(request)

    # Hàm gửi yêu cầu RTSP chung
    def sendRtspRequest(self, request):
        """ Hàm chung để gửi gói tin RTSP qua socket TCP. """
        if self.rtspSocket:
            try:
                self.rtspSocket.send(request.encode())
                
                if self.verbose:
                    self.log(request.strip(), "CLIENT")
                    
                threading.Thread(target=self.recvRtspReply).start()
            except Exception as e:
                self.log(f"Send Error: {e}", "ERROR")

    # =========================================================================
    # SECTION 4: RTSP RESPONSE HANDLERS (RECEIVE & PARSE)
    # =========================================================================
    
    # Hàm nhận phản hồi RTSP
    def recvRtspReply(self):
        """ Nhận phản hồi từ Server. """
        try:
            reply = self.rtspSocket.recv(1024)
            if reply:
                self.parseRtspReply(reply.decode("utf-8"))
        except:
            pass
    
    # Hàm phân tích phản hồi RTSP
    def parseRtspReply(self, data):
        """ Phân tích phản hồi và chuyển đổi trạng thái. """
        lines = data.split('\n')
        status_line = lines[0].strip()
        
        if self.verbose:
            self.log(data.strip(), "SERVER") 
        
        try:
            seqNum = int(lines[1].split(' ')[1])
        except:
            return

        # Lấy Session ID
        for line in lines:
            if "Session" in line:
                self.sessionId = int(line.split(' ')[1])
        
        if self.sessionId == 0: return
        
        # Xử lý chuyển đổi trạng thái (State Machine)
        if self.sessionId != 0:
            if self.requestSent == self.SETUP:
                self.state = self.READY
                self.openRtpPort()
            elif self.requestSent == self.PLAY:
                self.state = self.PLAYING
                self.playEvent = threading.Event()
                self.playEvent.clear()
                threading.Thread(target=self.listenRtp).start()
            elif self.requestSent == self.PAUSE:
                self.state = self.READY
                self.playEvent.set()
            elif self.requestSent == self.TEARDOWN:
                self.state = self.INIT
                self.playEvent.set()
                self.teardownAcked = 1
                try: self.rtspSocket.close() 
                except: pass

    # Hàm mở cổng RTP (UDP)
    def openRtpPort(self):
        """ Mở cổng UDP để nhận RTP và thiết lập socket. """
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Cho phép dùng lại cổng ngay lập tức (Chống lỗi 'Address already in use')
        self.rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Tăng kích thước bộ đệm nhận tin lên 2MB (Để hứng gói tin HD tốc độ cao)
        self.rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
        
        self.rtpSocket.settimeout(0.5)
        try:
            self.rtpSocket.bind(("", self.rtpPort))
            if self.verbose:
                self.log(f"RTP Port {self.rtpPort} Open", "SYSTEM")
        except Exception as e:
            self.log(f"Unable to bind RTP Port {self.rtpPort}: {e}", "ERROR")

    # Hàm lắng nghe RTP
    def listenRtp(self):
        """
        VÒNG LẶP CHÍNH: Nhận gói RTP, ghép mảnh, tính toán Loss/Stats.
        """
        current_frame_buffer = bytearray()
        packet_count = 0 
        total_frame_count = 0
        
        # Biến tính toán Packet Loss
        last_seq_num = -1      
        total_lost = 0         
        total_received = 0     
        current_loss_rate = 0.0 
        
        while True:
            if self.playEvent.is_set(): 
                break
                
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    
                    # 1. Lấy thông tin gói
                    curr_seq = rtpPacket.seqNum()
                    payload = rtpPacket.getPayload()
                    
                    current_frame_buffer += payload
                    packet_count += 1
                    total_received += 1
                    
                    # 2. Thuật toán tính Loss (Gap Detection)
                    if last_seq_num != -1:
                        # Tính khoảng cách giữa gói hiện tại và gói trước
                        diff = curr_seq - last_seq_num
                        
                        # Xử lý trường hợp số thứ tự quay vòng (0 -> 65535)
                        if diff < 0: 
                            diff += 65536
                            
                        # Nếu khoảng cách > 1, tức là có gói bị rơi ở giữa
                        if diff > 1:
                            lost = diff - 1
                            total_lost += lost
                            # print(f"[LOSS] Detected {lost} missing packets!") # Uncomment để debug
                    
                    # Cập nhật số thứ tự cho vòng sau
                    last_seq_num = curr_seq
                    
                    # 3. Kiểm tra Marker Bit (Kết thúc Frame)
                    if rtpPacket.header[1] >> 7 == 1:
                        if len(current_frame_buffer) > 0:
                            total_frame_count += 1
                            
                            # Tính toán % Loss
                            if (total_received + total_lost) > 0:
                                current_loss_rate = (total_lost / (total_received + total_lost)) * 100
                            
                            # In log thống kê (Sampling mỗi 50 frame)
                            if total_frame_count % 50 == 0:
                                sz = len(current_frame_buffer)
                                msg = f"📊 STREAM_MONITOR: Frame #{total_frame_count} | Size: {sz}b | Frag: {packet_count} | Loss: {current_loss_rate:.1f}%"
                                self.log(msg, "SYSTEM")
                            
                            # Gửi TUPLE (Data, Pkts, Loss) sang Buffer
                            frame_tuple = (current_frame_buffer[:], packet_count, current_loss_rate)
                            self.jitter_buffer.put(frame_tuple)
                        
                        # Reset cho frame tiếp theo
                        current_frame_buffer = bytearray()
                        packet_count = 0
                        
                        
            except socket.timeout:
                continue
            except Exception as e:
                pass