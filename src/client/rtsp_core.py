import socket
import threading
import sys
import os
import traceback
import time

# Import RtpPacket
try:
    from src.common.rtp_packet import RtpPacket
except ImportError:
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    try:
        from src.common.rtp_packet import RtpPacket
    except ImportError:
        print("[CORE LỖI] Không tìm thấy src/common/rtp_packet.py")
        sys.exit(1)

class RtspClientCore:
    """
    Class này xử lý toàn bộ logic mạng: RTSP Protocol & RTP Receiving.
    Nó KHÔNG chứa code giao diện (Tkinter/PyQt).
    Nó giao tiếp với GUI thông qua các hàm callback.
    """
    
    # RTSP States
    INIT = 0
    READY = 1
    PLAYING = 2
    
    # Request Types
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    def __init__(self, server_addr, server_port, rtp_port, filename, on_frame_decoded_callback):
        """
        :param on_frame_decoded_callback: Hàm của GUI sẽ được gọi khi nhận được ảnh mới. 
                                          Dạng hàm: func(image_bytes)
        """
        self.serverAddr = server_addr
        self.serverPort = int(server_port)
        self.rtpPort = int(rtp_port)
        self.fileName = filename
        
        # Callbacks
        self.on_frame_decoded = on_frame_decoded_callback
        
        # RTSP variables
        self.state = self.INIT
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.rtspSocket = None
        
        # RTP variables
        self.rtpSocket = None
        self.frameNbr = 0
        
        # Threading control
        self.playEvent = None
    
    def connect_server(self):
        """Kết nối TCP tới Server."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print(f"[CORE] Connected to Server {self.serverAddr}:{self.serverPort}")
            return True
        except:
            print(f"[CORE] Connection Failed to {self.serverAddr}")
            return False

    def send_setup(self):
        if self.state == self.INIT:
            # Khởi tạo thread lắng nghe phản hồi RTSP
            threading.Thread(target=self.recv_rtsp_reply).start()
            self.rtspSeq += 1
            
            request = f"SETUP {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nTransport: RTP/UDP; client_port={self.rtpPort}\r\n\r\n"
            self.requestSent = self.SETUP
            self._send_request(request)

    def send_play(self):
        if self.state == self.READY:
            self.rtspSeq += 1
            request = f"PLAY {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nSession: {self.sessionId}\r\n\r\n"
            self.requestSent = self.PLAY
            
            # Khởi tạo thread lắng nghe RTP (UDP)
            print("[CORE] Starting RTP Listener thread...")
            self.playEvent = threading.Event()
            self.playEvent.clear()
            threading.Thread(target=self.listen_rtp).start()
            
            self._send_request(request)

    def send_pause(self):
        if self.state == self.PLAYING:
            self.rtspSeq += 1
            request = f"PAUSE {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nSession: {self.sessionId}\r\n\r\n"
            self.requestSent = self.PAUSE
            self._send_request(request)

    def send_teardown(self):
        self.rtspSeq += 1
        request = f"TEARDOWN {self.fileName} RTSP/1.0\r\nCSeq: {self.rtspSeq}\r\nSession: {self.sessionId}\r\n\r\n"
        self.requestSent = self.TEARDOWN
        self._send_request(request)

    def _send_request(self, request_str):
        if self.rtspSocket:
            self.rtspSocket.send(request_str.encode())
            print(f'\n[CORE] Data sent:\n{request_str}')

    def recv_rtsp_reply(self):
        """Lắng nghe phản hồi RTSP từ Server (Chạy trên thread riêng)."""
        while True:
            try:
                reply = self.rtspSocket.recv(1024)
                if reply:
                    self.parse_rtsp_reply(reply.decode("utf-8"))
                
                if self.requestSent == self.TEARDOWN:
                    self.rtspSocket.shutdown(socket.SHUT_RDWR)
                    self.rtspSocket.close()
                    break
            except:
                break
    
    def parse_rtsp_reply(self, data):
        print("[CORE] Server Reply:\n" + data)
        lines = data.split('\n')
        try:
            seqNum = int(lines[1].split(' ')[1])
        except:
            return

        if seqNum == self.rtspSeq:
            try:
                session = int(lines[2].split(' ')[1])
                if self.sessionId == 0:
                    self.sessionId = session
                
                if self.sessionId == session:
                    if int(lines[0].split(' ')[1]) == 200:
                        if self.requestSent == self.SETUP:
                            self.state = self.READY
                            self.open_rtp_port()
                        elif self.requestSent == self.PLAY:
                            self.state = self.PLAYING
                        elif self.requestSent == self.PAUSE:
                            self.state = self.READY
                            self.playEvent.set() # Dừng vòng lặp RTP
                        elif self.requestSent == self.TEARDOWN:
                            self.state = self.INIT
                            self.teardownAcked = 1
            except Exception as e:
                print(f"[CORE] Error parsing Session ID: {e}")

    def open_rtp_port(self):
        """Mở cổng UDP để nhận video."""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)
        try:
            self.state = self.READY
            self.rtpSocket.bind(('', self.rtpPort))
            print(f"[CORE] Bind RTP Port {self.rtpPort} Success")
        except:
            print(f"[CORE] Unable to bind PORT={self.rtpPort}")

    def listen_rtp(self):
        """
        Lắng nghe gói tin RTP.
        Đây là nơi người bạn kia sẽ cần sửa để thêm Buffer/Cache/Fragmentation.
        """
        while True:
            try:
                if self.rtpSocket:
                    data, addr = self.rtpSocket.recvfrom(20480)
                    if data:
                        rtpPacket = RtpPacket()
                        rtpPacket.decode(data)
                        
                        currFrameNbr = rtpPacket.seqNum()
                        
                        # Logic đơn giản: Frame mới hơn thì lấy (vứt gói cũ)
                        if currFrameNbr > self.frameNbr:
                            self.frameNbr = currFrameNbr
                            
                            # GỌI CALLBACK ĐỂ GUI CẬP NHẬT
                            if self.on_frame_decoded:
                                self.on_frame_decoded(rtpPacket.getPayload())
                                
            except socket.timeout:
                if self.playEvent.is_set():
                    break
            except Exception as e:
                if self.playEvent.is_set():
                    break
                if self.teardownAcked == 1:
                    if self.rtpSocket:
                        self.rtpSocket.shutdown(socket.SHUT_RDWR)
                        self.rtpSocket.close()
                    break