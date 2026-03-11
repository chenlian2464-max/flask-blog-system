from flask_login import login_user, login_required, logout_user, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from models import db, User

bcrypt = Bcrypt()

auth_bp = Blueprint('auth', __name__,url_prefix='/auth')
"""用户认证模块（核心权限控制）"""
# 注册路由
@auth_bp.route('/register', methods=['GET', 'POST'])
# 初始化表单变量
def register():
    form_data = {
        'username': '',
        'email': ''
    }
    # 拦截已登录用户
    if current_user.is_authenticated:  # is_authenticated判断用户是否登录
        return redirect(url_for('blog.index'))
    # 处理注册请求
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        # 更新表单回显数据（字典的值填充输入框，避免用户重新输入已填的用户名 / 邮箱，提升体验）
        form_data['username'] = username
        form_data['email'] = email
        # 基础校验
        if not username or not email or not password:
            flash('请填写所有必填项！', 'error')
            return render_template('auth/register.html', **form_data)
        if password != confirm_password:
            flash('两次密码不一致！', 'error')
            return render_template('auth/register.html', **form_data)
        if User.query.filter_by(username=username).first():
            flash('用户名已存在！', 'error')
            return render_template('auth/register.html', **form_data)
        if User.query.filter_by(email=email).first():
            flash('邮箱已注册！', 'error')
            return render_template('auth/register.html', **form_data)
        if len(password) < 6 or len(password) > 20:
            flash('密码长度必须在6-20位之间！', 'error')
            return render_template('auth/register.html', **form_data)

        # 加密密码
        try:
            # bcrypt加密，rounds参数设置加密强度，越大越安全，默认10，加密后转为utf-8编码
            hashed_password = bcrypt.generate_password_hash(password,rounds = 10).decode('utf-8')
        except Exception as e:
            flash(f"密码加密失败:{str(e)}","error")
            return render_template('auth/register.html', **form_data)
        # 创建新用户并保存到数据库
        user = User(username = username,email = email,password = hashed_password)
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback() # 回滚,避免脏数据
            flash(f"用户注册失败:{str(e)}","error")
            return render_template('auth/register.html', **form_data)
        flash("注册成功！请登录","success")
        return redirect(url_for('auth.login'))
      # 渲染注册页面
    return render_template('auth/register.html',**form_data)
# 登录路由
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 初始化表单变量
    form_data = {'email': ''}
    # 处理登录请求
    # 已登录用户直接跳转
    if current_user.is_authenticated:
        # 管理员跳转到管理后台，普通用户跳转到博客首页
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))  # 管理员后台路由
        return redirect(url_for('blog.index'))
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        form_data['email'] = email # 更新回显数据
        # 基础校验
        if not email or not password:
            flash('请填写邮箱和密码！', 'error')
            return render_template('auth/login.html', **form_data)
        user = User.query.filter_by(email=email).first() # 查询用户
        if not user:
            flash('邮箱未注册！', 'error')
            return render_template('auth/login.html', **form_data)
        # 验证密码
        try:
            # 检查密码（user.password 是加密后的字符串）
            if not bcrypt.check_password_hash(user.password, password):
                flash('密码错误！', 'error')
                return render_template('auth/login.html', **form_data)
        except Exception as e:
            flash(f'系统异常：{str(e)}', 'error')
            return render_template('auth/login.html', **form_data)
        #登录用户
        # login_user(user, remember=True) # 记住登录状态,需要前端配合传 remember 参数。
        login_user(user)
        flash("登录成功","success")
        if user.is_admin:
            # 管理员跳转到管理后台
            return redirect(url_for('admin.dashboard'))
        else:
            # 普通用户跳转到博客首页
            return redirect(url_for('blog.index'))
    # 渲染登录页面
    return render_template('auth/login.html',**form_data)
# 登出路由
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("您已退出登录",'success')
    return redirect(url_for('blog.index'))



# # 管理员后台路由
# @auth_bp.route('/admin/login', methods=['GET', 'POST'])
# def admin_login():
#     if request.method == 'GET':
#         # 已有登录则直接跳后台
#         if current_user.is_authenticated and isinstance(current_user, Admin):
#             return redirect(url_for('admin.dashboard'))
#         return render_template('auth/admin_login.html')  # 登录页模板
    
#     # POST 请求：验证登录
#     username = request.form.get('username')
#     password = request.form.get('password')
#     remember = request.form.get('remember') == 'on'

#     # 校验参数
#     if not username or not password:
#         flash('账号和密码不能为空', 'error')
#         return redirect(url_for('auth.admin_login'))
    
#     # 查询管理员
#     admin = Admin.query.filter_by(username=username).first()
#     if not admin or not admin.check_password(password):
#         flash('账号或密码错误', 'error')
#         return redirect(url_for('auth.admin_login'))
    
#     # 登录成功：创建会话
#     login_user(admin, remember=remember)
#     flash('登录成功', 'success')
#     return redirect(url_for('admin.dashboard'))  # 跳后台首页

