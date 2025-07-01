from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import logging

class BaseLLMService(ABC):
    """大模型服务的基础抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化大模型服务
        
        Args:
            config: 配置字典，包含API密钥等信息
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭客户端连接，释放资源"""
        pass