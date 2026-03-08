import os


class Config:
    instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_path,'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # 信号追踪，关闭可节省内存
    SECRET_KEY = 'asdfghjkl'
class DevelopmentConfig(Config):
    DEBUG = True
class ProductionConfig(Config):
    DEBUG = False
    # 生产环境数据库配置
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(Config.instance_path, 'prod.db')


