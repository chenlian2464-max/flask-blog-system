from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
from flask import Flask
from routes import auth_bp, blog_bp, admin_bp
from models import db,User,Category
import settings
import os
import sys


# 模块导入路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,BASE_DIR)

# 初始化应用
app = Flask(__name__, instance_relative_config=True) 
app.config.from_object(settings.DevelopmentConfig)   
os.makedirs('instance', exist_ok=True)                         # 示例文件
db.init_app(app)                                               # 数据加载
bcrypt = Bcrypt()                                              # 加密解密 
login_manager = LoginManager(app)                              # 登录认证   
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'
login_manager.remember_cookie_duration = timedelta(minutes=0)  # 记住我有效期设为 0             
@login_manager.user_loader                           
def load_user(user_id):
    return db.session.get(User, int(user_id))



# 注册蓝图
app.register_blueprint(auth_bp)                                # 认证蓝图
app.register_blueprint(blog_bp)                                # 博客蓝图
app.register_blueprint(admin_bp)                               # 管理蓝图
# 初始数据
with app.app_context():
    db.drop_all()
    db.create_all()
    """自定义管理员"""
    if not User.query.filter_by(username='admin').first():     
        admin = User(username='admin', email='admin@localhost')
        password = '123456'
        hashed_password =bcrypt.generate_password_hash(password,rounds = 10).decode('utf-8')
        admin.password = hashed_password
        admin.is_admin = True
        db.session.add(admin)
        if not Category.query.first():                # 初始分类
            for name in ['技术笔记', '生活随笔', '学习总结']:
                db.session.add(Category(name=name))
        db.session.commit()
if __name__ == '__main__':
    app.run(port = 5001)