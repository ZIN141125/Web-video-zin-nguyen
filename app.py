import os
from flask import Flask, redirect, url_for, session, render_template, request, flash
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)

# 🔑 CẤU HÌNH BẢO MẬT (BẮT BUỘC)
# Thay 'SECRET_KEY_BAC_PHUONG_SON' bằng một chuỗi ký tự bất kỳ tùy ý bạn để làm khóa mã hóa session
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'SECRET_KEY_BAC_PHUONG_SON')

# 🛠️ Cấu hình kết nối Google OAuth lấy từ Environment trên Render
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# Khởi tạo module OAuth
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

# 🏠 1. ROUTE TRANG CHỦ / ĐĂNG NHẬP THÔNG THƯỜNG
@app.route('/', methods=['GET', 'POST'])
def index():
    # Giả lập logic kiểm tra nếu đang ở màn hình Đăng ký hoặc Đăng nhập thông thường
    is_register = request.args.get('register') == 'true'
    
    if request.method == 'POST':
        # Đây là nơi xử lý Form tài khoản mật khẩu bình thường của Sơn (nếu có)
        # Tạm thời cấu hình chuyển hướng vào không gian làm việc sau khi post thành công
        session['user'] = 'Tài khoản thường'
        return redirect(url_for('dashboard'))
        
    return render_template('index.html', is_register=is_register, show_login=True)

# 🚀 2. ROUTE KÍCH HOẠT ĐĂNG NHẬP GOOGLE (Giải quyết lỗi 404 cũ)
@app.route('/login/google')
def login_google():
    # Tự động tạo link callback động theo tên miền của bạn (ví dụ: web-video-zin-nguyen.onrender.com)
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

# 🔄 3. ROUTE ĐÓN DỮ LIỆU TRẢ VỀ TỪ GOOGLE (CALLBACK)
@app.route('/login/google/callback')
def google_callback():
    try:
        # Lấy token xác thực từ Google trả về
        token = google.authorize_access_token()
        # Bóc tách thông tin cá nhân của người dùng (Email, Tên, Ảnh đại diện)
        user_info = token.get('userinfo')
        
        if user_info:
            # Lưu email người dùng đăng nhập vào Session của hệ thống
            session['user'] = user_info['email']
            session['user_name'] = user_info['name']
            session['user_picture'] = user_info['picture']
            
            flash(f"Đăng nhập thành công! Chào mừng {user_info['name']}", "success")
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash("Đăng nhập bằng Google thất bại. Vui lòng thử lại!", "danger")
        print(f"Lỗi OAuth: {e}")
        
    return redirect(url_for('index'))

# 💻 4. ROUTE TRANG QUẢN LÝ VIDEO (KHÔNG GIAN LÀM VIỆC)
@app.route('/dashboard')
def dashboard():
    # Kiểm tra nếu chưa đăng nhập thì bắt quay xe về trang chủ ngay
    if 'user' not in session:
        flash("Vui lòng đăng nhập trước!", "danger")
        return redirect(url_for('index'))
    
    # Đoạn này Sơn có thể trả về giao diện quản lý video chính của bạn
    return f"<h3>Xin chào {session.get('user_name', 'Bạn')} ({session.get('user')})!</h3><p>Đây là Không gian quản lý & Sáng tạo video của bạn.</p><br><a href='/logout'>Đăng xuất</a>"

# 🚪 5. ROUTE ĐĂNG XUẤT
@app.route('/logout')
def logout():
    session.clear() # Xóa sạch phiên đăng nhập
    flash("Bạn đã đăng xuất hệ thống.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Chạy ứng dụng nội bộ hỗ trợ cả HTTP và HTTPS
    app.run(debug=True)
