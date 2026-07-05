from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session
import json
import os
from deep_translator import GoogleTranslator
from gtts import gTTS
import io

app = Flask(__name__)
app.secret_key = 'son_dep_trai_he_thong_da_nguoi_dung'

# Hàm đọc ghi dữ liệu cấu trúc mới (Tách biệt theo Username)
def load_data():
    if not os.path.exists('data.json'):
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump({"users": {}, "videos": {}, "tools": {}}, f)
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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

# Chức năng Đăng ký tài khoản mới
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

# Chức năng Đăng nhập
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Thêm video (chỉ lưu vào kho của user đang đăng nhập)
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

# Thêm công cụ (chỉ lưu vào kho của user đang đăng nhập)
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
