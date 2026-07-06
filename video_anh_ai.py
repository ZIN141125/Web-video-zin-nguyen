import os
import time
import requests
import urllib.parse
import replicate  # Sử dụng để sinh video thực tế
from flask import Blueprint, request, jsonify, session, send_from_directory
from deep_translator import GoogleTranslator

# Khởi tạo Blueprint
visual_ai_bp = Blueprint('visual_ai', __name__)

# Cấu hình thư mục lưu trữ media
STATIC_MEDIA_FOLDER = os.path.join(os.getcwd(), 'static', 'media')
os.makedirs(STATIC_MEDIA_FOLDER, exist_ok=True)


# =================================================================
# 🎨 1. API TẠO ẢNH BẰNG AI (GIỮ NGUYÊN HOẶC CHUYỂN REPLICATE)
# =================================================================
@visual_ai_bp.route('/api/generate-image', methods=['POST'])
def generate_image():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        # Nhận dữ liệu từ form (hỗ trợ cả JSON hoặc Form data)
        if request.is_json:
            req_data = request.get_json()
            prompt_vi = req_data.get('prompt', '').strip()
            aspect_ratio = req_data.get('aspect_ratio', '1:1')
        else:
            prompt_vi = request.form.get('prompt', '').strip()
            aspect_ratio = request.form.get('aspect_ratio', '1:1')
        
        if not prompt_vi:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả ảnh!"})

        # Tự động dịch sang tiếng Anh để AI hiểu đúng ý tưởng
        try:
            prompt_en = GoogleTranslator(source='vi', target='en').translate(prompt_vi)
        except:
            prompt_en = prompt_vi 

        # Xử lý kích thước dựa trên tỷ lệ
        width, height = 1024, 1024
        if aspect_ratio == '16:9':
            width, height = 1280, 720
        elif aspect_ratio == '9:16':
            width, height = 720, 1280

        encoded_prompt = urllib.parse.quote(prompt_en)
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
                "media_type": "image",
                "media_url": f"/static/media/{filename}"
            })
        else:
            return jsonify({"success": False, "error": "Server AI đang bận, thử lại sau vài giây!"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# =================================================================
# 🎬 2. API TẠO VIDEO AI THỰC TẾ (SỬ DỤNG LTX-VIDEO QUA REPLICATE)
# =================================================================
@visual_ai_bp.route('/api/generate-video', methods=['POST'])
def generate_video():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập!"})
    
    try:
        # Nhận dữ liệu linh hoạt từ JSON hoặc Form data
        if request.is_json:
            req_data = request.get_json()
            prompt_vi = req_data.get('prompt', '').strip()
            aspect_ratio = req_data.get('aspect_ratio', '16:9')
        else:
            prompt_vi = request.form.get('prompt', '').strip()
            aspect_ratio = request.form.get('aspect_ratio', '16:9')
        
        if not prompt_vi:
            return jsonify({"success": False, "error": "Vui lòng nhập mô tả kịch bản video!"})

        # Tự động dịch kịch bản sang tiếng Anh giúp AI dựng chuyển động chính xác
        try:
            prompt_en = GoogleTranslator(source='vi', target='en').translate(prompt_vi)
        except:
            prompt_en = prompt_vi

        # Gọi mô hình LTX-Video chuẩn trên Replicate để sinh file .mp4 thực tế
        output = replicate.run(
            "lightricks/ltx-video:0a2d05a4207865768560383b16867a9cf186debf98ff8e5a7b633ec27f4c6e94",
            input={
                "prompt": prompt_en,
                "aspect_ratio": aspect_ratio,
                "num_inference_steps": 40,
                "frame_rate": 25
            }
        )

        # Replicate trả về kết quả dạng chuỗi URL hoặc một danh sách chứa URL video
        if isinstance(output, list) and len(output) > 0:
            remote_video_url = output[0]
        else:
            remote_video_url = output

        # Tiến hành tải file .mp4 từ server Replicate về server của bạn để lưu trữ an toàn
        safe_username = "".join([c for c in session['username'] if c.isalnum()])
        filename = f"vid_{safe_username}_{int(time.time())}.mp4"
        local_path = os.path.join(STATIC_MEDIA_FOLDER, filename)

        video_response = requests.get(remote_video_url, timeout=120)
        if video_response.status_code == 200:
            with open(local_path, 'wb') as handler:
                handler.write(video_response.content)
            
            # Trả về thành công kèm thuộc tính media_type rõ ràng
            return jsonify({
                "success": True,
                "media_type": "video",
                "media_url": f"/static/media/{filename}"
            })
        else:
            return jsonify({"success": False, "error": "Không thể tải tệp video từ máy chủ AI về hệ thống!"})

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            error_msg = "Tài khoản Replicate đã đạt giới hạn gọi miễn phí hoặc chưa thiết lập phương thức thanh toán!"
        return jsonify({"success": False, "error": error_msg})


# 📁 ROUTE PHỤC VỤ FILE MEDIA TĨNH
@visual_ai_bp.route('/static/media/<filename>')
def serve_media(filename):
    return send_from_directory(STATIC_MEDIA_FOLDER, filename)
