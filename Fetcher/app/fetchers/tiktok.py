from app.fetchers.base import BaseFetcher

class TiktokFetcher(BaseFetcher):
    def __init__(self, proxy_pool=None, account_manager=None):
        super().__init__(proxy_pool, account_manager)
        self.platform = "tiktok"
    
    async def fetch_user_profile(self, username):
        """获取 TikTok 用户资料"""
        self.logger.info(f"获取 TikTok 用户资料: {username}")
        
        # 模拟返回数据
        return {
            "username": username,
            "display_name": f"{username.capitalize()}",
            "followers": 10000,
            "following": 200,
            "likes": 50000
        }
    
    async def find_similar_users(self, username, count=5):
        """查找与指定用户相似的 TikTok 用户"""
        self.logger.info(f"查找与 {username} 相似的 TikTok 用户，数量: {count}")
        
        # 模拟返回数据
        similar_users = []
        for i in range(count):
            similar_users.append({
                "username": f"similar_tiktok_{i}",
                "display_name": f"Similar TikTok {i}",
                "followers": 8000 + i * 500,
                "following": 180 + i * 10,
                "likes": 40000 + i * 2000
            })
        
        return similar_users 