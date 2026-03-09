from datetime import datetime
from . import db

class Post(db.Model):
    id = db.Column(db.Integer,primary_key = True)                # 文章id
    title = db.Column(db.String(100),nullable = False)           # 文章标题
    content = db.Column(db.Text,nullable = False)                # 文章内容
    created_at = db.Column(db.DateTime,default = datetime.utcnow)# 创建时间
    updated_at = db.Column(db.DateTime,default = datetime.utcnow,
                                      onupdate = datetime.utcnow)# 更新时间
    # 关联用户
    user_id = db.Column(db.Integer,nullable = False)
    # 关联分类
    category_id = db.Column(db.Integer,nullable = False)

    def __repr__(self):
        return '<Post %r>' % self.title