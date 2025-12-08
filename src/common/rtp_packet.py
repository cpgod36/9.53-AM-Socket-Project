import sys
from time import time

# Kích thước Header RTP chuẩn là 12 bytes
HEADER_SIZE = 12

class RtpPacket:    
    """
    Xử lý gói tin RTP (Real-time Transport Protocol).
    Hỗ trợ Encode (đóng gói) và Decode (giải mã).
    """
    def __init__(self):
        self.header = bytearray(HEADER_SIZE)
        self.payload = bytearray()
        
    # =========================================================================
    # ENCODING (ĐÓNG GÓI DỮ LIỆU)
    # =========================================================================
        
    def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload, timestamp=None):
        """
        Tạo gói tin RTP từ các thông số đầu vào.
        
        :param version: RTP Version (thường là 2)
        :param padding: Padding bit (0 hoặc 1)
        :param extension: Extension bit
        :param cc: CSRC Count
        :param seqnum: Số thứ tự gói tin (Frame Index hoặc Fragment Index)
        :param marker: Bit đánh dấu (1 = Kết thúc frame, 0 = Một phần của frame)
        :param pt: Payload Type (MJPEG = 26)
        :param ssrc: Synchronization Source Identifier
        :param payload: Dữ liệu ảnh (hoặc mảnh của ảnh)
        :param timestamp: Thời gian gửi (nếu None sẽ lấy thời gian thực)
        """
        
        # Tự động lấy thời gian nếu không truyền vào
        if timestamp is None:
            timestamp = int(time())
        
        self.header = bytearray(HEADER_SIZE)
        
        # --- Byte 0: V (2 bits) | P (1 bit) | X (1 bit) | CC (4 bits) ---
        self.header[0] = (version << 6) | (padding << 5) | (extension << 4) | cc
        
        # --- Byte 1: M (1 bit) | PT (7 bits) ---
        self.header[1] = (marker << 7) | pt
        
        # --- Byte 2-3: Sequence Number (16 bits) ---
        self.header[2] = (seqnum >> 8) & 0xFF
        self.header[3] = seqnum & 0xFF 
        
        # --- Byte 4-7: Timestamp (32 bits) ---
        self.header[4] = (timestamp >> 24) & 0xFF
        self.header[5] = (timestamp >> 16) & 0xFF
        self.header[6] = (timestamp >> 8) & 0xFF
        self.header[7] = timestamp & 0xFF
        
        # --- Byte 8-11: SSRC (32 bits) ---
        self.header[8] = (ssrc >> 24) & 0xFF
        self.header[9] = (ssrc >> 16) & 0xFF
        self.header[10] = (ssrc >> 8) & 0xFF
        self.header[11] = ssrc & 0xFF
        
        # Gán payload
        self.payload = payload
        
    # =========================================================================
    # DECODING (GIẢI MÃ DỮ LIỆU)
    # =========================================================================
    
    def decode(self, byteStream):
        """ Tách Header và Payload từ dòng dữ liệu nhận được. """
        if len(byteStream) < HEADER_SIZE:
            raise ValueError("Data stream too short to be RTP packet")

        self.header = bytearray(byteStream[:HEADER_SIZE])
        self.payload = byteStream[HEADER_SIZE:]
    
    # =========================================================================
    # GETTERS (LẤY THÔNG TIN HEADER)
    # =========================================================================
    
    def version(self):
        """ Lấy RTP Version. """
        return int(self.header[0] >> 6)
    
    def seqNum(self):
        """ Lấy Sequence Number (Dùng để tính Packet Loss). """
        seqNum = (self.header[2] << 8) | self.header[3] 
        return int(seqNum)
    
    def timestamp(self):
        """ Lấy Timestamp. """
        timestamp = (self.header[4] << 24) | (self.header[5] << 16) | (self.header[6] << 8) | self.header[7]
        return int(timestamp)
    
    def payloadType(self):
        """ Lấy Payload Type. """
        pt = self.header[1] & 127
        return int(pt)
    
    def getPayload(self):
        """ Lấy dữ liệu ảnh. """
        return self.payload
        
    def getPacket(self):
        """ Lấy toàn bộ gói RTP (Header + Payload) để gửi đi. """
        return self.header + self.payload