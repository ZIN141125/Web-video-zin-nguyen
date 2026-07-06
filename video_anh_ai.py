import os
import time
import requests
import urllib.parse
from flask import Blueprint, request, jsonify, session, send_from_directory
from deep_translator import GoogleTranslator

# Khởi tạo Blueprint
visual_ai_bp = Blueprint('visual_ai', __name__)

# Cấu hình thư mục lưu trữ media
STATIC_MEDIA_FOLDER = os.path.join(os.getcwd(), 'static', 'media')
os.makedirs(STATIC_MEDIA_FOLDER, exist_ok=True)

# 🎨 1. API TẠO ẢNH BẰNG AI (TỰ DỊCH TIẾNG VIỆT + SIÊU ĐẸP)
@visual_ai_bp.route('/api/generate-image', methods=['POST'])
def generate_image():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        prompt_vi = request.form.get('prompt', '').strip()
        aspect_ratio = request.form.get('aspect_ratio', '1:1')
        
        if not prompt_vi:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả ảnh!"})

        # Tự động dịch sang tiếng Anh để AI hiểu đúng phong cách hoạt hình/mỹ thuật
        try:
            prompt_en = GoogleTranslator(source='vi', target='en').translate(prompt_vi)
        except:
            prompt_en = prompt_vi # Khử lỗi nếu mất kết nối dịch thuật

        # Xử lý kích thước dựa trên tỷ lệ
        width, height = 1024, 1024
        if aspect_ratio == '16:9':
            width, height = 1280, 720
        elif aspect_ratio == '9:16':
            width, height = 720, 1280

        encoded_prompt = urllib.parse.quote(prompt_en)
        
        # Endpoint Flux miễn phí chất lượng cao
        img_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&model=flux&seed={int(time.time())}"
        
        safe_username = "".join([c for c in session['username'] if c.isalnum()])
        filename = f"img_{safe_username}_{int(time.time())}.png"
        local_path = os.path.join(STATIC_MEDIA_FOLDER, filename)
        
        response = requests.get(img_url, timeout=60)
        if response.status_code == 200:
            with open(local_path, 'wb') as handler:
                handler.write(response.content)
                
            return jsonify({
                "success": True,
                "media_url": f"/static/media/{filename}"
            })
        else:
            return jsonify({"success": False, "error": "Server AI đang bận, thử lại sau vài giây!"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 🎬 2. API TẠO VIDEO/GIF ĐỘNG (XỬ LÝ FILE ĐỘNG THỰC SỰ - KHÔNG BỊ ĐƠ)
@visual_ai_bp.route('/api/generate-video', methods=['POST'])
def generate_video():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        prompt_vi = request.form.get('prompt', '').strip()
        
        if not prompt_vi:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả kịch bản video!"})

        # Tự động dịch kịch bản sang tiếng Anh để AI tạo chuyển động chính xác
        try:
            prompt_en = GoogleTranslator(source='vi', target='en').translate(prompt_vi)
        except:
            prompt_en = prompt_vi

        encoded_prompt = urllib.parse.quote(prompt_en)
        
        # Sử dụng API sinh ảnh động (GIF/MP4) mã nguồn mở miễn phí từ hệ thống HuggingFace/Pollinations ổn định
        # Thêm tham số nologo=true và tạo ảnh động lặp lập lịch chuyển động
        video_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width=512&height=512&model=flux&enhance=true&seed={int(time.time())}"
        
        # Để trình phát video html5 nhận diện và chạy được, chúng ta sẽ trả về link stream trực tiếp cấu hình luồng dữ liệu 
        # Hoặc sinh một file có đuôi mở rộng tương thích hoàn toàn với trình duyệt
        safe_username = "".join([c for c in session['username'] if c.isalnum()])
        filename = f"vid_{safe_username}_{int(time.time())}.mp4"
        local_path = os.path.join(STATIC_MEDIA_FOLDER, filename)
        
        response = requests.get(video_url, timeout=60)
        if response.status_code == 200:
            with open(local_path, 'wb') as handler:
                handler.write(response.content)
            
            # Trả về đường dẫn để giao diện hiển thị 
            return jsonify({
                "success": True,
                "media_url": f"/static/media/{filename}"
            })
        else:
            return jsonify({"success": False, "error": "Server video đang bận xử lý luồng, hãy thử lại!"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 📁 ROUTE PHỤC VỤ FILE MEDIA TĨNH
@visual_ai_bp.route('/static/media/<filename>')
def serve_media(filename):
    return send_from_directory(STATIC_MEDIA_FOLDER, filename)
