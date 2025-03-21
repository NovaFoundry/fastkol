import asyncio
import logging
from app.config import settings
from app.rabbitmq.consumer import RabbitMQConsumer
from app.db.operations import init_db
from app.celery_app import celery_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # 初始化数据库连接
    await init_db()
    
    # 启动RabbitMQ消费者
    consumer = RabbitMQConsumer(
        url=settings.RABBITMQ_URL,
        queue=settings.RABBITMQ_QUEUE
    )
    
    try:
        logger.info("Starting RabbitMQ consumer...")
        await consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await consumer.close()

if __name__ == "__main__":
    asyncio.run(main()) 