import consul
import yaml
import logging
from pathlib import Path

from app.settings import settings

logger = logging.getLogger(__name__)

class ConsulClient:
    def __init__(self):
        self.consul = None
        self.service_config = settings.get_config("consul", {}).get("service", {})
        self.consul_config = settings.get_config("consul", {}).get("server", {})
        self._init_consul()

    def _init_consul(self):
        self.consul = consul.Consul(
            host=self.consul_config["host"],
            port=self.consul_config["port"],
            scheme=self.consul_config["scheme"],
            token=self.consul_config["token"],
            dc=self.consul_config["datacenter"]
        )

    def register_service(self):
        """注册服务到 Consul"""
        try:
            self.consul.agent.service.register(
                name=self.service_config["name"],
                service_id=self.service_config["id"],
                address=self.service_config["address"],
                port=self.service_config["port"],
                tags=self.service_config["tags"],
                meta=self.service_config["meta"],
                check=self.service_config["check"],
                token=self.service_config["token"]
            )
            logger.info(f"Service {self.service_config['name']} registered successfully")
        except Exception as e:
            logger.error(f"Failed to register service: {str(e)}")
            raise

    def deregister_service(self):
        """从 Consul 注销服务"""
        try:
            self.consul.agent.service.deregister(self.service_config["id"])
            logger.info(f"Service {self.service_config['name']} deregistered successfully")
        except Exception as e:
            logger.error(f"Failed to deregister service: {str(e)}")
            raise

    def get_service(self, service_name):
        """获取服务信息"""
        try:
            index, data = self.consul.health.service(service_name, passing=True)
            return data
        except Exception as e:
            logger.error(f"Failed to get service {service_name}: {str(e)}")
            raise 

# 创建全局 Consul 实例
consul_client = ConsulClient()