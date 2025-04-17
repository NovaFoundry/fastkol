import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import lru_cache
from collections import OrderedDict

# 配置日志
logger = logging.getLogger(__name__)

# 配置更新回调函数类型
ConfigChangeCallback = Callable[[Dict[str, Any]], None]

# 基本配置设置
class Settings:
    def __init__(self):
        # 查找配置文件
        self.config_path = os.environ.get('FETCHER_CONFIG', None)
        
        if not self.config_path:
            # 默认查找项目根目录下的config.yaml
            root_dir = Path(__file__).parent.parent
            self.config_path = str(root_dir / 'config' / 'config.yaml')
        
        # 加载YAML配置
        self.config = self._load_config_from_file(self.config_path)

        self.NACOS_ENABLED = self.config.get('nacos', {}).get('enabled', False)
        nacos_config_path = self.config.get('nacos', {}).get('config_file', '')
        if self.NACOS_ENABLED and nacos_config_path:
            self.nacos_config = self._load_config_from_file(nacos_config_path)
        else:
            self.nacos_config = {}

        # 更新回调函数列表
        self._change_callbacks: list[ConfigChangeCallback] = []
    
    def _load_config_from_file(self, config_path: str) -> Dict[str, Any]:
        """从文件加载配置"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return {}
    
    def update_config(self, config_str: str):
        """更新配置并触发回调"""
        self.config = yaml.safe_load(config_str)
        
        # 触发所有回调
        for callback in self._change_callbacks:
            try:
                callback(self.config)
            except Exception as e:
                logger.error(f"Error in config change callback: {e}")
    
    def register_change_callback(self, callback: ConfigChangeCallback):
        """注册配置变更回调函数"""
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)
    
    def unregister_change_callback(self, callback: ConfigChangeCallback):
        """取消注册配置变更回调函数"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def save_config_to_file(self, config: str):
        try:
            with open(self.config_path, 'w') as f:
                f.write(config)
            logger.info(f"Config saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            return False
    
    def get_config(self, key: str = None, default: Any = None) -> Any:
        """获取配置项
        
        Args:
            key: 配置键名，如果为None则返回整个配置字典
            default: 当配置项不存在时返回的默认值
            
        Returns:
            配置项的值，如果key为None则返回整个配置字典
        """
        if key is None:
            return self.config
        return self.config.get(key, default)
    
    def get_nacos_config(self, key: str = None, default: Any = None) -> Any:
        """获取Nacos配置项
        
        Args:
            key: 配置键名，如果为None则返回整个配置字典
            default: 当配置项不存在时返回的默认值
            
        Returns:
            配置项的值，如果key为None则返回整个配置字典
        """
        if key is None:
            return self.nacos_config
        return self.nacos_config.get(key, default)
    
    def get_nacos_group(self) -> str:
        """获取Nacos组名"""
        return self.nacos_config.get('service', {}).get('group_name', 'DEFAULT_GROUP')
    
    def get_nacos_enabled(self) -> bool:
        """获取Nacos是否启用"""
        return self.NACOS_ENABLED

# 创建单例设置实例
@lru_cache()
def get_settings() -> Settings:
    return Settings()

# 向后兼容的实例
settings = get_settings() 