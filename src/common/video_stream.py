import os

class VideoStream:
    """
    Đọc dữ liệu từ file MJPEG Proprietary (Định dạng riêng của bài Lab).
    Hỗ trợ tự động phát hiện Header Size (5 bytes hoặc 6 bytes) để chạy cả video SD và HD.
    """
    def __init__(self, filename):
        self.filename = filename
        self.frameNum = 0
        self.header_size = 5 # Mặc định là 5
        
        try:
            self.file = open(filename, 'rb')
            # Tự động dò tìm xem file này là HD hay SD
            self._detect_header_size() 
        except FileNotFoundError:
            print(f"ERROR: File {filename} not found.")
            raise IOError
        except Exception as e:
            print(f"ERROR: Could not open file: {e}")
            raise IOError

    def _detect_header_size(self):
        """
        Thuật toán thông minh: Kiểm tra byte thứ 6.
        - Nếu byte 6 là số -> Header 6 số (Video HD > 100KB/frame).
        - Nếu byte 6 là rác/ảnh -> Header 5 số (Video SD).
        """
        try:
            # Lưu vị trí con trỏ hiện tại
            pos = self.file.tell()
            
            # Đọc thử 6 bytes
            chunk = self.file.read(5)
            byte_6 = self.file.read(1)
            
            # Quay lại từ đầu để không ảnh hưởng luồng đọc chính
            self.file.seek(pos)
            
            # Kiểm tra byte thứ 6 có phải là ký tự số ASCII không?
            if byte_6 and byte_6.isdigit():
                print(f"[*] Detected HD Video (6-byte header): {self.filename}")
                self.header_size = 6
            else:
                print(f"[*] Detected Standard Video (5-byte header): {self.filename}")
                self.header_size = 5
                
        except Exception as e:
            print(f"Warning: Could not detect header size, using default 5. {e}")
            self.header_size = 5

    def nextFrame(self):
        """
        Đọc frame tiếp theo từ file.
        Returns: Dữ liệu ảnh (bytes) hoặc None nếu hết file.
        """
        # 1. Đọc Header chứa độ dài frame (5 hoặc 6 bytes)
        data = self.file.read(self.header_size)
        
        if len(data) < self.header_size:
            return None 

        try:
            # 2. Parse độ dài (String -> Int)
            framelength = int(data)
        except ValueError:
            print("ERROR: Corrupted header or parsing error.")
            return None

        # 3. Đọc dữ liệu ảnh thật sự dựa trên độ dài
        data = self.file.read(framelength)
        
        self.frameNum += 1
        
        return data

    def frameNbr(self):
        """ Lấy số thứ tự frame hiện tại. """
        return self.frameNum
    
    def close(self):
        """ Đóng file. """
        if self.file:
            self.file.close()

    def reset(self):
        """ Tua lại từ đầu (Dùng cho tính năng Loop nếu cần). """
        if self.file:
            self.file.seek(0)
            self.frameNum = 0