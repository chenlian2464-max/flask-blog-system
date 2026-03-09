from datetime import datetime
from . import db

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 关联用户
    user_id = db.Column(db.Integer,nullable = False)
    # 关联文章
    post_id = db.Column(db.Integer,nullable = False)

    def __repr__(self):
        return '<Comment %r>' % self.id