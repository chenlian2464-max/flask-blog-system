from flask_sqlalchemy import SQLAlchemy

# 全局变量
"""数据库模型定义"""
db = SQLAlchemy()
# 导入模型类
from .user import User
from .post import Post
from .comment import Comment
from .category import Category

__all__ = ['db', 'User', 'Post', 'Comment', 'Category']