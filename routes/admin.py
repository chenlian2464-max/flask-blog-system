from flask import Blueprint, render_template, flash, redirect, url_for, request,abort
from flask_login import login_required, current_user
from models import db, Post, Category, User

def get_user_posts(user_id):
    return Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
# 获取文章作者
def get_post_author(post):
    return User.query.get(post.user_id)
# 获取文章分类
def get_post_category(post):
    if post.category_id:
        return Category.query.get(post.category_id)
    return None

# 管理员蓝图（路径前缀：/admin）
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理员仪表盘（路径：/admin/dashboard）
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    total_posts = Post.query.count()
    total_users = User.query.count()
    total_categories = Category.query.count()
    return render_template('admin/dashboard.html',
                           total_posts=total_posts,
                           total_users=total_users,
                           total_categories=total_categories)

"""分类管理模块（内容维度管理）"""
# 创建分类
@admin_bp.route('/add_category',methods=['POST','GET'])
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
    return redirect(url_for('blog.create'))


# 分类列表页
@admin_bp.route('/categories')
@login_required
def category_list():
    # 简单权限控制：仅第一个用户（管理员）可访问
    if not current_user.is_admin:
        abort(403)
    categories = Category.query.order_by(Category.created_at.desc()).all()
    return render_template('admin/category_list.html', categories=categories)

# 编辑分类
@admin_bp.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    if not current_user.is_admin:
        abort(403)
    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        new_name = request.form.get('name').strip()
        if not new_name:
            flash('分类名称不能为空！', 'danger')
            return redirect(url_for('edit_category', id=id))
        # 检查重名（排除自身）
        if Category.query.filter(Category.name == new_name, Category.id != id).first():
            flash('该分类名称已存在！', 'danger')
            return redirect(url_for('edit_category', id=id))
        category.name = new_name
        db.session.commit()
        flash('分类修改成功！', 'success')
        return redirect(url_for('admin.category_list'))
    return render_template('admin/edit_category.html', category=category)

# 删除分类
@admin_bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    if not current_user.is_admin:
        abort(403)
    category = Category.query.get_or_404(id)
    # 检查分类下是否有文章（可选：防止误删有内容的分类）
    category.posts = get_user_posts(id)
    if category.posts:
        flash('该分类下仍有文章，无法删除！', 'danger')
        return redirect(url_for('admin.category_list'))
    db.session.delete(category)
    db.session.commit()
    flash('分类删除成功！', 'success')
    return redirect(url_for('admin.category_list'))

# 分类详情页：展示该分类下的所有文章
@admin_bp.route('/category/<int:id>')
def category_detail(id):
    category = Category.query.get_or_404(id)
     # 手动补充作者和分类信息
    for post in posts:# 可优化
        # 根据user_id查询User模型，添加作者信息
        post.author = User.query.get(post.user_id) if post.user_id else None
        # 根据category_id查询Category模型，添加分类信息
        post.category = Category.query.get(post.category_id) if post.category_id else None
    posts = category.get_posts()
    categories = Category.query.all()  # 侧边栏分类列表
    return render_template('blog/index.html', 
                           category=category, 
                           posts=posts,
                           categories=categories)