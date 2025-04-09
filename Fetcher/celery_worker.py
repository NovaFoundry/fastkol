import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.celery_app import app

if __name__ == '__main__':
    app.start() 