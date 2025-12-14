import os

class VideoStream:
    """
    Video Streamer Đa Năng (Universal Video Streamer).
    Hỗ trợ 2 chế độ:
    1. Proprietary Mode: Header độ dài (5 hoặc 6 bytes) - Dùng cho file convert.
    2. Standard Mode: Quét Marker JPEG (\xff\xd8 ... \xff\xd9) - Dùng cho file tải trên mạng.
    """
    
    def __init__(self, filename):
        self.filename = filename
        self.frameNum = 0
        self.mode = "UNKNOWN"
        self.header_size = 5
        
        try:
            self.file = open(filename, 'rb')
            self._detect_file_mode()
        except FileNotFoundError:
            print(f"ERROR: File {filename} not found.")
            raise IOError
        except Exception as e:
            print(f"ERROR: Could not open file: {e}")
            raise IOError

    def _detect_file_mode(self):
        """
        Logic phát hiện chế độ cực kỳ nghiêm ngặt.
        """
        try:
            pos = self.file.tell()
            chunk = self.file.read(5)
            self.file.seek(pos)      
            
            if not chunk: return

            try:
                chunk_str = chunk.decode('ascii')
                if chunk_str.isdigit():
                    self.mode = "PROPRIETARY"
                    self._detect_header_size()
                    return
            except:
                pass 
            
            self.mode = "STANDARD"
                
        except Exception as e:
            print(f"Error detecting mode: {e}")
            self.mode = "STANDARD" 

    def _detect_header_size(self):
        """Logic dò Header 5/6 số"""
        try:
            pos = self.file.tell()
            self.file.read(5)
            byte_6 = self.file.read(1)
            self.file.seek(pos)
            
            if byte_6 and byte_6.isdigit():
                self.header_size = 6
            else:
                self.header_size = 5
        except:
            self.header_size = 5

    def nextFrame(self):
        """Điều phối việc đọc frame."""
        if self.mode == "PROPRIETARY":
            return self._read_proprietary_frame()
        else:
            return self._read_standard_frame()

    def _read_proprietary_frame(self):
        try:
            data = self.file.read(self.header_size)
            if len(data) < self.header_size: return None
            
            framelength = int(data)
            data = self.file.read(framelength)
            self.frameNum += 1
            return data
        except ValueError:
            self.mode = "STANDARD"
            self.file.seek(-len(data), 1) 
            return self._read_standard_frame()

    def _read_standard_frame(self):
        data = bytearray()
        found_soi = False
        
        # 1. Tìm SOI (FF D8)
        while not found_soi:
            byte = self.file.read(1)
            if not byte: return None # EOF
            
            if byte == b'\xff':
                next_byte = self.file.read(1)
                if next_byte == b'\xd8':
                    data.extend(b'\xff\xd8')
                    found_soi = True
                elif next_byte == b'\xff':
                    self.file.seek(-1, 1)
        
        while True:
            byte = self.file.read(1)
            if not byte: return None
            
            data.extend(byte)
            
            if byte == b'\xff':
                next_byte = self.file.read(1)
                data.extend(next_byte)
                
                if next_byte == b'\xd9':
                    self.frameNum += 1
                    return bytes(data)
                
                if next_byte == b'\xd8':
                    self.file.seek(-2, 1)
                    self.frameNum += 1
                    return bytes(data[:-2])
    
    def frameNbr(self):
        return self.frameNum
    
    def close(self):
        if self.file: self.file.close()

    def reset(self):
        if self.file:
            self.file.seek(0)
            self.frameNum = 0