from celery import Celery
import os
import sys
import logging
import asyncio
import nest_asyncio
from typing import Tuple, List, Dict, Any
from app.settings import settings
from app.fetchers.twitter import TwitterFetcher
from app.fetchers.youtube import YoutubeFetcher
from app.fetchers.instagram import InstagramFetcher
from app.fetchers.tiktok import TiktokFetcher
from app.proxy.pool import ProxyPool
from app.account_pool.manager import AccountManager
from app.db.operations import update_fetch_task

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置日志
logger = logging.getLogger(__name__)

# 创建 Celery 实例
app = Celery(
    'fetcher',
    broker=settings.get_config("celery", {}).get("broker_url", ""),
    backend=settings.get_config("celery", {}).get("result_backend", ""),
    include=['app.fetchers.twitter']  # 包含任务模块
)

# 可选的 Celery 配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.get_config("celery", {}).get("timezone", "UTC"),
    enable_utc=settings.get_config("celery", {}).get("enable_utc", True),
    broker_connection_retry_on_startup=True,  # 添加启动时的连接重试设置
    result_expires=settings.get_config("celery", {}).get("result_expires", 3600),
)

# 创建全局资源
proxy_pool = ProxyPool()
account_manager = AccountManager()

# 允许嵌套事件循环
nest_asyncio.apply()

@app.task(name='app.celery_app.process_similar_task')
def process_similar_task(task_data):
    """处理相似用户查找任务"""
    try:
        task_id = task_data.get('task_id')
        platform = task_data.get('platform')
        params = task_data.get('params', {})
        
        logger.info(f"处理相似用户查找任务 {task_id}: {platform} 平台")
        
        async def async_process():
            """异步处理任务的内部函数"""
            try:
                # 运行爬虫获取结果
                success, msg, result = await run_similar_fetcher(platform, params)
                if success:
                    # 保存结果到数据库
                    await update_fetch_task(task_id, "completed", result)
                    return {"status": "success", "user_count": len(result)}
                else:
                    logger.error(f"任务处理失败: {msg}")
                    await update_fetch_task(task_id, "failed", result, msg)
                    return {"status": "failed", "error": msg}
            except Exception as e:
                logger.error(f"任务处理失败: {str(e)}")
                await update_fetch_task(task_id, "failed", None, str(e))
                return {"status": "failed", "error": str(e)}
        
        # 使用 asyncio.run() 执行异步任务       
        return asyncio.run(async_process())
    
    except Exception as e:
        logger.error(f"任务处理外部失败: {str(e)}")
        return {"status": "error", "error": str(e)}

@app.task(name='app.celery_app.process_search_task')
def process_search_task(task_data):
    """处理用户搜索任务"""
    try:
        task_id = task_data.get('task_id')
        platform = task_data.get('platform')
        params = task_data.get('params', {})
        
        logger.info(f"处理用户搜索任务 {task_id}: {platform} 平台")
        
        async def async_process():
            """异步处理任务的内部函数"""
            try:
                # 运行爬虫获取结果
                success, msg, result = await run_search_fetcher(platform, params)
                if success:
                    # 保存结果到数据库
                    await update_fetch_task(task_id, "completed", result)
                    return {"status": "success", "user_count": len(result)}
                else:
                    logger.error(f"任务处理失败: {msg}")
                    await update_fetch_task(task_id, "failed", result, msg)
                    return {"status": "failed", "error": msg}
            except Exception as e:
                logger.error(f"任务处理失败: {str(e)}")
                await update_fetch_task(task_id, "failed", None, str(e))
                return {"status": "failed", "error": str(e)}
        
        # 使用 asyncio.run() 执行异步任务       
        return asyncio.run(async_process())
    
    except Exception as e:
        logger.error(f"任务处理外部失败: {str(e)}")
        return {"status": "error", "error": str(e)}

async def run_similar_fetcher(platform, params) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """根据平台选择合适的爬虫并运行相似用户查找"""
    fetcher = None
    
    # 根据平台创建爬虫实例
    if platform == "twitter":
        fetcher = TwitterFetcher()
    elif platform == "instagram":
        fetcher = InstagramFetcher()
    else:
        raise ValueError(f"不支持的平台: {platform}")

    try:
        username = params.get("username")
        count = params.get("count", 200)
        uid = params.get("uid")
        logger.info(f"查找与 {username} 相似的用户，数量: {count}, uid: {uid}")
        success, msg, result = await fetcher.find_similar_users(username, count, uid)
        return (success, msg, result)
    finally:
        # 清理资源
        await fetcher.cleanup()

async def run_search_fetcher(platform, params) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """根据平台选择合适的爬虫并运行用户搜索"""
    fetcher = None
    
    # 根据平台创建爬虫实例
    if platform == "twitter":
        fetcher = TwitterFetcher()
    elif platform == "instagram":
        fetcher = InstagramFetcher()
    else:
        raise ValueError(f"不支持的平台: {platform}")

    try:
        query = params.get("query")
        count = params.get("count", 200)
        logger.info(f"使用query: {query} 搜索用户, 数量: {count}")
        success, msg, result = await fetcher.find_users_by_search(query, count)
        return (success, msg, result)
    finally:
        # 清理资源
        await fetcher.cleanup()

if __name__ == '__main__':
    app.start() 