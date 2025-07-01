from typing import Dict, Any, List, Optional, Union
import aiohttp
import json
import asyncio
import logging
from openai import AsyncOpenAI, DefaultHttpxClient
from .base import BaseLLMService
from .exceptions import LLMServiceError, LLMRateLimitError
from .ratelimiter import LLMRateLimiter

class GrokService(BaseLLMService):
    """Grok大模型服务实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Grok服务
        
        Args:
            config: 配置字典，包含API密钥等信息
        """
        super().__init__(config)
        
        # 获取代理配置
        proxy = config.get("proxy")
        
        # 创建HTTP客户端
        http_client = None
        if proxy:
            self.logger.info(f"使用代理: {proxy}")
            http_client = DefaultHttpxClient(proxy=proxy)
        
        # 获取超时设置（秒）
        timeout_seconds = config.get("timeout", 60)
        
        self.client = AsyncOpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("api_base"),
            timeout=timeout_seconds,  # 直接使用浮点数表示秒数
            max_retries=config.get("max_retries", 3),
            http_client=http_client
        )
        self.default_model = config.get("model", "grok-1")
        self.logger.info(f"Grok服务初始化完成，默认模型: {self.default_model}")
        
        # 初始化模型限流器缓存
        self.rate_limiters = {}
    
    def _get_rate_limiter(self, model: str) -> LLMRateLimiter:
        """获取或创建模型限流器
        
        Args:
            model: 模型名称
            
        Returns:
            LLMRateLimiter: 限流器实例
        """
        if model not in self.rate_limiters:
            self.rate_limiters[model] = LLMRateLimiter("grok", model, self.config)
        return self.rate_limiters[model]
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成聊天完成响应
        
        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "Hello"}]
            model: 模型名称，如果为None则使用配置中的默认模型
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 模型响应
        """
        try:
            # 使用默认值或配置中的值
            _model = model or self.default_model
            _temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)
            _max_tokens = max_tokens or self.config.get("max_tokens", 1000)
            
            # 获取并应用限流
            rate_limiter = self._get_rate_limiter(_model)
            await rate_limiter.acquire()
            
            self.logger.debug(f"发送请求到Grok API，模型: {_model}, 温度: {_temperature}")
            
            response = await self.client.chat.completions.create(
                model=_model,
                messages=messages,
                temperature=_temperature,
                max_tokens=_max_tokens,
                **kwargs
            )
            
            return response.model_dump()
            
        except asyncio.TimeoutError as e:
            self.logger.error(f"Grok API请求超时: {str(e)}")
            raise LLMServiceError(f"Grok API请求超时: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                self.logger.error(f"Grok API速率限制错误: {error_msg}")
                raise LLMRateLimitError(f"Grok API速率限制错误: {error_msg}")
            self.logger.error(f"Grok API调用失败: {error_msg}")
            raise LLMServiceError(f"Grok API调用失败: {error_msg}")
    
    async def embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成文本嵌入向量
        
        Args:
            texts: 单个文本或文本列表
            model: 模型名称，如果为None则使用配置中的默认嵌入模型
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 包含嵌入向量的响应
        """
        try:
            # 处理输入，确保texts是列表
            input_texts = [texts] if isinstance(texts, str) else texts
            
            # 使用默认嵌入模型或指定模型
            _model = model or self.config.get("embedding_model", "grok-1")
            
            # 获取并应用限流
            rate_limiter = self._get_rate_limiter(_model)
            await rate_limiter.acquire()
            
            response = await self.client.embeddings.create(
                model=_model,
                input=input_texts,
                **kwargs
            )
            
            return response.model_dump()
            
        except asyncio.TimeoutError as e:
            self.logger.error(f"Grok嵌入API请求超时: {str(e)}")
            raise LLMServiceError(f"Grok嵌入API请求超时: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                self.logger.error(f"Grok嵌入API速率限制错误: {error_msg}")
                raise LLMRateLimitError(f"Grok嵌入API速率限制错误: {error_msg}")
            self.logger.error(f"Grok嵌入API调用失败: {error_msg}")
            raise LLMServiceError(f"Grok嵌入API调用失败: {error_msg}")
    
    async def close(self) -> None:
        """关闭客户端连接，释放资源"""
        # 关闭所有限流器
        for limiter in self.rate_limiters.values():
            await limiter.close()
        
        # 关闭API客户端
        self.logger.info("关闭Grok服务连接")
        await self.client.close()