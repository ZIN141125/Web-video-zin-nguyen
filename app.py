import os
import json
import io
import asyncio
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, flash
from deep_translator import GoogleTranslator
import edge_tts
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = 'son_dep_trai_he_thong_da_nguoi_dung'

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

# 🏠 ROUTE TRANG CHỦ
@app.route('/')
def index():
    if not session.get('username'):
        return render_template('index.html', show_login=True, is_register=False)
    
    username = session['username']
    data = load_data()
    
    user_videos = data['videos'].get(username, [])
    user_tools = data['tools'].get(username, [])
    
    return render_template('index.html', show_login=False, username=username, videos=user_videos, tools=user_tools)

# 🔑 CHỨC NĂNG ĐĂNG KÝ (ĐÃ THÊM Ô XÁC NHẬN MẬT KHẨU)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('index.html', show_login=True, is_register=True)
    
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    confirm_password = request.form.get('confirm_password').strip() # Lấy ô xác nhận mật khẩu
    
    if not username or not password or not confirm_password:
        return render_template('index.html', show_login=True, is_register=True, error="Không được để trống thông tin!")
    
    # Kiểm tra xem 2 mật khẩu nhập vào có trùng khớp không
    if password != confirm_password:
        return render_template('index.html', show_login=True, is_register=True, error="Mật khẩu xác nhận không khớp! Vui lòng nhập lại.")
    
    data = load_data()
    if username in data['users']:
        return render_template('index.html', show_login=True, is_register=True, error="Tài khoản này đã tồn tại rồi!")
    
    data['users'][username] = password
    data['videos'][username] = []
    data['tools'][username] = []
    save_data(data)
    
    return render_template('index.html', show_login=True, is_register=False, success="Đăng ký thành công! Hãy đăng nhập nhé.")

# 🔑 CHỨC NĂNG ĐĂNG NHẬP THƯỜNG
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    
    data = load_data()
    if username in data['users'] and data['users'][username] == password:
        session['username'] = username
        return redirect(url_for('index'))
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
            return redirect(url_for('index'))
    except Exception as e:
        print(f"Lỗi Google Auth: {e}")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 🎙️ API TTS NÂNG CẤP (EDGE-TTS: KHÔNG GIỚI HẠN TỪ, GIỌNG CON NGƯỜI)
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập"})
    
    req_data = request.get_json()
    text = req_data.get('text', '').strip()
    
    # Danh sách giọng đọc AI Việt Nam siêu giống người thật:
    # 1. vi-VN-HoaiNamNeural (Nam - Giọng đọc truyện/tin tức cực hay)
    # 2. vi-VN-NamMinhNeural (Nam - Giọng chuẩn, ấm áp)
    # 3. vi-VN-MaiPhuongNeural (Nữ - Giọng mượt mà, truyền cảm)
    voice = req_data.get('voice', 'vi-VN-HoaiNamNeural') 
    
    if not text:
        return jsonify({"success": False, "error": "Văn bản trống"})
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        fp = io.BytesIO()
        
        # Chạy vòng lặp bất đồng bộ để xử lý chuỗi văn bản dài từ 3000-5000 từ cực tốc độ
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for chunk in loop.run_until_complete(communicate.stream()):
            if chunk["data"]:
                fp.write(chunk["data"])
                
        fp.seek(0)
        return send_file(fp, mimetype='audio/mp3', as_attachment=False)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# 🌐 API DỊCH THUẬT ĐA NGÔN NGỮ TOÀN CẦU
@app.route('/api/translate', methods=['POST'])
def translate_text():
    if not session.get('username'): 
        return jsonify({"success": False, "error": "Chưa đăng nhập"})
    
    req_data = request.get_json()
    text = req_data.get('text', '')
    target_lang = req_data.get('lang', 'vi') # Nhận mã ngôn ngữ linh hoạt từ giao diện (en, zh-CN, ja, ko, fr...)
    
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
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
    return redirect(url_for('index'))

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
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
