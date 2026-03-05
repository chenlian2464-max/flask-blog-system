from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_paginate import Pagination, get_page_parameter
from datetime import datetime

# 实例化应用,设计数据库连接
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 密钥,用于flash消息
app.config['SECRET_KEY'] = b'asdfghjkl'
# 分页设置
app.config['POSTS_PER_PAGE'] = 3
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
        db.drop_all()  # 先删干净
        db.create_all()  # 按模型定义顺序创建表
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
    # 处理搜索
    search_query = request.args.get('search','')
    # 处理分页
    page = request.args.get(get_page_parameter(),type = int,default = 1)
    pre_page = app.config['POSTS_PER_PAGE']
    # 构建查询条件
    post_query = Post.query.order_by(Post.created_at.desc())
    pagination = post_query.paginate(
        page = page,
        per_page = pre_page,
        error_out = False,
        max_per_page = 3
    )
    posts = pagination.items
    # 构建查询对象
    query = Post.query.order_by(Post.created_at.desc())
    if search_query:
        query = query.filter(Post.title.contains(search_query) | Post.content.contains(search_query))
    # 手动补充作者和分类信息
    for post in posts:
        post.author = User.query.get(post.user_id) if post.user_id else None
        post.category = Category.query.get(post.category_id) if post.category_id else None
    # 展示文章列表(传递paginatio对象和搜索条件)
    return render_template("index.html",posts = posts,pagination = pagination,search_query = search_query)
# 注册路由
@app.route('/register',methods = ['GET','POST'])
def register():
     # 初始化表单变量
    form_data = {
        'username': '',
        'email': ''
    }
    # 处理注册请求
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        # 获取表单数据
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        # 更新表单回显数据
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
        # 加密密码
        try:
            hashed_password = bcrypt.generate_password_hash(password,rounds = 10).decode('utf-8')
        except Exception as e:
            flash(f"密码加密失败:{str(e)}","error")
            return render_template('register.html', **form_data)
        # 创建新用户并保存到数据库
        user = User(username = username,email = email,password = hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("注册成功！请登录","success")
        return redirect(url_for('login'))
      # 跳转到登录页面
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
        email = request.form['email']
        password = request.form['password']
        form_data['email'] = email
        # 基础校验
        if not email or not password:
            flash('请填写邮箱和密码！', 'error')
            return render_template('login.html', **form_data)
        user = User.query.filter_by(email=email).first()
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
            flash(f'密码验证失败：{str(e)}', 'error')
            return render_template('login.html', **form_data)
        #登录用户
        login_user(user)
        flash("登录成功","success")
        return redirect(url_for('index'))
    # 跳转到登录页面
    return render_template('login.html',**form_data)
# 退出登录
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("您已退出登录",'success')
    return redirect(url_for('index'))
# 文章详情页（评论）
@app.route("/post/<int:post_id>",methods = ["POST","GET"])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    # 手动补充作者和分类
    post.author = get_post_author(post)
    post.category = get_post_category(post)
    # 获取评论
    comments = get_post_comments(post_id)
    # 给评论补充作者信息
    for comment in comments:
        comment.author = User.query.get(comment.user_id)
        if not comment.author:
            comment.author = type('Anonymous', (), {'username': '匿名用户'})()
    # 处理评论
    if request.method == 'POST' and current_user.is_authenticated:
        content = request.form.get('comment','').strip()
        if content:
            comment = Comment(
                content = content,
                user_id = current_user.id,
                post_id = post_id
            )
            db.session.add(comment)
            db.session.commit()
            # 提交后重定向，重新加载页面（确保新评论也有 author）
            return redirect(url_for('post', post_id=post_id))
        else:
            flash("评论内容不能为空！","error")
    # 获取该文章的所有评论
    comments = Comment.query.filter_by(post_id = post_id).order_by(Comment.created_at.desc()).all()
    return render_template("post.html",post = post,comments = comments)
# 创建文章(分类，登录验证)
@app.route("/create",methods = ["GET","POST"])
@login_required
def create():
    # 获取所有分类
    categories = Category.query.all()
    # 获取文章标题和内容（post请求）
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        category_id = request.form.get("category")
    # 验证文章标题和内容是否为空
        if not title:
            flash("标题或内容不能为空","error")
            return redirect(url_for("create"))
    # 保存文章到数据库
        new_post = Post(
            title = title,
            content = content,
            user_id = current_user.id,
            category_id = category_id if category_id else None
        )
        try:
            db.session.add(new_post)
            db.session.commit()
            flash("文章创建成功","success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"文章创建失败:{str(e)}","error")
            return redirect(url_for("create"))
    # 展示创建表单(get请求)
    return render_template("edit.html",is_create = True,categories = categories)
# 编辑文章
@app.route("/edit/<int:post_id>",methods = ["GET","POST"])
@login_required
def edit(post_id):
    post = Post.query.get_or_404(post_id)
    categories = Category.query.all()

    if post.user_id != current_user.id:
        abort(403) # 未授权访问

    if request.method == "POST":
        post.title =request.form.get("title").strip()
        post.content = request.form.get("content").strip()
        post.category_id = request.form.get("category")

        if not post.title or not post.content:
            flash("标题或内容不能为空","error")
            return redirect(url_for("post",post_id = post_id))
        
        try:
            db.session.commit()
            flash("文章更新成功","success")
            return redirect(url_for("post",post_id = post_id))
        except Exception as e:
            flash(f"文章更新失败:{str(e)}","error")
            return redirect(url_for("edit"),post_id = post_id)
    return render_template("edit.html",post = post,is_create = False,categories = categories)
# 删除文章
@app.route("/delete/<int:post_id>")
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
        flash(f"文章删除失败{str(e)}","error")
    return redirect(url_for("index"))
# 删除评论
@app.route('/delete_comment/<int:comment_id>')
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    post = Post.query.get(post_id)
    # 验证评论作者
    if comment.user_id != current_user.id and post.user_id != current_user.id:
        abort(403) # 未授权访问
    post_id =comment.post_id
    try:
        db.session.delete(comment)
        db.session.commit()
        flash("评论删除成功","success")
    except Exception as e:
        flash(f"评论删除失败{str(e)}","error")
    return redirect(url_for("post",post_id = post_id))
# 添加分类
@app.route('/add_category',methods = ['POST'])
@login_required
def add_category():
    if request.method == 'POST':
        name = request.form['category_name'].strip()
        if not name:
            flash("分类名称不能为空！","error")
        elif Category.query.filter_by(name = name).first():
            flash("分类已存在！","error")
        else:
            category = Category(name = name)
            db.session.add(category)
            db.session.commit()
            flash(f"分类{name}添加成功！","success")
    # 跳转到创建文章页面
    return redirect(url_for('create'))
if __name__ == '__main__':
    init_db()
    app.run(debug = True,port = 5001,use_reloader = False)