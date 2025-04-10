import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.celery_app import app

if __name__ == '__main__':
    logger.info("启动 Celery 工作进程...")
    # 使用 worker 命令启动 Celery 工作进程
    argv = [
        'worker',
        '--loglevel=INFO',
        '--pool=solo',  # 在 Windows 上使用 solo 池
        '-n', 'fetcher_worker@%h'
    ]
    app.worker_main(argv) 