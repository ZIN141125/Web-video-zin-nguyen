from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

# Hàm xử lý đọc dữ liệu từ file JSON
def load_data():
    if not os.path.exists('data.json'):
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump({"videos": [], "tools": []}, f)
    with open('data.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Hàm xử lý ghi dữ liệu vào file JSON
def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Đường dẫn trang chủ hiển thị danh sách video và công cụ
@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', videos=data['videos'], tools=data['tools'])

# Đường dẫn xử lý khi thêm một video mới
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

# Đường dẫn xử lý khi thêm một công cụ mới
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

# CHẠY ỨNG DỤNG - Cấu hình PORT chuẩn dành riêng cho Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
