import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from app.settings import settings
from app.db.models import FetchResult, Proxy, Base

logger = logging.getLogger(__name__)

# 创建数据库引擎
engine = create_async_engine(settings.get_config("database", {}).get("url", ""))
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成")

async def save_result(task_data, result):
    """保存爬取结果到数据库"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with SessionLocal() as session:
                async with session.begin():  # 使用事务上下文管理器
                    fetch_result = FetchResult(
                        task_id=task_data.get('task_id', ''),
                        platform=task_data.get('platform', ''),
                        action=task_data.get('action', ''),
                        params=task_data.get('params', {}),
                        result=result
                    )
                    session.add(fetch_result)
                    await session.commit()
                    logger.info(f"结果已保存到数据库，任务ID: {task_data.get('task_id', '')}")
                    return  # 成功保存后退出函数
        except Exception as e:
            logger.warning(f"保存结果到数据库失败，重试 {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"最终保存结果到数据库失败: {str(e)}")
                raise  # 如果重试仍然失败，抛出异常

async def get_all_proxies():
    """获取所有活跃代理"""
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                select(Proxy).where(Proxy.is_active == 1)
            )
            proxies = result.scalars().all()
            return [
                {
                    "host": p.host,
                    "port": p.port,
                    "username": p.username,
                    "password": p.password,
                    "protocol": p.protocol
                }
                for p in proxies
            ]
    except Exception as e:
        logger.error(f"获取代理列表失败: {str(e)}")
        return [] 