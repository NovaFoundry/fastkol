import os
import logging
from typing import Any, Dict, Optional, Callable
import yaml
import nacos
from fastapi import FastAPI
from app.settings import settings

logger = logging.getLogger(__name__)

class NacosClient:
    def __init__(self):
        """初始化 Nacos 客户端"""
        self.client = None
        self.config = None
        self.service_config = {}
        self.config_callbacks = []
        self._config_callbacks = []
        
        # 如果 Nacos 未启用，直接返回
        if not settings.get_nacos_enabled():
            logger.info("Nacos is disabled, skipping initialization")
            return
            
        try:            
            # 初始化 Nacos 客户端
            nacos_config = settings.get_nacos_config().get('nacos')
            self.client = nacos.NacosClient(
                server_addresses=nacos_config['server_addr'],
                namespace=nacos_config['namespace'],
                username=nacos_config['username'],
                password=nacos_config['password'],
            )
            logger.info("Successfully connected to Nacos server")
        except Exception as e:
            logger.error(f"Failed to initialize Nacos client: {e}")
            
    def register_service(self) -> bool:
        """注册服务到 Nacos"""
        if not self.client or not settings.get_nacos_enabled():
            return False
            
        try:
            service_config = settings.get_nacos_config().get('service')
            self.client.add_naming_instance(
                service_name=service_config['name'],
                ip=service_config['ip'],
                port=service_config['port'],
                weight=service_config['weight'],
                cluster_name=service_config['cluster_name'],
                group_name=service_config['group_name'],
                ephemeral=service_config['ephemeral'],
                heartbeat_interval=service_config.get('heartbeat_interval', 5)
            )
            logger.info(f"Successfully registered service {service_config['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to register service: {e}")
            return False
            
    def deregister_service(self) -> bool:
        """从 Nacos 注销服务"""
        if not self.client or not settings.get_nacos_enabled():
            return False
            
        try:
            service_config = settings.get_nacos_config().get('service')
            self.client.remove_naming_instance(
                service_name=service_config['name'],
                ip=service_config['ip'],
                port=service_config['port']
            )
            logger.info(f"Successfully deregistered service {service_config['name']}")
            return True
        except Exception as e:
            logger.error(f"Failed to deregister service: {e}")
            return False
            
    def get_service_instances(self, service_name: str) -> list:
        """获取服务实例列表"""
        if not self.client or not settings.get_nacos_enabled():
            return []
            
        try:
            return self.client.list_naming_instance(service_name)
        except Exception as e:
            logger.error(f"Failed to get service instances: {e}")
            return []
            
    def get_config(self, data_id: str, group: str = "DEFAULT_GROUP") -> str:
        """获取配置"""
        if not self.client or not settings.get_nacos_enabled():
            return ""
            
        try:
            config_str = self.client.get_config(data_id, group)
            return config_str
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return ""
            
    def add_config_watcher(self, data_id: str, group: str, callback: Callable):
        """添加配置变更监听器"""
        if not self.client or not settings.get_nacos_enabled():
            return
            
        try:
            self.client.add_config_watcher(data_id, group, callback)
            self._config_callbacks.append((data_id, group, callback))
            logger.info(f"Added config watcher for {data_id}")
        except Exception as e:
            logger.error(f"Failed to add config watcher: {e}")
            
    def remove_config_watcher(self, data_id: str, group: str, callback: Callable):
        """移除配置变更监听器"""
        if not self.client or not settings.get_nacos_enabled():
            return
            
        try:
            self.client.remove_config_watcher(data_id, group, callback)
            self._config_callbacks.remove((data_id, group, callback))
            logger.info(f"Removed config watcher for {data_id}")
        except Exception as e:
            logger.error(f"Failed to remove config watcher: {e}")

    def get_is_initialized(self) -> bool:
        """获取 Nacos 是否已初始化"""
        return self.client is not None

# 创建全局 Nacos 实例
nacos_client = NacosClient() 