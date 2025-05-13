import logging
from typing import Optional, Dict, Any, Callable
from fastapi import FastAPI

from app.settings import settings, get_settings

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器，负责从Nacos加载配置并实现热加载"""
    
    def __init__(self):
        self.settings = get_settings()
        self._config_callbacks = []
    
    def initialize(self):
        """初始化配置管理器，不依赖FastAPI"""
        if not self.settings.get_nacos_enabled():
            logger.info("Nacos is disabled, using local configuration only")
            return
        
        try:
            # 初始化 Nacos 服务
            # if not nacos_client.get_is_initialized():
            #     logger.warning("Failed to initialize Nacos service, using local configuration only")
            #     return
            
            # 应用启动时，从Nacos获取最新配置并更新本地文件
            # self._fetch_and_update_config()
            
            # 添加配置变更监听
            # self._setup_config_watcher()
            
            logger.info("Configuration manager initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing configuration manager: {e}")
            logger.warning("Using local configuration only")
    
    def _fetch_and_update_config(self):
        """从Nacos获取最新配置并更新本地文件"""
        # if not nacos_client.get_is_initialized():
        #     logger.warning("Nacos client not initialized, cannot fetch config")
        #     return
        
        try:
            # 从Nacos获取最新配置
            # config_str = nacos_client.get_config(
            #     data_id=self.settings.get_nacos_config("nacos", {}).get("data_id", ""),
            #     group=self.settings.get_nacos_config("nacos", {}).get("group", "DEFAULT_GROUP")
            # )
            
            # if not config_str:
            #     logger.warning("No config retrieved from Nacos")
            #     return
            
            logger.info("Successfully fetched config from Nacos at startup")
            
            # 更新本地配置文件
            # self._update_local_config_file(config_str)
            
            # 更新设置对象
            # self.settings.update_config(config_str)
            # logger.info("Configuration initialized from Nacos successfully")
            
        except Exception as e:
            logger.error(f"Error fetching and updating config at startup: {e}")
    
    # def _setup_config_watcher(self):
    #     """设置配置变更监听器"""
    #     if not nacos_client.get_is_initialized():
    #         return
            
    #     def config_change_handler(config):
    #         logger.info("Received configuration update from Nacos")
            
    #         # 更新本地配置文件
    #         self._update_local_config_file(config)
            
    #         # 更新设置对象
    #         self.settings.update_config(config)
            
    #         # 触发所有注册的回调
    #         for callback in self._config_callbacks:
    #             try:
    #                 callback(config)
    #             except Exception as e:
    #                 logger.error(f"Error in config change callback: {e}")
                    
    #         logger.info("Configuration hot-reloaded successfully")
            
        # # 添加配置变更监听
        # nacos_client.add_config_watcher(config_change_handler)
    
    def register_config_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注册配置变更回调函数"""
        if callback not in self._config_callbacks:
            self._config_callbacks.append(callback)
            logger.info("Config change callback registered")
    
    def unregister_config_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注销配置变更回调函数"""
        if callback in self._config_callbacks:
            self._config_callbacks.remove(callback)
            logger.info("Config change callback unregistered")
    
    def _update_local_config_file(self, config_str: str):
        """将配置更新到本地文件"""
        try:
            path = self.settings.config_path
            
            # 使用settings中的方法保存配置
            if self.settings.save_config_to_file(config_str):
                logger.info(f"Local config file {path} updated successfully")
                return True
            else:
                logger.warning("Failed to update local config file")
                return False
        except Exception as e:
            logger.error(f"Error updating local config file: {e}")
            return False

# 创建配置管理器实例
config_manager = ConfigManager() 