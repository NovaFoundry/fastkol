import consul
import yaml
import logging
from pathlib import Path
import socket
import psutil

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
            # token=self.consul_config["token"],
            dc=self.consul_config["datacenter"]
        )

    def _get_lan_ip(self, interface_name="eth0"):
        """优先获取指定网卡（如eth0）的IP地址，若失败则回退为自动探测"""
        try:
            addrs = psutil.net_if_addrs()
            if interface_name in addrs:
                for snic in addrs[interface_name]:
                    if snic.family.name == "AF_INET":
                        return snic.address
        except Exception as e:
            logger.error(f"Failed to get IP from {interface_name}: {e}")
        # 回退为原有自动探测
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.error(f"Failed to get LAN IP: {e}")
            return "127.0.0.1"

    def register_service(self):
        """注册服务到 Consul"""
        try:
            address = self.service_config.get("address")
            if self.service_config.get("address") == "0.0.0.0":
                address = self._get_lan_ip()
            self.consul.agent.service.register(
                name=self.service_config["name"],
                service_id=self.service_config["id"],
                address=address,
                port=self.service_config["port"],
                tags=self.service_config["tags"],
                meta=self.service_config["meta"],
                check=self.service_config["check"],
                token=self.consul_config["token"]
            )
            logger.info(f"Service {self.service_config['name']} registered successfully with address {address}")
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