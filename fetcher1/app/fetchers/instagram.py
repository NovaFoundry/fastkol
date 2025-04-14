from app.fetchers.base import BaseFetcher

class InstagramFetcher(BaseFetcher):
    def __init__(self, proxy_pool=None, account_manager=None):
        super().__init__(proxy_pool, account_manager)
        self.platform = "instagram"
    
    async def fetch_user_profile(self, username):
        """获取 Instagram 用户资料"""
        self.logger.info(f"获取 Instagram 用户资料: {username}")
        
        # 模拟返回数据
        return {
            "username": username,
            "display_name": f"{username.capitalize()}",
            "followers": 3000,
            "following": 500,
            "posts": 120
        }
    
    async def find_similar_users(self, username, count=5):
        """查找与指定用户相似的 Instagram 用户"""
        self.logger.info(f"查找与 {username} 相似的 Instagram 用户，数量: {count}")
        
        # 模拟返回数据
        similar_users = []
        for i in range(count):
            similar_users.append({
                "username": f"similar_insta_{i}",
                "display_name": f"Similar Insta {i}",
                "followers": 2500 + i * 150,
                "following": 450 + i * 20,
                "posts": 100 + i * 10
            })
        
        return similar_users 