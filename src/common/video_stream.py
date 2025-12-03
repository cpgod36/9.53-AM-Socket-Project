import os

class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.frameNum = 0
        self.header_size = 5 # Mặc định là 5
        try:
            self.file = open(filename, 'rb')
            self._detect_header_size() # Tự động dò tìm header
        except FileNotFoundError:
            print(f"ERROR: File {filename} not found.")
            raise IOError
        except Exception as e:
            print(f"ERROR: Could not open file: {e}")
            raise IOError

    def _detect_header_size(self):
        """Hàm thông minh: Kiểm tra xem file này dùng header 5 số hay 6 số"""
        try:
            # Lưu vị trí hiện tại
            pos = self.file.tell()
            
            # Đọc 5 byte đầu
            chunk = self.file.read(5)
            # Đọc thêm 1 byte nữa (byte thứ 6)
            byte_6 = self.file.read(1)
            
            # Quay lại từ đầu để lát nữa hàm nextFrame đọc lại cho đúng
            self.file.seek(pos)
            
            # Logic: Nếu byte thứ 6 cũng là ký tự số (ASCII 0-9) 
            # thì khả năng cao đây là header 6 số (HD)
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
        """Get next frame."""
        # Đọc header dựa trên kích thước đã dò tìm được
        data = self.file.read(self.header_size)
        
        if len(data) < self.header_size:
            return None # Hết file

        try:
            # Chuyển chuỗi số thành int
            framelength = int(data)
        except ValueError:
            print("ERROR: Corrupted header or parsing error.")
            return None

        # Đọc dữ liệu ảnh
        data = self.file.read(framelength)
        
        self.frameNum += 1
        
        return data

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
    
    def close(self):
        """Close the file handle manually."""
        if self.file:
            self.file.close()

    def reset(self):
        """Restart video from beginning"""
        if self.file:
            self.file.seek(0)
            self.frameNum = 0