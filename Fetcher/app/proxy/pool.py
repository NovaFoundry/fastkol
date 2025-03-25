import logging
import time
import random
import asyncio
import aiohttp
from typing import Dict, List, Optional
from app.config import settings
from app.db.models import Proxy

logger = logging.getLogger(__name__)

class ProxyPool:
    """代理池管理类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.proxies = []
        self.blacklist = set()
        self.last_update = 0
        self.update_interval = 300  # 5分钟更新一次
        self.lock = asyncio.Lock()
        
    async def initialize(self):
        """初始化代理池"""
        await self.update_proxies()
        
    async def update_proxies(self):
        """从数据库或API更新代理列表"""
        async with self.lock:
            try:
                # 从数据库加载代理
                from app.db.operations import get_all_proxies
                db_proxies = await get_all_proxies()
                
                # 定期从Gateway API获取新的代理信息
                if time.time() - self.last_update > self.update_interval:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(
                                f"{settings.GATEWAY_URL}/api/v1/resources/proxies",
                                headers={"Authorization": f"Bearer {settings.API_TOKEN}"}
                            ) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    api_proxies = data.get("data", [])
                                    
                                    # 合并代理列表
                                    seen_hosts = {p["host"] for p in db_proxies}
                                    for api_proxy in api_proxies:
                                        if api_proxy["host"] not in seen_hosts:
                                            db_proxies.append(api_proxy)
                    except Exception as e:
                        logger.error(f"从Gateway获取代理失败: {str(e)}")
                
                # 过滤掉黑名单代理
                self.proxies = [p for p in db_proxies if f"{p['host']}:{p['port']}" not in self.blacklist]
                self.last_update = time.time()
                
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
            # 在实际应用中，可能会将失败的代理从池中移除
            proxy_id = f"{proxy['host']}:{proxy['port']}"
            self.blacklist.add(proxy_id)
            
            # 从可用列表中移除
            self.proxies = [p for p in self.proxies if f"{p['host']}:{p['port']}" != proxy_id]
            
            # 向Gateway报告代理故障
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{settings.GATEWAY_URL}/api/v1/resources/proxies/report",
                        json={"host": proxy["host"], "port": proxy["port"], "status": "failed"},
                        headers={"Authorization": f"Bearer {settings.API_TOKEN}"}
                    )
            except Exception as e:
                logger.error(f"报告代理状态失败: {str(e)}") 