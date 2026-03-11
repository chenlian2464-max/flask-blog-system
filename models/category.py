from datetime import datetime
from . import db

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_posts(self):
        from models import Post
        return Post.query.filter_by(category_id=self.id).all()

    def get_post_count(self):
        from models import Post
        return Post.query.filter_by(category_id=self.id).count()
    
    def __repr__(self):
        return f"Category('{self.name}')"