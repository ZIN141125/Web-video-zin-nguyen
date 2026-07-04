```python
# =========================
# IMPORT THƯ VIỆN
# =========================

from flask import Flask, render_template, request, redirect
import json
import os

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Tên file lưu dữ liệu
DATA_FILE = "data.json"


# =========================
# HÀM KHỞI TẠO FILE JSON
# =========================

def initialize_data_file():
    """
    Nếu file data.json chưa tồn tại
    thì tự động tạo file mới.
    """

    if not os.path.exists(DATA_FILE):

        default_data = {
            "videos": [],
            "tools": []
        }

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                default_data,
                f,
                ensure_ascii=False,
                indent=4
            )


# =========================
# HÀM ĐỌC DỮ LIỆU JSON
# =========================

def load_data():
    """
    Đọc dữ liệu từ file JSON
    """

    initialize_data_file()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:

        print("Lỗi đọc dữ liệu:", e)

        return {
            "videos": [],
            "tools": []
        }


# =========================
# HÀM GHI DỮ LIỆU JSON
# =========================

def save_data(data):
    """
    Ghi dữ liệu vào file JSON
    """

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


# =========================
# TRANG CHỦ
# =========================

@app.route("/")
def index():
    """
    Hiển thị giao diện chính
    """

    data = load_data()

    videos = data.get("videos", [])
    tools = data.get("tools", [])

    return render_template(
        "index.html",
        videos=videos,
        tools=tools
    )


# =========================
# THÊM VIDEO
# =========================

@app.route("/add_video", methods=["POST"])
def add_video():
    """
    Nhận dữ liệu từ form Video
    """

    data = load_data()

    video = {

        "title": request.form.get("title", "").strip(),

        "status": request.form.get(
            "status",
            "Ý tưởng"
        ).strip(),

        "script": request.form.get(
            "script",
            ""
        ).strip(),

        "drive_link": request.form.get(
            "drive_link",
            ""
        ).strip()
    }

    data["videos"].append(video)

    save_data(data)

    return redirect("/")


# =========================
# THÊM CÔNG CỤ
# =========================

@app.route("/add_tool", methods=["POST"])
def add_tool():
    """
    Nhận dữ liệu từ form Công cụ
    """

    data = load_data()

    tool = {

        "name": request.form.get(
            "tool_name",
            ""
        ).strip(),

        "url": request.form.get(
            "tool_url",
            ""
        ).strip(),

        "note": request.form.get(
            "tool_note",
            ""
        ).strip()
    }

    data["tools"].append(tool)

    save_data(data)

    return redirect("/")


# =========================
# CHẠY ỨNG DỤNG
# =========================

if __name__ == "__main__":

    # Lấy PORT từ môi trường
    # Render sẽ tự truyền biến PORT
    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    # Chạy Flask
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
```

