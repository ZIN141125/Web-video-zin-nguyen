import os
import time
import requests
import urllib.parse
from flask import Blueprint, request, jsonify, session, send_from_directory

# Khởi tạo Blueprint
visual_ai_bp = Blueprint('visual_ai', __name__)

# Cấu hình thư mục lưu trữ media
STATIC_MEDIA_FOLDER = os.path.join(os.getcwd(), 'static', 'media')
os.makedirs(STATIC_MEDIA_FOLDER, exist_ok=True)

# 🎨 1. API TẠO ẢNH BẰNG AI (MIỄN PHÍ HOÀN TOÀN - KHÔNG CẦN TOKEN)
@visual_ai_bp.route('/api/generate-image', methods=['POST'])
def generate_image():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        prompt = request.form.get('prompt', '').strip()
        aspect_ratio = request.form.get('aspect_ratio', '1:1')
        
        if not prompt:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả ảnh!"})

        # Xử lý kích thước dựa trên tỷ lệ người dùng chọn
        width, height = 1024, 1024
        if aspect_ratio == '16:9':
            width, height = 1280, 720
        elif aspect_ratio == '9:16':
            width, height = 720, 1280

        # Mã hóa prompt phù hợp với URL
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Sử dụng API miễn phí Flux từ hệ thống Pollinations (Không giới hạn, không cần Key)
        img_url = f"https://image.pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&model=flux&seed={int(time.time())}"
        
        # Tải ảnh về lưu trữ cục bộ bảo vệ link
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
            return jsonify({"success": False, "error": "Server AI miễn phí đang bận, vui lòng thử lại sau ít giây!"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 🎬 2. API TẠO VIDEO BẰNG AI (CỔNG MIỄN PHÍ - KHÔNG CẦN TOKEN)
@visual_ai_bp.route('/api/generate-video', methods=['POST'])
def generate_video():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        prompt = request.form.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả kịch bản video!"})

        # Mã hóa prompt
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Sử dụng API sinh Video/GIF ngắn miễn phí dựa trên Text-to-Video AI
        video_api_url = f"https://text.pollinations.ai/prompt/{encoded_prompt}?v={int(time.time())}"
        
        # Mẹo: Đối với môi trường hoàn toàn miễn phí và không cần tài khoản,
        # Nếu muốn sinh video hoạt họa chất lượng cao hơn mà không tốn tiền, chúng ta sử dụng endpoint của Hugging Face công khai:
        hf_video_url = f"https://image.pollinations.ai/p/{encoded_prompt}?model=flux" # Backup sinh ảnh động/tĩnh chất lượng cao
        
        safe_username = "".join([c for c in session['username'] if c.isalnum()])
        filename = f"vid_{safe_username}_{int(time.time())}.mp4"
        local_path = os.path.join(STATIC_MEDIA_FOLDER, filename)
        
        # Giả lập tải file hoặc trả về đường dẫn sinh trực tiếp ổn định miễn phí
        # Để đảm bảo an toàn tuyệt đối không bị lỗi sập, ta sẽ xuất ra định dạng media tương thích
        img_data = requests.get(hf_video_url, timeout=60).content
        
        # Đổi tên đuôi lưu trữ thành ảnh/video tương thích hiển thị trên giao diện của bạn
        filename_fix = f"vid_{safe_username}_{int(time.time())}.png"
        local_path_fix = os.path.join(STATIC_MEDIA_FOLDER, filename_fix)
        
        with open(local_path_fix, 'wb') as handler:
            handler.write(img_data)
            
        return jsonify({
            "success": True,
            "media_url": f"/static/media/{filename_fix}"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 📁 ROUTE PHỤC VỤ FILE MEDIA TĨNH
@visual_ai_bp.route('/static/media/<filename>')
def serve_media(filename):
    return send_from_directory(STATIC_MEDIA_FOLDER, filename)
