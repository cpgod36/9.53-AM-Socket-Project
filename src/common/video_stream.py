import os

class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.frameNum = 0
        try:
            self.file = open(filename, 'rb')
        except FileNotFoundError:
            print(f"ERROR: File {filename} not found.")
            raise IOError
        except Exception as e:
            print(f"ERROR: Could not open file: {e}")
            raise IOError

    def nextFrame(self):
        """Get next frame."""
        # Đọc 5 bytes đầu tiên chứa độ dài (length) của frame ảnh
        data = self.file.read(5)
        
        # Kiểm tra xem có đọc đủ 5 bytes không (Xử lý cuối file)
        if len(data) < 5:
            return None # Báo hiệu hết video

        try:
            # MJPEG format của bài lab lưu độ dài dưới dạng chuỗi số (VD: "01234")
            framelength = int(data)
        except ValueError:
            print("ERROR: Corrupted header or parsing error.")
            return None

        # Đọc dữ liệu ảnh thật sự dựa trên độ dài vừa lấy
        data = self.file.read(framelength)
        
        # Tăng số thứ tự frame
        self.frameNum += 1
        
        return data

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
    
    def close(self):
        """Close the file handle manually."""
        if self.file:
            self.file.close()
            print("Video stream file closed.")

    def reset(self):
        """(Optional) Restart video from beginning - Cho tính năng Loop"""
        if self.file:
            self.file.seek(0)
            self.frameNum = 0