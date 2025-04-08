import logging
import time
import random
import asyncio
from typing import Dict, List, Optional
from app.settings import settings

logger = logging.getLogger(__name__)

class ProxyPool:
    """代理池管理类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.proxies = []
        self.blacklist = set()
        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """初始化代理池"""
        await self.update_proxies()
        
    async def update_proxies(self):
        """从配置中加载代理列表"""
        async with self.lock:
            try:
                # 从配置中加载代理，而不是数据库或API
                self.proxies = []
                
                # 检查settings中是否有PROXIES配置
                if hasattr(settings, 'PROXIES') and settings.PROXIES:
                    for proxy in settings.PROXIES:
                        if f"{proxy['host']}:{proxy['port']}" not in self.blacklist:
                            self.proxies.append(proxy)
                
                logger.info(f"代理池更新完成，当前可用代理数: {len(self.proxies)}")
            except Exception as e:
                logger.error(f"更新代理池失败: {str(e)}")
                
    async def get_proxy(self):
        """获取一个代理"""
        if not self.proxies:
            self.logger.warning("代理池为空，返回 None")
            return None
        
        proxy = random.choice(self.proxies)
        self.logger.info(f"使用代理: {proxy}")
        return proxy
    
    async def report_proxy_status(self, proxy, success):
        """报告代理状态"""
        if success:
            self.logger.info(f"代理 {proxy} 工作正常")
        else:
            self.logger.warning(f"代理 {proxy} 工作异常")
            # 将失败的代理加入黑名单
            if proxy:
                proxy_id = f"{proxy['host']}:{proxy['port']}"
                self.blacklist.add(proxy_id)
                
                # 从可用列表中移除
                self.proxies = [p for p in self.proxies if f"{p['host']}:{p['port']}" != proxy_id] 