from typing import Dict, Any, Optional
import logging
from app.core.distributed_ratelimiter import DistributedRateLimiter

class LLMRateLimiter:
    """大模型API限流器
    
    使用分布式限流器实现对不同模型的请求限流
    """
    
    def __init__(self, provider: str, model: str, config: Dict[str, Any]):
        """初始化限流器
        
        Args:
            provider: 提供商名称，如'grok'、'openai'
            model: 模型名称，如'grok-3'、'gpt-4o'
            config: 限流配置，包含rate_limits字段
        """
        self.provider = provider
        self.model = model
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 获取模型限流配置
        rate_limits = config.get("rate_limits", {})
        model_rate_limit = rate_limits.get(model)
        
        if model_rate_limit is None:
            # 如果没有特定模型的限流配置，使用默认限流
            default_rate_limit = rate_limits.get("default", 1.0)
            self.limiter = DistributedRateLimiter(
                key=f"llm:{provider}:default",
                rate_per_sec=default_rate_limit
            )
            self.logger.info(f"使用默认限流配置: {default_rate_limit} 请求/秒")
        else:
            # 使用特定模型的限流配置
            self.limiter = DistributedRateLimiter(
                key=f"llm:{provider}:{model}",
                rate_per_sec=model_rate_limit
            )
            self.logger.info(f"模型 {model} 限流配置: {model_rate_limit} 请求/秒")
    
    async def acquire(self):
        """获取令牌，如果超过限流则等待"""
        await self.limiter.acquire()
    
    async def close(self):
        """关闭限流器"""
        await self.limiter.close()