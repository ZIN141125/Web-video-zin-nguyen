import os
import json
import io
import asyncio
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session, flash
from deep_translator import GoogleTranslator
from authlib.integrations.flask_client import OAuth
import edge_tts  # <--- Thêm thư viện edge-tts xử lý giọng đọc con người

app = Flask(__name__)
app.secret_key = 'son_dep_trai_he_thong_da_nguoi_dung'

# 📂 CẤU HÌNH THƯ MỤC LƯU TRỮ AUDIO MP3 TĨNH
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

# 🎙️ BƯỚC 1: ROUTE API TTS ĐÃ ĐƯỢC CHỈNH SỬA TOÀN DIỆN VÀ CHẠY ỔN ĐỊNH
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập hệ thống!"})
    
    try:
        req_data = request.get_json() or {}
        raw_text = req_data.get('text', '')
        voice = req_data.get('voice', 'vi-VN-HoaiNamNeural') # Nhận cấu hình giọng chọn từ giao diện
        
        # 🧼 BẢO VỆ BACKEND: Lọc bỏ dòng trống và các dòng gạch phân tách kịch bản rác (---, ***, v.v.)
        clean_lines = []
        for line in raw_text.split('\n'):
            line_str = line.strip()
            # Bỏ qua dòng trống hoặc dòng chứa chuỗi ký tự phân tách đặc biệt
            if line_str and not re.match(r'^[-\*_ ]+$', line_str):
                clean_lines.append(line_str)
        
        text = "\n".join(clean_lines).strip()
        
        if not text:
            return jsonify({"success": False, "error": "Văn bản kịch bản trống hoặc chứa ký tự rác không hợp lệ!"})
            
        # Xác định tên file đầu ra dựa trên tài khoản để tránh ghi đè dồn dập giữa các phiên làm việc
        safe_username = "".join([c for c in session['username'] if c.isalnum()])
        filename = f"audio_{safe_username}.mp3"
        output_path = os.path.join(STATIC_AUDIO_FOLDER, filename)
        
        # Hàm xử lý chuyển đổi bất tuần tự của thư viện Edge-TTS
        async def generate_voice_file():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
        # 🌟 KHẮC PHỤC XUNG ĐỘT EVENT LOOP TRÊN RENDER/GUNICORN
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            # Nếu loop đang chạy (môi trường server bất đồng bộ phức tạp), ép tiến trình chạy đồng bộ an toàn
            future = asyncio.run_coroutine_threadsafe(generate_voice_file(), loop)
            future.result() # Đợi cho tới khi tạo xong file
        else:
            loop.run_until_complete(generate_voice_file())
        
        # Kiểm tra sự tồn tại và tính hợp lệ của file sau khi xuất bản
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return jsonify({"success": False, "error": "Hệ thống Edge-TTS không xuất được dữ liệu âm thanh hợp lệ."})

        # Trả về tín hiệu thành công kèm URL dẫn đến file audio tĩnh
        return jsonify({
            "success": True, 
            "text": text,
            "audio_url": f"/static/audio/{filename}"
        })
        
    except Exception as e:
        print(f"Lỗi hệ thống kết xuất âm thanh: {e}")
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
