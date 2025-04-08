import json
import logging
import aio_pika
from app.celery_app import process_task
from app.settings import settings

logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    def __init__(self, url, queue):
        self.url = url
        self.queue_name = queue
        self.connection = None
        self.channel = None
        self.queue = None
    
    async def connect(self):
        """连接到RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()
        
        # 声明队列
        self.queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True
        )
        
        logger.info(f"Connected to RabbitMQ, queue: {self.queue_name}")
    
    async def start_consuming(self):
        """开始消费消息"""
        if not self.connection:
            await self.connect()
        
        async def process_message(message):
            async with message.process():
                try:
                    # 解码消息体
                    body = message.body.decode()
                    task_data = json.loads(body)
                    
                    logger.info(f"接收到任务: {task_data}")
                    
                    # 使用Celery处理任务
                    process_task.delay(task_data)
                    
                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
        
        # 设置消费者
        await self.queue.consume(process_message)
        
        # 保持脚本运行
        logger.info("Waiting for messages. To exit press CTRL+C")
        try:
            # 阻塞直到被中断
            await self.connection.wait_closed()
        except Exception as e:
            logger.error(f"Consumer interrupted: {str(e)}")
    
    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()
            logger.info("RabbitMQ connection closed") 