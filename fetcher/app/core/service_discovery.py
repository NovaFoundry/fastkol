from typing import Optional, Dict, Any
import aiohttp
import json
from app.core.consul_client import consul_client
from app.settings import settings

class ServiceDiscovery:
    """服务发现工具类"""
    
    @staticmethod
    async def get_service_url(service_name: str, protocol: str = 'http') -> Optional[str]:
        """获取服务的基础URL
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务的基础URL
        """
        # 获取服务实例列表
        services = consul_client.get_service(service_name)
        if not services:
            return None
        # 取第一个健康实例
        service = services[0]['Service']
        if not service:
            return None
        address = service.get('TaggedAddresses', {}).get(protocol, {}).get('address')
        final_address = None
        if address:
            final_address = address
        else:
            address = service.get('Address') or service.get('ServiceAddress')
            port = service.get('Port') or service.get('ServicePort')
            if address and port:
                final_address = f"{protocol}://{address}:{port}"
        print('final_address', final_address)
        return final_address
    
    @staticmethod
    async def make_request(
        service_name: str,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """向指定服务发送请求
        
        Args:
            service_name: 服务名称
            method: HTTP方法 (GET, POST, etc.)
            path: API路径
            **kwargs: 传递给 aiohttp 的其他参数
            
        Returns:
            响应数据
            
        Raises:
            Exception: 当服务不可用或请求失败时抛出异常
        """
        base_url = await ServiceDiscovery.get_service_url(service_name)
        if not base_url:
            raise Exception(f"Service {service_name} not found")
            
        url = f"{base_url}{path}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
    
    @staticmethod
    async def get(service_name: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送GET请求
        
        Args:
            service_name: 服务名称
            path: API路径
            **kwargs: 传递给 aiohttp 的其他参数
            
        Returns:
            响应数据
        """
        return await ServiceDiscovery.make_request(service_name, "GET", path, **kwargs)
    
    @staticmethod
    async def post(service_name: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送POST请求
        
        Args:
            service_name: 服务名称
            path: API路径
            **kwargs: 传递给 aiohttp 的其他参数
            
        Returns:
            响应数据
        """
        headers = {
            "Content-Type": "application/json"
        }
        return await ServiceDiscovery.make_request(service_name, "POST", path, headers=headers, **kwargs) 