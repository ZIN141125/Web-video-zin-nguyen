import os
import json
import io
import asyncio
import re
import threading  # <--- Thêm thư viện xử lý đa luồng độc lập để cách ly tiến trình asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session, flash
from deep_translator import GoogleTranslator
from authlib.integrations.flask_client import OAuth
import edge_tts  # <--- Thêm thư viện edge-tts xử lý giọng đọc con người

app = Flask(__name__)
app.secret_key = 'son_dep_trai_he_thong_da_nguoi_dung'

# 📂 CẤU HÌCH THƯ MỤC LƯU TRỮ AUDIO MP3 TĨNH
STATIC_AUDIO_FOLDER = os.path.join(os.getcwd(), 'static', 'audio')
os.makedirs(STATIC_AUDIO_FOLDER, exist_ok=True)

# 🔑 CẤU HÌNH GOOGLE OAUTH
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# 📂 HÀM ĐỌC/GHI DỮ LIỆU JSON
def load_data():
    if not os.path.exists('data.json'):
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump({"users": {}, "videos": {}, "tools": {}}, f)
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 🏠 ROUTE TRANG CHỦ & ĐĂNG NHẬP
@app.route('/')
def index():
    if not session.get('username'):
        return render_template('index.html', show_login=True, is_register=False)
    return redirect(url_for('dashboard'))

# 📊 ROUTE DASHBOARD (KHÔNG GIAN LÀM VIỆC SAU KHI LOGGED IN)
@app.route('/dashboard')
def dashboard():
    if not session.get('username'):
        return redirect(url_for('index'))
    
    username = session['username']
    data = load_data()
    
    user_videos = data['videos'].get(username, [])
    user_tools = data['tools'].get(username, [])
    
    return render_template('index.html', show_login=False, username=username, videos=user_videos, tools=user_tools)

# 🔑 CHỨC NĂNG ĐĂNG KÝ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('index.html', show_login=True, is_register=True)
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    if not username or not password or not confirm_password:
        return render_template('index.html', show_login=True, is_register=True, error="Không được để trống thông tin!")
    
    if password != confirm_password:
        return render_template('index.html', show_login=True, is_register=True, error="Mật khẩu xác nhận không khớp!")
    
    data = load_data()
    if username in data['users']:
        return render_template('index.html', show_login=True, is_register=True, error="Tài khoản đã tồn tại!")
    
    data['users'][username] = password
    data['videos'][username] = []
    data['tools'][username] = []
    save_data(data)
    
    return render_template('index.html', show_login=True, is_register=False, success="Đăng ký thành công! Hãy đăng nhập.")

# 🔑 CHỨC NĂNG ĐĂNG NHẬP THƯỜNG
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    data = load_data()
    if username in data['users'] and data['users'][username] == password:
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html', show_login=True, is_register=False, error="Sai tài khoản hoặc mật khẩu!")

