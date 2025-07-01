from typing import Dict, Any, Optional
from app.settings import settings
from .base import BaseLLMService
from .grok import GrokService
from .exceptions import LLMServiceError

class LLMServiceFactory:
    """大模型服务工厂类，用于创建不同的LLM服务实例"""
    
    @staticmethod
    def create(provider: Optional[str] = None) -> BaseLLMService:
        """创建LLM服务实例
        
        Args:
            provider: 提供商名称，如果为None则使用配置中的默认提供商
            
        Returns:
            BaseLLMService: LLM服务实例
            
        Raises:
            LLMServiceError: 如果提供商不支持或配置错误
        """
        # 获取LLM配置
        llm_config = settings.get_config("llm", {})
        
        # 使用默认提供商或指定提供商
        provider_name = provider or llm_config.get("default_provider")
        if not provider_name:
            raise LLMServiceError("未指定LLM提供商且未配置默认提供商")
        
        # 获取提供商配置
        providers_config = llm_config.get("providers", {})
        provider_config = providers_config.get(provider_name)
        if not provider_config:
            raise LLMServiceError(f"未找到提供商 '{provider_name}' 的配置")
        
        # 合并全局设置和提供商特定设置
        global_settings = llm_config.get("settings", {})
        merged_config = {**global_settings, **provider_config}
        
        # 根据提供商创建相应的服务实例
        if provider_name.lower() == "grok":
            return GrokService(merged_config)
        elif provider_name.lower() == "openai":
            # 未来可以添加OpenAI服务实现
            # return OpenAIService(merged_config)
            raise LLMServiceError("OpenAI服务尚未实现")
        else:
            raise LLMServiceError(f"不支持的LLM提供商: {provider_name}")