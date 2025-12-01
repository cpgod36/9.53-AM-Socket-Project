# RTSP/RTP Video Streaming Application

Đồ án Lập trình Socket - Xây dựng ứng dụng Streaming Video sử dụng giao thức RTSP (Real-Time Streaming Protocol) để điều khiển và RTP (Real-time Transport Protocol) để truyền dữ liệu.

## 👥 Thành viên nhóm
1. 24120026 - Phan Chí Cao (Trưởng nhóm, GUI Developer, Architecture)
2. 24120110 - Nguyễn Hoàng Nhật (Core Logic, HD Streaming, Buffering)

## 🚀 Tính năng

### 1. Cơ bản (Basic Requirements)
- [x] Mô hình Client-Server.
- [x] Giao thức RTSP: SETUP, PLAY, PAUSE, TEARDOWN.
- [x] Đóng gói packet RTP (Header bit-manipulation).
- [x] Giao diện điều khiển cơ bản (Tkinter).

### 2. Nâng cao (Advanced Requirements)
- [ ] **HD Video Streaming:** Hỗ trợ phân mảnh (Fragmentation) cho video chất lượng cao (720p/1080p).
- [ ] **Client-Side Buffering:** Cơ chế bộ đệm (Jitter Buffer) giúp video mượt mà khi mạng lag.
- [ ] **Modern UI:** Giao diện hiện đại (PyQt/Figma Design) tách biệt với Logic.

---

## 🛠 Cài đặt môi trường

Dự án yêu cầu Python 3.8+.

1. **Clone dự án:**
   ```bash
   git clone https://github.com/cpgod36/9.53-AM-Socket-Project.git
   cd 9.53_Socket_Project