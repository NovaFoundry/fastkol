import logging
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.settings import settings
from app.db.models import FetchTask, Base
from typing import Optional

logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_async_engine(
    settings.get_config("database", {}).get("url", ""),
    isolation_level="REPEATABLE READ"  # 设置事务隔离级别
)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成")

async def create_fetch_task(task_data: dict, status: str="pending", result: list=[], error: str=None) -> FetchTask:
    """创建新的任务记录
    
    Args:
        task_data: 任务数据字典
        
    Returns:
        FetchTask: 创建的任务记录
        
    Raises:
        Exception: 当创建失败时抛出异常
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                async with session.begin():
                    fetch_task = FetchTask(
                        task_id=task_data.get('task_id', ''),
                        platform=task_data.get('platform', ''),
                        action=task_data.get('action', ''),
                        params=task_data.get('params', {}),
                        status=status,
                        result=result,
                        error=error
                    )
                    session.add(fetch_task)
                    await session.commit()
                    logger.info(f"新任务已创建，任务ID: {task_data.get('task_id', '')}")
                    return fetch_task
        except Exception as e:
            logger.warning(f"创建任务失败，重试 {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"最终创建任务失败: {str(e)}")
                raise

async def update_fetch_task(task_id: str, status: str, result: list = None, error: str = None) -> bool:
    """更新任务状态和结果
    
    Args:
        task_id: 任务ID
        status: 新状态
        result: 可选的成功结果数据
        error: 可选的错误信息
        
    Returns:
        bool: 更新是否成功
        
    Raises:
        Exception: 当更新失败时抛出异常
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                async with session.begin():
                    stmt = select(FetchTask).where(FetchTask.task_id == task_id)
                    result_proxy = await session.execute(stmt)
                    task = result_proxy.scalar_one_or_none()
                    
                    if not task:
                        logger.error(f"任务不存在，任务ID: {task_id}")
                        return False
                    
                    task.status = status
                    if result is not None:
                        task.result = result
                    if error is not None:
                        task.error = error
                    
                    await session.commit()
                    logger.info(f"任务状态已更新，任务ID: {task_id}, 新状态: {status}")
                    return True
        except Exception as e:
            logger.warning(f"更新任务状态失败，重试 {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"最终更新任务状态失败: {str(e)}")
                raise

async def get_fetch_task(task_id: str) -> Optional[FetchTask]:
    """获取任务信息
    
    Args:
        task_id: 任务ID
        
    Returns:
        Optional[FetchTask]: 任务信息，如果任务不存在则返回None
        
    Raises:
        Exception: 当查询失败时抛出异常
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                stmt = select(FetchTask).where(FetchTask.task_id == task_id)
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()
                
                if not task:
                    logger.warning(f"任务不存在，任务ID: {task_id}")
                    return None
                
                logger.info(f"成功获取任务信息，任务ID: {task_id}")
                return task
        except Exception as e:
            logger.warning(f"获取任务信息失败，重试 {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"最终获取任务信息失败: {str(e)}")
                raise