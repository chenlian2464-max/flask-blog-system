from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_paginate import Pagination, get_page_parameter
from datetime import datetime
import settings
import os

# 确保实例文件夹存在
if not os.path.exists('instance'):
    os.mkdir('instance')

app = Flask(__name__)

app.config.from_object(settings.DevelopmentConfig) # 开发环境配置
# app.config.from_object(settings.ProductionConfig) # 生产环境配置

# 分页设置
app.config['POSTS_PRE_PAGE'] = 3
# 实例化数据库对象
db = SQLAlchemy(app)
# 实例化bcrypt对象
bcrypt = Bcrypt(app)
# 登录管理器
login_manager = LoginManager(app)
login_manager.init_app(app) # 初始化登录管理器
login_manager.login_view = "login" # 设置登录视图函数名(未登录时跳转到该视图)

"""数据库模型定义"""
# 1.用户模型
class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
# 2.分类模型
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
# 3.文章模型
class Post(db.Model):
    id = db.Column(db.Integer,primary_key = True)                # 文章id
    title = db.Column(db.String(100),nullable = False)           # 文章标题
    content = db.Column(db.Text,nullable = False)                # 文章内容
    created_at = db.Column(db.DateTime,default = datetime.utcnow)# 创建时间
    updated_at = db.Column(db.DateTime,default = datetime.utcnow,updated_at = datetime.utcnow)# 更新时间
    # 关联用户
    user_id = db.Column(db.Integer,nullable = False)
    # 关联分类
    category_id = db.Column(db.Integer,nullable = False)
# 4.评论模型
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 关联用户
    user_id = db.Column(db.Integer,nullable = False)
    # 关联文章
    post_id = db.Column(db.Integer,nullable = False)

# -------------------------- 手动关联函数（替代外键关联） --------------------------
# 获取文章作者
def get_post_author(post):
    return User.query.get(post.user_id)

# 获取文章分类
def get_post_category(post):
    if post.category_id:
        return Category.query.get(post.category_id)
    return None

# 获取文章评论
def get_post_comments(post_id):
    return Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()

# 获取用户的文章
def get_user_posts(user_id):
    return Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()

# 用户加载器（login-manager使用）
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) if user_id else None
# -------------------------- 数据库初始化（调整为仅在首次运行/需要时执行） --------------------------
def init_db():
    with app.app_context():
        db.create_all() 
        # 添加默认分类
        if not Category.query.first():
            for name in ['技术笔记', '生活随笔', '学习总结']:
                db.session.add(Category(name=name))
            db.session.commit()
    print("数据库初始化完成！")



"""路由定义"""

# 首页（分页，搜索）
@app.route('/')
def index():
    # 处理搜索（request.args获取URL中查询字符串的参数，http://xxx/?search=python）
    search_query = request.args.get('search','')
    # 处理分页（get_page_parameter()获取分页参数名，默认值为page，http://xxx/?page=2）
    page = request.args.get(get_page_parameter(),type = int,default = 1)
    pre_page = app.config['POSTS_PRE_PAGE']
    # 构建查询条件（搜索条件）
    post_query = Post.query.order_by(Post.created_at.desc()) # 查询Post模型（文章表）的所有数据，按创建时间倒序排列，最新的放前面
    if search_query:
        post_query = post_query.filter(
            post_query.title.contanins() | post_query.content.contains(search_query)
        )
    # 构建分页对象
    pagination = post_query.paginate(
        page = page,        # 当前页码
        per_page = pre_page,# 每页显示数量
        error_out = False,  # 若页码超出范围，是否报错
        max_per_page = app.config['POSTS_PRE_PAGE'] # 最大每页显示数量
    )
    posts = pagination.items # 获取当前页码的文章列表
   
    # 手动补充作者和分类信息
    for post in posts:# 可优化
        # 根据user_id查询User模型，添加作者信息
        post.author = User.query.get(post.user_id) if post.user_id else None
        # 根据category_id查询Category模型，添加分类信息
        post.category = Category.query.get(post.category_id) if post.category_id else None
    # 展示文章列表(传递paginatio对象和搜索条件)
    return render_template("index.html",posts = posts,pagination = pagination,search_query = search_query)

