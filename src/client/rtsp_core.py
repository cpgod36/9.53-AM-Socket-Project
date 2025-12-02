import socket
import threading
import sys
import traceback
import os
import time

# Import class hỗ trợ từ common và buffer
try:
    from src.common.rtp_packet import RtpPacket
    from src.client.buffer import JitterBuffer
except ImportError:
    # Fallback cho trường hợp chạy trực tiếp để test
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
    from src.common.rtp_packet import RtpPacket
    from src.client.buffer import JitterBuffer

class RtspCore:
    # Các trạng thái RTSP
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT
    
    # Các hằng số thông điệp RTSP
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    
    def __init__(self, server_addr, server_port, rtp_port, file_name):
        self.serverAddr = server_addr
        self.serverPort = int(server_port)
        self.rtpPort = int(rtp_port)
        self.fileName = file_name
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.rtspSocket = None
        self.rtpSocket = None
        
        # Buffer lưu trữ frame hoàn chỉnh
        self.jitter_buffer = JitterBuffer()
        
        # Biến điều khiển luồng nhận RTP
        self.playEvent = threading.Event()
        
        # Kết nối đến Server ngay khi khởi tạo
        self.connectToServer()

    def connectToServer(self):
        """Khởi tạo kết nối TCP cho RTSP"""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print(f"Connected to RTSP Server at {self.serverAddr}:{self.serverPort}")
        except:
            print(f"Failed to connect to {self.serverAddr}")

    def sendSetup(self):
        """Gửi lệnh SETUP"""
        if self.state == self.INIT:
            self.rtspSeq += 1
            request = f"SETUP {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nTransport: RTP/UDP; client_port= {self.rtpPort}"
            self.requestSent = self.SETUP
            self.sendRtspRequest(request)

    def sendPlay(self):
        """Gửi lệnh PLAY"""
        if self.state == self.READY:
            self.rtspSeq += 1
            request = f"PLAY {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}"
            self.requestSent = self.PLAY
            self.sendRtspRequest(request)

    def sendPause(self):
        """Gửi lệnh PAUSE"""
        if self.state == self.PLAYING:
            self.rtspSeq += 1
            request = f"PAUSE {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}"
            self.requestSent = self.PAUSE
            self.sendRtspRequest(request)

    def sendTeardown(self):
        """Gửi lệnh TEARDOWN"""
        self.rtspSeq += 1
        request = f"TEARDOWN {self.fileName} RTSP/1.0\nCSeq: {self.rtspSeq}\nSession: {self.sessionId}"
        self.requestSent = self.TEARDOWN
        self.sendRtspRequest(request)

    def sendRtspRequest(self, request):
        """Gửi request và chờ phản hồi"""
        self.rtspSocket.send(request.encode())
        print(f"\nSent Request:\n{request}")
        
        # Nhận phản hồi ngay lập tức (Blocking đơn giản)
        threading.Thread(target=self.recvRtspReply).start()

    def recvRtspReply(self):
        """Nhận và xử lý phản hồi RTSP từ Server"""
        try:
            reply = self.rtspSocket.recv(1024)
            if reply:
                self.parseRtspReply(reply.decode("utf-8"))
        except:
            pass

    def parseRtspReply(self, data):
        """Phân tích phản hồi RTSP"""
        print(f"Server Reply:\n{data}")
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])
        
        # Lấy Session ID
        for line in lines:
            if "Session" in line:
                self.sessionId = int(line.split(' ')[1])
        
        if self.sessionId == 0: return # Lỗi chưa có session
        
        if self.sessionId != 0:
            if self.requestSent == self.SETUP:
                print("Updating state to READY")
                self.state = self.READY
                self.openRtpPort()
                
            elif self.requestSent == self.PLAY:
                print("Updating state to PLAYING")
                self.state = self.PLAYING
                self.playEvent = threading.Event()
                self.playEvent.clear()
                # Bắt đầu luồng nhận RTP
                threading.Thread(target=self.listenRtp).start()
                
            elif self.requestSent == self.PAUSE:
                print("Updating state to READY")
                self.state = self.READY
                self.playEvent.set() # Dừng luồng RTP
                
            elif self.requestSent == self.TEARDOWN:
                print("Updating state to INIT")
                self.state = self.INIT
                self.playEvent.set()
                self.teardownAcked = 1
                self.rtspSocket.close()

    def openRtpPort(self):
        """Mở cổng UDP để nhận RTP"""
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtpSocket.settimeout(0.5)
        try:
            self.rtpSocket.bind(("", self.rtpPort))
            print(f"RTP Port {self.rtpPort} is open.")
        except:
            print(f"Unable to bind to port {self.rtpPort}")

    # -----------------------------------------------------------
    # LOGIC GHÉP GÓI TIN (FRAGMENTATION REASSEMBLY)
    # -----------------------------------------------------------
    def listenRtp(self):
        """Lắng nghe và ghép các gói RTP thành frame ảnh"""
        current_frame_buffer = bytearray()
        
        while True:
            # Nếu user bấm Pause/Teardown thì dừng luồng này
            if self.playEvent.is_set(): 
                break
                
            try:
                data = self.rtpSocket.recv(2048) # Nhận gói tin UDP
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    
                    # 1. Lấy dữ liệu payload của gói này
                    payload = rtpPacket.getPayload()
                    
                    # 2. Ghép vào buffer tạm
                    current_frame_buffer += payload
                    
                    # 3. Kiểm tra Marker bit (Bit M trong header)
                    # Nếu M = 1 nghĩa là đây là mảnh cuối cùng của frame
                    if rtpPacket.header[1] >> 7 == 1: # Kiểm tra bit đầu tiên của byte thứ 2
                        
                        # Frame đã hoàn thiện -> Đẩy vào Jitter Buffer
                        # Clone buffer để tránh tham chiếu sai
                        if len(current_frame_buffer) > 0:
                            self.jitter_buffer.put(current_frame_buffer[:])
                        
                        # Reset buffer tạm để hứng frame tiếp theo
                        current_frame_buffer = bytearray()
                        
            except socket.timeout:
                # Không nhận được data trong 0.5s -> Có thể server chưa gửi hoặc lag
                continue
            except Exception as e:
                # print(f"RTP Error: {e}")
                pass