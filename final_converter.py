import cv2
from PIL import Image
import io
import sys
import os

def convert_to_hd_optimized(input_path, output_path, target_fps=30, quality=90):
    if not os.path.exists(input_path):
        print(f"[Lỗi] Không tìm thấy: {input_path}")
        return

    cap = cv2.VideoCapture(input_path)
    
    # Lấy thông số gốc
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"[*] Input: {input_path} | FPS gốc: {original_fps:.2f}")
    print(f"[*] Target: {output_path} | FPS đích: {target_fps} | Quality: {quality}")

    # Tính toán bước nhảy frame (Frame Skipping)
    # Nếu video gốc 60fps, ta chỉ lấy mỗi frame thứ 2 (step=2) để về 30fps
    step = max(1, round(original_fps / target_fps))
    
    frame_idx = 0
    saved_count = 0
    
    with open(output_path, 'wb') as f:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Chỉ xử lý nếu frame này nằm trong bước nhảy
            if frame_idx % step == 0:
                # 1. Convert sang RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
                # 2. Resize nhẹ nếu video quá lớn (Optional - giúp giảm lag mạng)
                # Nếu video > 1080p, ép về 1280x720 để mạng UDP chịu nổi
                if pil_img.width > 1280:
                    ratio = 1280 / pil_img.width
                    new_height = int(pil_img.height * ratio)
                    pil_img = pil_img.resize((1280, new_height), Image.Resampling.LANCZOS)

                # 3. Nén JPEG High Quality
                buffer = io.BytesIO()
                pil_img.save(buffer, format="JPEG", quality=quality) # <--- TĂNG ĐỘ NÉT TẠI ĐÂY
                jpeg_data = buffer.getvalue()
                
                # 4. Ghi Header 6 số
                size = len(jpeg_data)
                header = str(size).zfill(6).encode()
                
                f.write(header)
                f.write(jpeg_data)
                saved_count += 1
                
                if saved_count % 50 == 0:
                    print(f"   -> Processed: {frame_idx}/{total_frames} | Saved: {saved_count} frames")

            frame_idx += 1

    cap.release()
    print(f"\n[XONG] Video đã được tối ưu hóa!")
    print(f"Lưu ý: Bạn phải chỉnh Server gửi với tốc độ {target_fps} FPS (sleep {1.0/target_fps:.3f})")

if __name__ == "__main__":
    INPUT = "input.mp4" 
    OUTPUT = "assets/video/movie_hd.Mjpeg"
    
    # Convert về 30 FPS, Chất lượng 90 (Rất nét)
    convert_to_hd_optimized(INPUT, OUTPUT, target_fps=30, quality=90)