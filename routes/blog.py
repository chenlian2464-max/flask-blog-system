from flask_login import login_required, logout_user, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_paginate import  get_page_parameter
from models import db,User,Post,Category,Comment
import markdown

blog_bp = Blueprint('blog',__name__,)

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
"""文章管理模块（核心内容创作）"""
# 首页
@blog_bp.route('/')
def index():
    # 处理搜索（request.args获取URL中查询字符串的参数，http://xxx/?search=python）
    search_query = request.args.get('search','')
    # 处理分页（get_page_parameter()获取分页参数名，默认值为page，http://xxx/?page=2）
    page = request.args.get(get_page_parameter(),type = int,default = 1)
    pre_page = 3
    # 构建查询条件（搜索条件）
    post_query = Post.query.order_by(Post.created_at.desc()) # 查询Post模型（文章表）的所有数据，按创建时间倒序排列，最新的放前面
    if search_query:
        post_query = post_query.filter(
            Post.title.contains(search_query) | Post.content.contains(search_query)
        )
    # 构建分页对象
    pagination = post_query.paginate(
        page = page,        # 当前页码
        per_page = pre_page,# 每页显示数量
        error_out = False,  # 若页码超出范围，是否报错
        max_per_page = 5# 最大每页显示数量
    )
    posts = pagination.items # 获取当前页码的文章列表
   
    # 手动补充作者和分类信息
    for post in posts:# 可优化
        # 根据user_id查询User模型，添加作者信息
        post.author = User.query.get(post.user_id) if post.user_id else None
        # 根据category_id查询Category模型，添加分类信息
        post.category = Category.query.get(post.category_id) if post.category_id else None
    # 展示文章列表(传递paginatio对象和搜索条件)
    return render_template("blog/index.html",posts = posts,pagination = pagination,search_query = search_query)
# 文章详情页
@blog_bp.route('/post/<int:post_id>',methods=['GET','POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id) # 查询文章存在或404
    # 手动补充作者和分类（可优化）
    post.author = get_post_author(post)
    post.category = get_post_category(post)
    # 将Markdown内容转换为HTML
    post.content_html = markdown.markdown(
        post.content,
        extensions = [
           'markdown.extensions.extra',      
           'markdown.extensions.codehilite', # 语法高亮
           'markdown.extensions.toc'         # 自动生成目录
        ]
    )
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
                return redirect(url_for('blog.post', post_id=post_id))
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
    return render_template("blog/post.html",post = post,comments = comments)
# 发布文章页
@blog_bp.route('/create',methods=['GET','POST'])
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
            return render_template("blog/edit.html", is_create=True, categories=categories)
    # 验证分类是否存在
        if category_id and not Category.query.get(category_id):
            flash("分类不存在！","error")
            return render_template("blog/edit.html", is_create=True, categories=categories)
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
            return redirect(url_for("blog.index"))
        except Exception as e:
            db.session.rollback()
            flash(f"文章创建失败:{str(e)}","error")
            return redirect(url_for("create"))
    return render_template("blog/edit.html",is_create = True,categories = categories)
# 编辑文章页
@blog_bp.route('/edit/<int:post_id>',methods=['GET','POST'])
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
            return render_template("blog/edit.html",post = post,is_create = False,categories = categories)
        # 更新文章
        post.title = title
        post.content = content
        post.category_id = category_id
        try:
            db.session.commit()
            flash("文章更新成功","success")
            return redirect(url_for("blog.post",post_id = post_id))
        except Exception as e:
            db.session.rollback()
            flash(f"文章更新失败:{str(e)}","error")
            return redirect(url_for("blog.edit",post_id = post_id))
    return render_template("blog/edit.html",post = post,is_create = False,categories = categories)
# 删除文章
@blog_bp.route('/delete/<int:post_id>',methods=['POST','GET'])
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
        return redirect(url_for("blog.index"))
    except Exception as e:
        db.session.rollback()
        flash(f"文章删除失败{str(e)}","error")
        return redirect(url_for("blog.index"))
# 删除评论
@blog_bp.route('/delete_comment/<int:comment_id>',methods=["GET",'POST'])
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
    return redirect(url_for("blog.post",post_id = post_id))
