class LLMServiceError(Exception):
    """大模型服务异常基类"""
    pass

class LLMAPIError(LLMServiceError):
    """API调用错误"""
    pass

class LLMConfigError(LLMServiceError):
    """配置错误"""
    pass

class LLMRateLimitError(LLMAPIError):
    """速率限制错误"""
    pass

class LLMAuthenticationError(LLMAPIError):
    """认证错误"""
    pass