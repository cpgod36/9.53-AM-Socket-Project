import queue

class JitterBuffer:
    """
    Bộ đệm khung hình (Jitter Buffer).
    Giúp ổn định luồng video khi mạng chập chờn hoặc gói tin đến không đều.
    """
    def __init__(self, max_size=300):
        # max_size: Số lượng frame tối đa lưu trong bộ đệm
        # Sử dụng Queue của Python để đảm bảo Thread-safe (An toàn đa luồng)
        self.buffer = queue.Queue(maxsize=max_size)

    def put(self, frame):
        """
        Thêm frame vào hàng đợi.
        (Được gọi bởi luồng mạng - Network Thread/Core)
        """
        if not self.buffer.full():
            self.buffer.put(frame)
        else:
            # Nếu bộ đệm đầy, xóa frame cũ nhất để nhường chỗ (Strategy: Drop Oldest)
            # Điều này giúp giảm độ trễ (latency) nếu mạng bị tắc nghẽn
            try:
                self.buffer.get_nowait()
                self.buffer.put(frame)
            except queue.Empty:
                pass

    def get(self):
        """
        Lấy frame ra để hiển thị.
        (Được gọi bởi luồng giao diện - UI Thread/Timer)
        """

        try:
            # Lấy frame ra, nếu không có thì trả về None (không chặn UI)
            return self.buffer.get_nowait()
        except queue.Empty:
            return None
    
    def qsize(self):
        """ Kiểm tra số lượng frame hiện có """
        return self.buffer.qsize()

    def clear(self):
        """ 
        Xóa sạch bộ đệm.
        Dùng khi Stop, Replay hoặc Switch Video để tránh hiện ảnh cũ. 
        """
        with self.buffer.mutex:
            self.buffer.queue.clear()