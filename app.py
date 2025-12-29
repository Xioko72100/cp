# app.py
# pip install flask peewee bcrypt wtforms waitress
import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from peewee import *
from bcrypt import hashpw, gensalt, checkpw
from wtforms import Form, StringField, PasswordField, validators

# --- 1. 資料庫與模型配置 ---

# 使用標準 SQLite 資料庫 (已修正：替換 SqliteExtDatabase)
DB_PATH = 'database.db'
db = SqliteDatabase(DB_PATH) 

# Flask Session 密鑰
SECRET_KEY = os.environ.get('SECRET_KEY', 'default_super_secret_key_123_change_this!')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField(unique=True, index=True)
    password_hash = CharField()
    
    # 創建使用者並雜湊密碼
    @staticmethod
    def create_user(username, password):
        if User.select().where(User.username == username).exists():
            raise ValueError("Username already exists.")
        
        # 雜湊密碼，確保密碼編碼為 bytes
        hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
        return User.create(username=username, password_hash=hashed_password)

class Score(BaseModel):
    user = ForeignKeyField(User, backref='scores')
    score_value = IntegerField()
    timestamp = DateTimeField(default=datetime.now)
    
    class Meta:
        # 建立複合索引以加速英雄榜查詢
        indexes = (
            (('score_value', 'timestamp'), False),
        )

# 初始化資料庫連接和表格
def initialize_db(db):
    """連接資料庫並創建表格 (如果不存在)"""
    db.connect()
    db.create_tables([User, Score], safe=True) 
    if not db.is_closed():
        db.close()

# --- 2. 表單驗證 (WTForms) ---

class RegistrationForm(Form):
    # 使用者名稱驗證：長度必須在 4 到 25 個字元之間
    username = StringField('Username', [validators.Length(min=4, max=25)])
    
    # 密碼驗證：必須輸入資料，且必須與 'confirm' 欄位一致
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')

class LoginForm(Form):
    username = StringField('Username', [validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])

# --- 3. Flask 應用程式設定與路由 ---

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
initialize_db(db)

# 自定義登入檢查裝飾器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('您需要登入才能訪問此頁面。', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def before_request():
    """在每次請求前連接資料庫"""
    if db.is_closed():
        db.connect()

@app.after_request
def after_request(response):
    """在每次請求後關閉資料庫連接"""
    if not db.is_closed():
        db.close()
    return response

# --- 4. 路由定義 ---

@app.route('/')
def index():
    """英雄榜 / 歡迎頁"""
    try:
        top_scores = (Score
                      .select(Score.score_value, User.username)
                      .join(User)
                      .order_by(Score.score_value.desc())
                      .limit(10))
        
        leaderboard_data = [{'username': s.user.username, 'score': s.score_value} for s in top_scores]
    except Exception as e:
        print(f"Leaderboard error: {e}")
        leaderboard_data = []

    return render_template('index.html', leaderboard=leaderboard_data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """使用者註冊"""
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            User.create_user(form.username.data, form.password.data)
            flash('註冊成功！您現在可以登入了。', 'success')
            return redirect(url_for('login'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception:
            flash('註冊失敗，請稍後再試。', 'danger')
            
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """使用者登入"""
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            user = User.get(User.username == form.username.data)
        except User.DoesNotExist:
            flash('無效的使用者名稱或密碼。', 'danger')
            return render_template('login.html', form=form)

        # 驗證密碼：確保密碼和雜湊都為 bytes
        if checkpw(form.password.data.encode('utf-8'), user.password_hash.encode('utf-8')):
            session['username'] = user.username 
            session['user_id'] = user.id
            flash('登入成功！', 'success')
            return redirect(url_for('game'))
        else:
            flash('無效的使用者名稱或密碼。', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    """使用者登出"""
    session.pop('username', None)
    session.pop('user_id', None)
    flash('您已成功登出。', 'info')
    return redirect(url_for('index'))

@app.route('/game')
@login_required 
def game():
    """遊戲運行頁面"""
    return render_template('game.html')

@app.route('/submit_score', methods=['POST'])
@login_required
def submit_score():
    """接收 Brython 傳來分數的 API 接口"""
    # 1. 檢查 Content-Type: application/json
    if not request.is_json:
        print("Error: Request is not JSON.")
        return jsonify({'success': False, 'message': 'Request must be JSON format. Did you set Content-Type header?'}), 415

    score_value = request.json.get('score')
    
    # 2. 檢查分數值的有效性
    if score_value is None or not str(score_value).isdigit():
        print(f"Error: Invalid or missing score value received: {score_value}")
        return jsonify({'success': False, 'message': 'Invalid score value provided.'}), 400

    try:
        user_id = session.get('user_id')
        
        # 3. 檢查 Session 中的 user_id
        if user_id is None:
            print("Error: user_id missing from session during score submission.")
            return jsonify({'success': False, 'message': 'Authentication failed or session expired.'}), 401

        user = User.get_by_id(user_id)
        
        # 儲存分數
        Score.create(
            user=user, 
            score_value=int(score_value),
            timestamp=datetime.now()
        )
        print(f"Success: Score {score_value} saved for user {user.username}.")
        return jsonify({'success': True, 'message': 'Score saved successfully!'})
        
    except User.DoesNotExist:
        # 使用者ID在資料庫中不存在
        print(f"Error: User ID {user_id} not found in database.")
        session.pop('username', None)
        session.pop('user_id', None)
        return jsonify({'success': False, 'message': 'User not found, please log in again.'}), 401
    
    except Exception as e:
        # 資料庫/其他伺服器錯誤
        print(f"Error saving score (Internal): {e}")
        return jsonify({'success': False, 'message': 'Internal error saving score. Check server logs.'}), 500

if __name__ == '__main__':
    app.run(debug=True)