"""用户认证模块（核心权限控制）"""
# 注册路由
@app.route('/register',methods = ['GET','POST'])
def register():
    # 初始化表单变量
    form_data = {
        'username': '',
        'email': ''
    }
    # 拦截已登录用户
    if current_user.is_authenticated:  # is_authenticated判断用户是否登录
        return redirect(url_for('index'))
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
            return render_template('register.html', **form_data)
        if password != confirm_password:
            flash('两次密码不一致！', 'error')
            return render_template('register.html', **form_data)
        if User.query.filter_by(username=username).first():
            flash('用户名已存在！', 'error')
            return render_template('register.html', **form_data)
        if User.query.filter_by(email=email).first():
            flash('邮箱已注册！', 'error')
            return render_template('register.html', **form_data)
        # 可增加密码长度（如至少 6 位）、复杂度（包含字母 + 数字）校验。

        # 加密密码
        try:
            # bcrypt加密，rounds参数设置加密强度，越大越安全，默认10，加密后转为utf-8编码
            hashed_password = bcrypt.generate_password_hash(password,rounds = 10).decode('utf-8')
        except Exception as e:
            flash(f"密码加密失败:{str(e)}","error")
            return render_template('register.html', **form_data)
        # 创建新用户并保存到数据库
        user = User(username = username,email = email,password = hashed_password)
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback() # 回滚,避免脏数据
            flash(f"用户注册失败:{str(e)}","error")
            return render_template('register.html', **form_data)
        flash("注册成功！请登录","success")
        return redirect(url_for('login'))
      # 渲染注册页面
    return render_template('register.html',**form_data)
# 登录路由
@app.route('/login',methods = ['GET','POST'])
def login():
    # 初始化表单变量
    form_data = {'email': ''}
    # 处理登录请求
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        form_data['email'] = email # 更新回显数据
        # 基础校验
        if not email or not password:
            flash('请填写邮箱和密码！', 'error')
            return render_template('login.html', **form_data)
        user = User.query.filter_by(email=email).first() # 查询用户
        if not user:
            flash('邮箱未注册！', 'error')
            return render_template('login.html', **form_data)
        # 验证密码
        try:
            # 检查密码（user.password 是加密后的字符串）
            if not bcrypt.check_password_hash(user.password, password):
                flash('密码错误！', 'error')
                return render_template('login.html', **form_data)
        except Exception as e:
            flash(f'系统异常：{str(e)}', 'error')
            return render_template('login.html', **form_data)
        #登录用户
        # login_user(user, remember=True) # 记住登录状态,需要前端配合传 remember 参数。
        login_user(user)
        flash("登录成功","success")
        return redirect(url_for('index'))
    # 渲染登录页面
    return render_template('login.html',**form_data)
# 退出登录
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("您已退出登录",'success')
    return redirect(url_for('index'))



"""文章管理模块（核心内容创作）"""
# 文章详情页（评论）
@app.route("/post/<int:post_id>",methods = ["POST","GET"])
def post(post_id):
    post = Post.query.get_or_404(post_id) # 查询文章存在或404
    # 手动补充作者和分类（可优化）
    post.author = get_post_author(post)
    post.category = get_post_category(post)
    # 处理评论
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('comment','').strip()
        if content:
            comment = Comment(
                content = content,
                user_id = current_user.id,
                post_id = post_id
            )
            try:
                db.session.add(comment)
                db.session.commit()
                flash("评论成功！","success")
                # 提交后重定向，重新加载页面（确保新评论也有 author）
                return redirect(url_for('post', post_id=post_id))
            except Exception as e:
                db.session.rollback()
                flash(f"评论失败:{str(e)}","error")
        else:
            flash("评论内容不能为空！","error")
    # 获取该文章的评论和补充作者信息
    comments = Comment.query.filter_by(post_id = post_id).order_by(Comment.created_at.desc()).all()
    for comment in comments:
        comment.author = User.query.get(comment.user_id)
        if not comment.author:
            comment.author = type('Anonymous', (), {'username': '匿名用户'})() # 动态创建一个名为 Anonymous 的类并实例化，该对象有 username 属性，值为「匿名用户」
    return render_template("post.html",post = post,comments = comments)
