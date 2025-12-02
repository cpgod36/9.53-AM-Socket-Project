from random import randint
import sys, traceback, threading, socket, time, os

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
# -------------------------------------------

class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2
    
    clientInfo = {}
    
    def __init__(self, clientInfo):
        self.clientInfo = clientInfo
        # Set timeout to None to ensure blocking mode or handle it properly
        if self.clientInfo['rtspSocket'][0]:
            self.clientInfo['rtspSocket'][0].settimeout(0.5)
        
    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()
    
    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
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
                # Nếu lỗi là 'event' (KeyError) do đóng ngắt quãng thì bỏ qua
                if str(e) == "'event'":
                    break
                print(f"Error receiving data: {e}")
                break
            
    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        lines = data.split('\n')
        line1 = lines[0].split(' ')
        requestType = line1[0]
        filename_req = line1[1] 
        
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

        # Process SETUP request
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
        
        # Process PLAY request      
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING
                
                # Tạo socket UDP mới
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
                self.replyRtsp(self.OK_200, seq)
                
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
                self.clientInfo['worker'].start()
        
        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY
                self.clientInfo['event'].set()
                self.replyRtsp(self.OK_200, seq)
        
        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")
            self.state = self.INIT 
            self.clientInfo['event'].set()
            self.replyRtsp(self.OK_200, seq)
            
            if 'rtpSocket' in self.clientInfo:
                self.clientInfo['rtpSocket'].close()
            if 'videoStream' in self.clientInfo:
                self.clientInfo['videoStream'].close() 
            
    def sendRtp(self):
        """Send RTP packets over UDP with Fragmentation logic."""
        currentSeqNum = 0 
        
        while True:
            # Time Drift Correction
            self.clientInfo['event'].wait(0.05) 
            
            if self.clientInfo['event'].is_set(): 
                break 
                
            data = self.clientInfo['videoStream'].nextFrame()
            
            if data: 
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    
                    # --- [Role B] Logic Phân mảnh (Fragmentation) ---
                    MAX_RTP_PAYLOAD = 1400 
                    datalen = len(data)
                    currentTimestamp = int(time.time()) 
                    
                    currPos = 0
                    while currPos < datalen:
                        chunkSize = min(MAX_RTP_PAYLOAD, datalen - currPos)
                        chunk = data[currPos : currPos + chunkSize]
                        currPos += chunkSize
                        
                        marker = 1 if currPos >= datalen else 0
                        
                        self.clientInfo['rtpSocket'].sendto(
                            self.makeRtp(chunk, currentSeqNum, marker, currentTimestamp),
                            (address, port)
                        )
                        currentSeqNum += 1
                    
                    if frameNumber % 50 == 0:
                        print(f"Sent frame {frameNumber}, Total size: {datalen} bytes")

                except Exception as e:
                    print(f"Connection Error: {e}")
            else:
                print("End of video stream.")
                self.clientInfo['event'].set()
                break

    def makeRtp(self, payload, seqNum, marker, timestamp):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        pt = 26 # MJPEG type
        ssrc = 0 
        
        rtpPacket = RtpPacket()
        rtpPacket.encode(version, padding, extension, cc, seqNum, marker, pt, ssrc, payload, timestamp)
        
        return rtpPacket.getPacket()
        
    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            reply = f'RTSP/1.0 200 OK\r\nCSeq: {seq}\r\nSession: {self.clientInfo["session"]}\r\n\r\n'
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())
        
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
            print("500 CONNECTION ERROR")