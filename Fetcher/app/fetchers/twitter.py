from typing import List, Dict, Any
import logging
import asyncio
import re
import json
from app.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)

class TwitterFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        self.platform = "twitter"
    
    async def fetch_user_profile(self, username: str) -> Dict[str, Any]:
        """获取用户主页信息"""
        self.logger.info(f"获取 Twitter 用户资料: {username}")
        
        try:
            await self.page.goto(f"https://x.com/{username}")
            # 修改等待条件为 'attached'，因为script元素通常是隐藏的
            await self.page.wait_for_selector(
                'script[data-testid="UserProfileSchema-test"]',
                state='attached',  # 改为 attached 而不是默认的 visible
                timeout=10000
            )
            
            # 获取JSON数据
            json_content = await self.page.eval_on_selector(
                'script[data-testid="UserProfileSchema-test"]',
                'element => element.textContent'
            )
            profile_json = json.loads(json_content)
            main_entity = profile_json.get('mainEntity', {})
            
            # 从统计数据中获取关注者、关注数和推文数
            interaction_stats = {
                stat['name']: stat['userInteractionCount']
                for stat in main_entity.get('interactionStatistic', [])
            }
            
            profile_data = {
                "platform": self.platform,
                "username": main_entity.get('additionalName', ''),
                "nickname": main_entity.get('givenName', ''),
                "is_verified": bool(main_entity.get('disambiguatingDescription') == 'X'),
                "followers_count": interaction_stats.get('Follows', 0),
                "following_count": interaction_stats.get('Friends', 0),
                "tweet_count": interaction_stats.get('Tweets', 0),
                "bio": main_entity.get('description', ''),
                "location": main_entity.get('homeLocation', {}).get('name', ''),
                "url": main_entity.get('url', ''),
            }
            
            self.logger.info(f"成功获取用户资料: {username}")
            return profile_data
            
        except Exception as e:
            self.logger.error(f"获取用户资料失败 {username}: {str(e)}")
            raise
    
    async def find_similar_users(self, username: str, count: int = 5) -> List[Dict[str, Any]]:
        """找到与指定用户相似的用户"""
        self.logger.info(f"查找与 {username} 相似的 Twitter 用户，数量: {count}")
        
        try:
            # 模拟获取推荐用户列表
            similar_users = []
            for i in range(count):
                similar_users.append({
                    "username": f"similar_user_{i}",
                    "display_name": f"Similar User {i}",
                    "follower_count": 800 + i * 100,
                    "following_count": 400 + i * 50,
                    "tweet_count": 150 + i * 10,
                    "bio": f"Similar user {i} to {username}",
                    "similarity": 0.9 - (i * 0.1)  # 模拟相似度
                })
            
            self.logger.info(f"成功找到 {len(similar_users)} 个相似用户")
            return similar_users
            
        except Exception as e:
            self.logger.error(f"查找相似用户失败: {str(e)}")
            return [] 