# 创建文章(分类，登录验证)
@app.route("/create",methods = ["GET","POST"])
@login_required
def create():
    # 获取所有分类
    categories = Category.query.all()
    # 获取文章标题和内容
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        category_id = request.form.get("category")
    # 验证文章标题和内容是否为空
        if not title or not content:
            flash("标题或内容不能为空","error")  # 回显已填数据
            return render_template("edit.html", is_create=True, categories=categories, 
                           title=title, content=content, category_id=category_id)
    # 保存文章到数据库
        new_post = Post(
            title = title,
            content = content,
            user_id = current_user.id,
            category_id = int(category_id) if category_id else None
        )
        try:
            db.session.add(new_post)
            db.session.commit()
            flash("文章创建成功","success")
            return redirect(url_for("index"))
        except Exception as e:
            db.session.rollback()
            flash(f"文章创建失败:{str(e)}","error")
            return redirect(url_for("create"))
    return render_template("edit.html",is_create = True,categories = categories)
# 编辑文章
@app.route("/edit/<int:post_id>",methods = ["POST","GET"])
@login_required
def edit(post_id):
    post = Post.query.get_or_404(post_id) # 查询文章存在或404
    categories = Category.query.all()     # 获取所有分类

    if post.user_id != current_user.id:
        abort(403) # 未授权访问

    if request.method == "POST":
        title =request.form.get("title").strip()
        content = request.form.get("content").strip()
        category_id = int(request.form.get("category")) if request.form.get("category") else None




        if not title or not content:
            flash("标题或内容不能为空","error") 
            return render_template("edit.html",post = post,is_create = False,categories = categories)
        
        # 更新文章
        post.title = title
        post.content = content
        post.category_id = category_id

        try:
            db.session.commit()
            flash("文章更新成功","success")
            return redirect(url_for("post",post_id = post_id))
        except Exception as e:
            db.session.rollback()
            flash(f"文章更新失败:{str(e)}","error")
            return redirect(url_for("edit",post_id = post_id))
    return render_template("edit.html",post = post,is_create = False,categories = categories)
# 删除文章
@app.route("/delete/<int:post_id>",methods = ["GET"])
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        abort(403) # 未授权访问
    try:
        # 先删除关联评论
        Comment.query.filter_by(post_id=post_id).delete()
        # 删除文章
        db.session.delete(post)
        db.session.commit()
        flash("文章删除成功","success")
        return redirect(url_for("index"))
    except Exception as e:
        db.session.rollback()
        flash(f"文章删除失败{str(e)}","error")
        return redirect(url_for("index"))
# 删除评论
@app.route('/delete_comment/<int:comment_id>',methods = ['GET'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id     # 评论所属文章ID
    post = Post.query.get_or_404(post_id)# 查询文章ID
    # 验证评论作者(评论作者和文章作者可以删除评论)
    if comment.user_id != current_user.id and post.user_id != current_user.id:
        abort(403) # 未授权访问
    try:
        db.session.delete(comment)
        db.session.commit()
        flash("评论删除成功","success")
    except Exception as e:
        db.session.rollback()
        flash(f"评论删除失败{str(e)}","error")
    return redirect(url_for("post",post_id = post_id))



"""分类管理模块（内容维度管理）"""
# 创建分类
@app.route('/add_category',methods = ['POST'])
@login_required
def add_category():
    name = request.form.get('category_name','').strip()
    if not name:
        flash("分类名称不能为空！","error")
    elif Category.query.filter_by(name = name).first():
        flash("分类已存在！","error")
    else:
        try:
            category = Category(name = name)
            db.session.add(category)
            db.session.commit()
            flash(f"分类{name}添加成功！","success")
        except:
            db.session.rollback()
            flash("分类添加失败！","error")
    # 跳转到创建文章页面
    return redirect(url_for('create'))
# 删除分类
# 查看分类


"""评论互动模块（内容互动）"""
# 删除评论
if __name__ == '__main__':
    init_db()
    app.run(debug = True,port = 5001,use_reloader = False)