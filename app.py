from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import json
import os
from deep_translator import GoogleTranslator
from gtts import gTTS
import io

app = Flask(__name__)

# Đọc dữ liệu JSON
def load_data():
    if not os.path.exists('data.json'):
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump({"videos": [], "tools": []}, f)
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Ghi dữ liệu JSON
def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', videos=data['videos'], tools=data['tools'])

@app.route('/add_video', methods=['POST'])
def add_video():
    data = load_data()
    data['videos'].append({
        "title": request.form.get('title'),
        "status": request.form.get('status'),
        "script": request.form.get('script'),
        "drive_link": request.form.get('drive_link')
    })
    save_data(data)
    return redirect(url_for('index'))

@app.route('/add_tool', methods=['POST'])
def add_tool():
    data = load_data()
    data['tools'].append({
        "name": request.form.get('name'),
        "url": request.form.get('url'),
        "note": request.form.get('note')
    })
    save_data(data)
    return redirect(url_for('index'))

# TÍNH NĂNG AI 1: Dịch văn bản kịch bản công nghệ AI
@app.route('/api/translate', methods=['POST'])
def translate_text():
    req_data = request.get_json()
    text = req_data.get('text', '')
    target_lang = req_data.get('lang', 'vi') # Mặc định dịch sang tiếng Việt
    try:
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return jsonify({"success": True, "result": translated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# TÍNH NĂNG AI 2: Chuyển kịch bản chữ thành giọng nói (.mp3)
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
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
