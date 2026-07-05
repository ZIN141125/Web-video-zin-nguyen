import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, flash
import json
from deep_translator import GoogleTranslator
from gtts import gTTS
import io
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
# Giữ nguyên secret key gốc của Sơn để không bị mất phiên đăng nhập cũ
app.secret_key = 'son_dep_trai_he_thong_da_nguoi_dung'

# ⚙️ CẤU HÌNH GOOGLE OAUTH (Lấy chìa khóa từ Environment trên Render)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Hàm đọc ghi dữ liệu cấu trúc cũ (Giữ nguyên 100%)
def load_data():
    if not os.path.exists('data.json'):
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump({"users": {}, "videos": {}, "tools": {}}, f)
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Trang chủ xử lý hiển thị giao diện (Cập nhật hỗ trợ cả Username thường và Google Email)
@app.route('/')
def index():
    if not session.get('username'):
        return render_template('index.html', show_login=True, is_register=False)
    
    username = session['username']
    data = load_data()
    
    # Lấy dữ liệu riêng của user này, nếu chưa có thì trả về danh sách rỗng
    user_videos = data['videos'].get(username, [])
    user_tools = data['tools'].get(username, [])
    
    return render_template('index.html', show_login=False, username=username, videos=user_videos, tools=user_tools)

# Chức năng Đăng ký tài khoản mới bằng tay (Giữ nguyên)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('index.html', show_login=True, is_register=True)
    
    username = request.form.get('username').strip()
    password = request.form.get('password').strip()
    
    if not username or not password:
        return render_template('index.html', show_login=True, is_register=True, error="Không được để trống tài khoản/mật khẩu")
    
    data = load_data()
    if username in data['users']:
        return render_template('index.html', show_login=True, is_register=True, error="Tài khoản này đã tồn tại rồi!")
    
    # Lưu user mới
    data['users'][username] = password
    data['videos'][username] = []
    data['tools'][username] = []
    save_data(data)
    
    return render_template('index.html', show_login=True, is_register=False, success="Đăng ký thành công! Hãy đăng nhập nhé.")

# Chức năng Đăng nhập bằng tài khoản mật khẩu cũ (Đã sửa lỗi 404)
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

# 🚀 ROUTE ĐIỀU HƯỚNG SANG GOOGLE (Xử lý khi bấm nút Google trên giao diện)
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

# 🔄 ROUTE NHẬN KẾT QUẢ ĐĂNG NHẬP TỪ GOOGLE TRẢ VỀ
@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            email = user_info['email']
            
            # Đọc file data.json để kiểm tra xem Email Google này đã có trong hệ thống chưa
            data = load_data()
            
            # Nếu Email này chưa từng đăng nhập, tự động tạo kho lưu trữ Video/Tools riêng cho họ luôn
            if email not in data['users']:
                data['users'][email] = "GOOGLE_OAUTH_ACCOUNT" # Đánh dấu tài khoản đăng nhập bằng Google
                if email not in data['videos']: data['videos'][email] = []
                if email not in data['tools']: data['tools'][email] = []
                save_data(data)
                
            # Đăng nhập thành công, gán session['username'] chính là email để dùng chung logic hệ thống cũ
            session['username'] = email
            return redirect(url_for('index'))
            
    except Exception as e:
        print(f"Lỗi đăng nhập Google: {e}")
        
    return redirect(url_for('index'))

# Chức năng Đăng xuất (Xóa sạch phiên làm việc)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Thêm video (Giữ nguyên)
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

# Thêm công cụ (Giữ nguyên)
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

# API dịch thuật (Giữ nguyên)
@app.route('/api/translate', methods=['POST'])
def translate_text():
    if not session.get('username'): return jsonify({"success": False, "error": "Chưa đăng nhập"})
    req_data = request.get_json()
    text = req_data.get('text', '')
    target_lang = req_data.get('lang', 'vi')
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return jsonify({"success": True, "result": translated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API chuyển văn bản thành giọng nói (Giữ nguyên)
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    if not session.get('username'): return jsonify({"success": False, "error": "Chưa đăng nhập"})
    req_data = request.get_json()
    text = req_data.get('text', '')
    try:
        tts = gTTS(text=text, lang='vi', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return send_file(fp, mimetype='audio/mp3', as_attachment=False)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
