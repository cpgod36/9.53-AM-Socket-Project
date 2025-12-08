from random import randint
import sys, traceback, threading, socket, time, os

# --- IMPORT MODULES ---
try:
    from src.common.video_stream import VideoStream
    from src.common.rtp_packet import RtpPacket
except ImportError:
    try:
        from common.video_stream import VideoStream
        from common.rtp_packet import RtpPacket
    except ImportError:
        import sys, os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
        from src.common.video_stream import VideoStream
        from src.common.rtp_packet import RtpPacket

class ServerWorker:
    """
    Xử lý logic phía Server:
    1. Nhận lệnh RTSP (SETUP, PLAY, PAUSE, TEARDOWN).
    2. Đọc video từ file.
    3. Đóng gói RTP (có phân mảnh).
    4. Gửi dữ liệu qua UDP.
    """
    
    # RTSP Methods
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    
    # Server States
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    # Status Codes
    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2
    
    clientInfo = {}
    
    def __init__(self, clientInfo):
        self.clientInfo = clientInfo
        
        # Set timeout cho socket RTSP để không bị treo nếu client mất kết nối
        if self.clientInfo['rtspSocket'][0]:
            self.clientInfo['rtspSocket'][0].settimeout(0.5)
            
    def run(self):
        """ Bắt đầu luồng nhận lệnh RTSP. """
        threading.Thread(target=self.recvRtspRequest).start()
        
    # =========================================================================
    # RTSP CONTROL (NHẬN LỆNH)
    # =========================================================================
        
    def recvRtspRequest(self):
        """ Vòng lặp lắng nghe lệnh từ Client (TCP). """
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:            
            try:
                data = connSocket.recv(2048)
                if data:
                    print("-" * 40)
                    print("Data received:\n" + data.decode("utf-8"))
                    self.processRtspRequest(data.decode("utf-8"))
            except socket.timeout:
                continue
            except Exception as e:
                # Nếu client đóng kết nối (KeyError 'event' hoặc ConnectionReset) thì dừng vòng lặp
                if str(e) == "'event'":
                    break
                print(f"Error receiving data: {e}")
                break
    
    def processRtspRequest(self, data):
        """ Phân tích và xử lý lệnh RTSP. """
        lines = data.split('\n')
        line1 = lines[0].split(' ')
        requestType = line1[0]
        filename_req = line1[1] 
        
        # Đường dẫn tới thư mục video
        VIDEO_DIR = "assets/video" 
        filename = os.path.join(VIDEO_DIR, filename_req)
        
        seq = 0
        for line in lines:
            if "CSeq:" in line:
                try:
                    seq = line.split(' ')[1]
                except:
                    pass
            if "Session:" in line:
                pass

        # --- SETUP ---
        if requestType == self.SETUP:
            if self.state == self.INIT:
                print("processing SETUP\n")
                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    print(f"File not found: {filename}")
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq)
                    return 
                
                self.clientInfo['session'] = randint(100000, 999999)
                
                # Lấy RTP Port từ Client
                self.clientInfo['rtpPort'] = 0
                for line in lines:
                    if "client_port" in line:
                        try:
                            parts = line.split(';')
                            for part in parts:
                                if "client_port" in part:
                                    self.clientInfo['rtpPort'] = part.split('=')[1].strip()
                        except:
                            print("Error parsing port")

                self.replyRtsp(self.OK_200, seq)
        
        # --- PLAY ---      
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING
                
                # Tạo socket UDP mới để bắn dữ liệu
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                self.replyRtsp(self.OK_200, seq)
                
                # Bắt đầu luồng gửi RTP
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
                self.clientInfo['worker'].start()
        
        # --- PAUSE ---
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY
                self.clientInfo['event'].set() # Dừng luồng gửi
                self.replyRtsp(self.OK_200, seq)
        
        # --- TEARDOWN ---
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")
            self.state = self.INIT 
            self.clientInfo['event'].set() # Dừng luồng gửi
            self.replyRtsp(self.OK_200, seq)
            
            # Dọn dẹp tài nguyên
            if 'rtpSocket' in self.clientInfo:
                self.clientInfo['rtpSocket'].close()
            if 'videoStream' in self.clientInfo:
                self.clientInfo['videoStream'].close() 
     
    def replyRtsp(self, code, seq):
        """ Gửi phản hồi RTSP về Client. """
        if code == self.OK_200:
            reply = f'RTSP/1.0 200 OK\r\nCSeq: {seq}\r\nSession: {self.clientInfo["session"]}\r\n\r\n'
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())
        
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
            print("500 CONNECTION ERROR")
     
    # =========================================================================
    # RTP STREAMING (GỬI DỮ LIỆU)
    # =========================================================================
     
    def sendRtp(self):
        """
        VÒNG LẶP GỬI DỮ LIỆU (Streaming Loop).
        Hỗ trợ Phân mảnh (Fragmentation) cho Video HD.
        """
        currentSeqNum = 0 
        
        while True:
            # [CẤU HÌNH TỐI ƯU] Tốc độ 30 FPS (0.033s)
            # Giúp Server gửi ổn định, không làm ngộp Client
            self.clientInfo['event'].wait(0.033)  # ~30 FPS
            
            if self.clientInfo['event'].is_set(): 
                break 
                
            data = self.clientInfo['videoStream'].nextFrame()
            
            if data: 
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    
                    # --- Logic Phân mảnh (Fragmentation) ---
                    MAX_RTP_PAYLOAD = 1400 
                    datalen = len(data)
                    currentTimestamp = int(time.time()) 
                    
                    currPos = 0 
                    while currPos < datalen:
                        # Tính toán kích thước mảnh
                        chunkSize = min(MAX_RTP_PAYLOAD, datalen - currPos)
                        chunk = data[currPos : currPos + chunkSize]
                        currPos += chunkSize
                        
                        # Marker Bit: 1 nếu là mảnh cuối, 0 nếu còn nữa
                        marker = 1 if currPos >= datalen else 0
                        
                        # Gửi gói
                        self.clientInfo['rtpSocket'].sendto(
                            self.makeRtp(chunk, currentSeqNum, marker, currentTimestamp),
                            (address, port)
                        )
                        currentSeqNum += 1
                        
                    # In log mỗi 100 frame
                    if frameNumber % 100 == 0:
                        print(f"Sent frame {frameNumber}, Total size: {datalen} bytes")

                except Exception as e:
                    print(f"Connection Error: {e}")
            else:
                print("End of video stream.")
                self.clientInfo['event'].set()
                break
    
    def makeRtp(self, payload, seqNum, marker, timestamp):
        """ Đóng gói dữ liệu vào RTP Packet. """
        version = 2
        padding = 0
        extension = 0
        cc = 0
        pt = 26 # MJPEG type
        ssrc = 0 
        
        rtpPacket = RtpPacket()
        rtpPacket.encode(version, padding, extension, cc, seqNum, marker, pt, ssrc, payload, timestamp)
        
        return rtpPacket.getPacket()
                        
    
    
    
            
    
            
    

    
        
    