# 🚀 ĐIỀU HƯỚNG GOOGLE OAUTH
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if user_info:
            email = user_info['email']
            data = load_data()
            if email not in data['users']:
                data['users'][email] = "GOOGLE_OAUTH_ACCOUNT"
                if email not in data['videos']: data['videos'][email] = []
                if email not in data['tools']: data['tools'][email] = []
                save_data(data)
            session['username'] = email
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Lỗi Google Auth: {e}")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# 🎙️ ROUTE API TTS CHIA ĐOẠN ĐỘC LẬP - SỬA LỖI ĐỒNG BỘ GIỌNG ĐỌC CHI TIẾT
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập hệ thống!"})
    
    try:
        req_data = request.get_json() or {}
        raw_text = req_data.get('text', '')
        
        # 🎙️ ÉP ĐỒNG BỘ GIỌNG ĐỌC: Kiểm tra chặt chẽ chuỗi Front-end gửi lên
        input_voice = str(req_data.get('voice', '')).strip()
        
        # Thiết lập map giọng đọc chính xác để tránh Front-end truyền sai chuỗi định dạng
        if 'NamMinh' in input_voice or 'namminh' in input_voice.lower():
            voice = 'vi-VN-NamMinhNeural'
        elif 'MaiPhuong' in input_voice or 'maiphuong' in input_voice.lower() or 'mai' in input_voice.lower():
            voice = 'vi-VN-MaiPhuongNeural'
        else:
            voice = 'vi-VN-HoaiNamNeural' # Mặc định nếu không khớp hoặc lỗi truyền tin
        
        # 🧼 Bước 1: Làm sạch văn bản kịch bản đầu vào
        clean_lines = []
        for line in raw_text.split('\n'):
            line_str = line.strip()
            if line_str and not re.match(r'^[-\*_ ]+$', line_str):
                clean_lines.append(line_str)
        
        full_text = " ".join(clean_lines).strip()
        if not full_text:
            return jsonify({"success": False, "error": "Văn bản kịch bản trống hoặc không hợp lệ!"})

        # 🧩 Bước 2: Chia nhỏ kịch bản dài thành các đoạn an toàn (~200 từ/đoạn) dựa trên dấu ngắt câu
        words = full_text.split()
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for word in words:
            current_chunk.append(word)
            current_word_count += 1
            # Khi đoạn đạt từ 200 từ trở lên và kết thúc bằng một dấu ngắt câu, tiến hành tách đoạn
            if current_word_count >= 200 and word.endswith(('.', '!', '?', ':', ';', ',', '\"', '»')):
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_word_count = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        # Cấu hình file đích cố định theo tài khoản người dùng
        safe_username = "".join([c for c in session['username'] if c.isalnum()])
        final_filename = f"audio_{safe_username}.mp3"
        final_output_path = os.path.join(STATIC_AUDIO_FOLDER, final_filename)

        # 🔄 Bước 3: Hàm Worker tải luồng dữ liệu nhị phân song song/nối tiếp và gộp trực tiếp trên RAM
        def run_split_tts():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            
            try:
                combined_audio_data = bytearray()
                
                async def fetch_chunks():
                    nonlocal combined_audio_data
                    for chunk_text in chunks:
                        communicate = edge_tts.Communicate(chunk_text, voice)
                        chunk_bytes = bytearray()
                        
                        # Đọc trực tiếp luồng byte dữ liệu thô (audio chunk bytes) truyền về từ Microsoft
                        async_stream = communicate.stream()
                        async for chunk in async_stream:
                            if chunk["type"] == "audio":
                                chunk_bytes.extend(chunk["data"])
                        
                        # Gộp dữ liệu âm thanh phân đoạn nối tiếp nhau vào mảng RAM chung
                        combined_audio_data.extend(chunk_bytes)
                
                new_loop.run_until_complete(fetch_chunks())
                
                # Ghi một lần duy nhất toàn bộ khối dữ liệu tổng hợp xuống file MP3
                if combined_audio_data:
                    with open(final_output_path, "wb") as f:
                        f.write(combined_audio_data)
                        
            finally:
                new_loop.close()

        # Thực thi trong một tiểu trình (Thread) độc lập để tránh block tiến trình chính của server Render
        tts_thread = threading.Thread(target=run_split_tts)
        tts_thread.start()
        tts_thread.join(timeout=300) # Nâng thời gian chờ tối đa lên 5 phút cho kịch bản siêu dài

        # Kiểm tra tính toàn vẹn và dung lượng thực tế của file MP3 đầu ra
        if not os.path.exists(final_output_path) or os.path.getsize(final_output_path) == 0:
            if os.path.exists(final_output_path):
                os.remove(final_output_path)
            return jsonify({
                "success": False, 
                "error": f"Không thể kết xuất dữ liệu âm thanh kịch bản dài bằng giọng {voice}. Server Microsoft TTS từ chối kết nối. Hãy thử lại sau vài giây hoặc đổi sang giọng đọc khác!"
            })

        # Trả về URL dẫn đến file audio tĩnh kèm token thời gian thực (mtime) để buộc trình duyệt xóa cache file cũ
        return jsonify({
            "success": True, 
            "text": f"Đã xử lý thành công {len(chunks)} phân đoạn kịch bản dài bằng giọng đọc {voice}.",
            "audio_url": f"/static/audio/{final_filename}?v={os.path.getmtime(final_output_path)}"
        })
        
    except Exception as e:
        print(f"Lỗi hệ thống kết xuất âm thanh kịch bản dài: {e}")
        return jsonify({"success": False, "error": str(e)})


# Route để cấu hình Flask trả về file MP3 trong thư mục tĩnh static/audio/
@app.route('/static/audio/<filename>')
def serve_audio(filename):
    return send_from_directory(STATIC_AUDIO_FOLDER, filename)

# 🌐 API DỊCH THUẬT ĐA NGÔN NGỮ LINH HOẠT ĐA CHIỀU
@app.route('/api/translate', methods=['POST'])
def translate_text():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập"})
    
    req_data = request.get_json()
    text = req_data.get('text', '')
    source_lang = req_data.get('source', 'auto')
    target_lang = req_data.get('lang', 'vi')
    
    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        return jsonify({"success": True, "result": translated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# 📂 CÁC ROUTE LƯU TRỮ KHÁC (GIỮ NGUYÊN)
@app.route('/add_video', methods=['POST'])
def add_video():
    if not session.get('username'): return redirect(url_for('index'))
    username = session['username']
    data = load_data()
    if username not in data['videos']: data['videos'][username] = []
    data['videos'][username].append({
        "title": request.form.get('title'),
        "status": request.form.get('status'),
        "script": request.form.get('script'),
        "drive_link": request.form.get('drive_link')
    })
    save_data(data)
    return redirect(url_for('dashboard'))

@app.route('/add_tool', methods=['POST'])
def add_tool():
    if not session.get('username'): return redirect(url_for('index'))
    username = session['username']
    data = load_data()
    if username not in data['tools']: data['tools'][username] = []
    data['tools'][username].append({
        "name": request.form.get('name'),
        "url": request.form.get('url'),
        "note": request.form.get('note')
    })
    save_data(data)
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
