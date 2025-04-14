import logging
from playwright.async_api import async_playwright

class BaseFetcher:
    """所有爬虫的基类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.browser = None
        self.context = None
        self.page = None
    
    async def setup_browser(self):
        """设置浏览器"""
        self.logger.info("设置浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.logger.info("浏览器设置完成")
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("清理资源...")
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        self.logger.info("资源清理完成")
    
    async def fetch_user_profile(self, username):
        """获取用户资料 - 子类需要实现"""
        raise NotImplementedError("子类必须实现 fetch_user_profile 方法")
    
    async def find_similar_users(self, username, count=5):
        """查找相似用户 - 子类需要实现"""
        raise NotImplementedError("子类必须实现 find_similar_users 方法") 