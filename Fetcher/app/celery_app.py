from celery import Celery
import os
import sys
import logging
import asyncio
from app.settings import settings
from app.fetchers.twitter import TwitterFetcher
from app.fetchers.youtube import YoutubeFetcher
from app.fetchers.instagram import InstagramFetcher
from app.fetchers.tiktok import TiktokFetcher
from app.proxy.pool import ProxyPool
from app.account_pool.manager import AccountManager
from app.db.operations import save_result

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
)

# 创建全局资源
proxy_pool = ProxyPool()
account_manager = AccountManager()

@app.task
def process_task(task_data):
    """处理爬虫任务"""
    try:
        task_id = task_data.get('task_id')
        platform = task_data.get('platform')
        action = task_data.get('action')
        params = task_data.get('params', {})
        
        logger.info(f"处理任务 {task_id}: {platform} 平台, {action} 操作")
        
        # 运行异步任务
        result = asyncio.run(run_fetcher(platform, action, params))
        
        # 将结果保存到数据库
        asyncio.run(save_result(task_data, result))
        
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"任务处理失败: {str(e)}")
        return {"status": "error", "error": str(e)}

async def run_fetcher(platform, action, params):
    """根据平台选择合适的爬虫并运行"""
    fetcher = None
    
    # 根据平台创建爬虫实例
    if platform == "twitter":
        fetcher = TwitterFetcher(proxy_pool, account_manager)
    elif platform == "youtube":
        fetcher = YoutubeFetcher(proxy_pool, account_manager)
    elif platform == "instagram":
        fetcher = InstagramFetcher(proxy_pool, account_manager)
    elif platform == "tiktok":
        fetcher = TiktokFetcher(proxy_pool, account_manager)
    else:
        raise ValueError(f"不支持的平台: {platform}")
    
    # 设置浏览器
    await fetcher.setup_browser()
    
    try:
        # 执行指定操作
        if action == "similar":
            username = params.get("username")
            count = params.get("count", 5)
            
            if not username:
                raise ValueError("查找相似用户需要提供用户名")
                
            results = await fetcher.find_similar_users(username, count)
            
            # 应用关注者筛选
            follows_min = params.get("follows_min")
            follows_max = params.get("follows_max")
            
            if follows_min is not None or follows_max is not None:
                filtered_results = []
                for user in results:
                    followers = user.get("followers_count", 0)
                    if (follows_min is None or followers >= follows_min) and \
                       (follows_max is None or followers <= follows_max):
                        filtered_results.append(user)
                results = filtered_results
                
            return results
            
        elif action == "profile":
            username = params.get("username")
            
            if not username:
                raise ValueError("获取用户资料需要提供用户名")
                
            result = await fetcher.fetch_user_profile(username)
            return [result]
            
        elif action == "search":
            query = params.get("query")
            count = params.get("count", 5)
            
            if not query:
                raise ValueError("搜索需要提供查询关键词")
                
            results = await fetcher.search_users(query, count)
            return results
            
        else:
            raise ValueError(f"不支持的操作: {action}")
    
    finally:
        # 清理资源
        await fetcher.cleanup()

if __name__ == '__main__':
    app.start() 