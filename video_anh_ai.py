import os
import time
import requests
from flask import Blueprint, request, jsonify, session, send_from_directory
import replicate

# Khởi tạo Blueprint (Mô-đun tính năng riêng biệt)
visual_ai_bp = Blueprint('visual_ai', __name__)

# Cấu hình thư mục lưu trữ media
STATIC_MEDIA_FOLDER = os.path.join(os.getcwd(), 'static', 'media')
os.makedirs(STATIC_MEDIA_FOLDER, exist_ok=True)

# 🎨 1. API TẠO ẢNH BẰNG AI
@visual_ai_bp.route('/api/generate-image', methods=['POST'])
def generate_image():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        prompt = request.form.get('prompt', '').strip()
        aspect_ratio = request.form.get('aspect_ratio', '1:1')
        
        if not prompt:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả ảnh!"})

        input_data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "num_outputs": 1,
            "output_format": "png"
        }
        
        # Gọi mô hình Flux sinh ảnh siêu nhanh
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input=input_data
        )
        
        if output and len(output) > 0:
            img_url = output[0]
            
            # Lưu ảnh tĩnh nội bộ bảo vệ link không bị die
            safe_username = "".join([c for c in session['username'] if c.isalnum()])
            filename = f"img_{safe_username}_{int(time.time())}.png"
            local_path = os.path.join(STATIC_MEDIA_FOLDER, filename)
            
            img_data = requests.get(img_url).content
            with open(local_path, 'wb') as handler:
                handler.write(img_data)
                
            return jsonify({
                "success": True,
                "media_url": f"/static/media/{filename}"
            })
        else:
            return jsonify({"success": False, "error": "AI không trả về kết quả hình ảnh."})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 🎬 2. API TẠO VIDEO BẰNG AI
@visual_ai_bp.route('/api/generate-video', methods=['POST'])
def generate_video():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        prompt = request.form.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả kịch bản video!"})

        input_data = {
            "prompt": prompt,
            "num_frames": 49 # Thời lượng khoảng 3-4 giây
        }

        # Gọi mô hình LTX-Video mã nguồn mở
        output = replicate.run(
            "fofr/ltx-video", 
            input=input_data
        )
        
        if output:
            video_url = output
            
            # Tải video về lưu local
            safe_username = "".join([c for c in session['username'] if c.isalnum()])
            filename = f"vid_{safe_username}_{int(time.time())}.mp4"
            local_path = os.path.join(STATIC_MEDIA_FOLDER, filename)
            
            video_data = requests.get(video_url).content
            with open(local_path, 'wb') as handler:
                handler.write(video_data)
                
            return jsonify({
                "success": True,
                "media_url": f"/static/media/{filename}"
            })
        else:
            return jsonify({"success": False, "error": "AI không trả về kết quả video."})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# 📁 ROUTE PHỤC VỤ FILE MEDIA TĨNH
@visual_ai_bp.route('/static/media/<filename>')
def serve_media(filename):
    return send_from_directory(STATIC_MEDIA_FOLDER, filename)
