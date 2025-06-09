import asyncio
import os
import sys
import logging
import json
import traceback
from app.fetchers.twitter.twitter_v2 import TwitterFetcher
from app.fetchers.instagram import InstagramFetcher
# 添加项目根目录到 Python 路径
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, current_dir)
print(f"当前目录: {current_dir}")
print(f"Python 路径: {sys.path}")

# 配置日志 - 设置为 DEBUG 级别以获取更多信息
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_fetcher(platform, action, params):
    """测试爬虫功能"""
    fetcher = None
    
    try:
        logger.info(f"创建 {platform} 爬虫实例")
        # 根据平台创建爬虫实例
        if platform == "twitter":
            fetcher = TwitterFetcher()
        elif platform == "instagram":
            fetcher = InstagramFetcher()
        else:
            raise ValueError(f"不支持的平台: {platform}")
        
        # 执行指定操作
        if action == "find_similar_users":
            username = params.get("username")
            count = params.get("count", 200)
            uid = params.get("uid")
            logger.info(f"查找与 {username} 相似的用户，数量: {count}, uid: {uid}")
            _, _, result = await fetcher.find_similar_users(username, count, uid)
        elif action == "find_users_by_search":
            query = params.get("query")
            count = params.get("count", 20)
            logger.info(f"搜索用户: {query}, 数量: {count}")
            _, _,result = await fetcher.find_users_by_search(query, count)
        elif action == "fetch_user_profile":
            username = params.get("username")
            logger.info(f"获取用户资料: {username}")
            result = await fetcher.fetch_user_profile(username)
        elif action == "fetch_user_tweets":
            username = params.get("username")
            count = params.get("count", 50)
            uid = params.get("uid")
            logger.info(f"获取用户推文: {username}, 数量: {count}, uid: {uid}")
            _, _, _, pinned_tweets, normal_tweets = await fetcher.fetch_user_tweets(username=username, uid=uid)
            # 打印获取到的推文数量
            logger.info(f"成功获取 {len(pinned_tweets)} 条置顶推文")
            logger.info(f"成功获取 {len(normal_tweets)} 条普通推文")
            result = {
                "pinned_tweets": pinned_tweets,
                "normal_tweets": normal_tweets
            }
        elif action == "fetch_user_followings":
            username = params.get("username")
            count = params.get("count", 70)
            uid = params.get("uid")
            logger.info(f"获取用户关注: {username}, 数量: {count}, uid: {uid}")
            _, _, _, result = await fetcher.fetch_user_followings(username=username, uid=uid)
        elif action == "fetch_user_reels":
            username = params.get("username")
            count = params.get("count", 20)
            uid = params.get("uid")
            logger.info(f"获取用户Reels: {username}, 数量: {count}, uid: {uid}")
            result = await fetcher.fetch_user_reels(username, count, uid=uid)
            # 打印获取到的Reels数量
            logger.info(f"成功获取 {len(result)} 条Reels")
        else:
            raise ValueError(f"不支持的操作: {action}")
        logger.info(f"操作完成: {action}")
        return result
    
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    
    finally:
        # 清理资源
        await fetcher.cleanup()

if __name__ == "__main__":
    # 示例: 测试 Twitter 爬虫
    platform = "twitter"
    action = "fetch_user_followings"  # 修改为测试搜索用户
    params = {
        # "uid": "64325658281",
        "username": "deedydas",
        "count": 20  # 要获取的用户数量
    }
    
    logger.info(f"开始测试: 平台={platform}, 操作={action}, 参数={params}")
    
    try:
        # 运行测试
        result = asyncio.run(test_fetcher(platform, action, params))
        print(f"测试结果: {json.dumps(result, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"主程序异常: {str(e)}")
        logger.error(traceback.format_exc()) 