from typing import Tuple, List, Dict, Any
import logging
import asyncio
import re
import json
import random
import time
from app.fetchers.base import BaseFetcher
from playwright.async_api import Page
import urllib.parse
import aiohttp
import os
from app.core.service_discovery import ServiceDiscovery

from app.settings import settings

logger = logging.getLogger(__name__)

class InstagramFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        self.platform = "instagram"
        # 用户代理列表，模拟不同浏览器和设备
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
        # 加载 API 配置
        self._load_config()
        self.page = None
        self.browser = None
        self.logger = logger
        # 初始化时获取Instagram认证信息
        self.instagram_accounts = [
            {
                'csrfToken': 'QMCCestsU61qn124dnghm34ttsziK6l5',
                'cookie': 'ps_l=1; ps_n=1; ig_did=C9F6FC4C-4C67-491F-9620-C3F286E329C5; ig_nrcb=1; mid=ZyDt5AAEAAGHKTGYOazmdHv1MEEJ; datr=5O0gZ8Dn0ewlCn2TBfJ0b-Cr; csrftoken=QMCCestsU61qn124dnghm34ttsziK6l5; ds_user_id=3002998921; sessionid=3002998921%3AlnMf3NU621BfMl%3A8%3AAYenAosZIKeqaCoDPK4ZyCwWoDITMqVifWnvU9W22Q; wd=772x674; rur="NHA\0543002998921\0541776502501:01f7a95b22f18c128401f659c9b697ddec9b8d86145e6a317d1824cf391dff419e342d3b"',
            }
        ]  # 所有Instagram账号
        self.selected_instagram_account = self.instagram_accounts[0]
    
    def _load_config(self):
        """加载 Instagram API 配置"""
        try:
            # 加载代理配置
            proxy_config = settings.get_config('proxy', {})
            self.proxy_enabled = proxy_config.get('enabled', False)
            self.proxy_url = proxy_config.get('url', '')
            if self.proxy_enabled and self.proxy_url:
                self.logger.info(f"代理已启用: {self.proxy_url}")
            
            # 获取 Instagram API 配置
            instagram_config = settings.get_config('instagram', {})
            self.api_endpoints = instagram_config.get('endpoints', {})
            self.logger.info("成功加载 Instagram配置")
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 设置默认值
            self.api_endpoints = {}
            self.proxy_enabled = False
            self.proxy_url = ''
    
    async def _random_delay(self, min_seconds=1, max_seconds=5):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def fetch_user_profile(self, uid: str) -> Dict[str, Any]:
        """获取用户主页信息"""
        self.logger.info(f"开始获取 Instagram 用户资料, uid: {uid}")
        if not await self.select_instagram_account():
            self.logger.error("未选择Instagram账号，无法获取用户资料")
            return {}
        
        try:    
             # 构建请求 URL
            url = self.api_endpoints.get("user_by_uid", {}).get("url")
            doc_id = self.api_endpoints.get("user_by_uid", {}).get("doc_id")
            if not url:
                self.logger.error("无法获取 user_by_uid API 端点")
                return (False, "API端点未配置", [])
            
            # 准备 API 请求头
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "x-ig-app-id": "936619743392459",
                "x-csrftoken": self.selected_instagram_account.get('csrfToken', ''),
                "cookie": self.selected_instagram_account.get('cookie', ''),
            }
            
            # 准备请求参数
            variables = {
                "id": uid,
                "render_surface": "PROFILE",
            }
            
            # 准备表单数据
            form_data = {
                "doc_id": doc_id,
                "variables": json.dumps(variables)
            }
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers, "data": form_data}
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                async with session.post(url, **request_kwargs) as response:
                    response_data = await response.json()
            
            # 解析响应数据
            user_data = response_data.get("data", {}).get("user", {})
            if not user_data:
                self.logger.error("无法获取用户资料")
                return {}
            
            # 构建用户资料
            profile_data = {
                "uid":uid,
                "username": user_data.get("username", ""),
                "nickname": user_data.get("full_name", ""),
                "is_verified": user_data.get("is_verified", False),
                "followers_count": user_data.get("follower_count", 0),
                "following_count": user_data.get("following_count", 0),
                "post_count": user_data.get("media_count", 0),
                "bio": user_data.get("biography", ""),
                "url": f"https://www.instagram.com/{user_data.get('username', '')}"
            }
            
            self.logger.info(f"成功获取用户资料, uid: {uid}, username: {profile_data['username']}")
            return profile_data
            
        except asyncio.TimeoutError:
            self.logger.error(f"获取用户资料请求超时")
            return {}
        except aiohttp.ClientError as e:
            self.logger.error(f"API请求错误: {str(e)}")
            return {}
        except Exception as e:
            self.logger.error(f"获取用户资料失败: {str(e)}")
            return {}
        
    async def fetch_user_profile_id(self, username: str) -> Tuple[bool, str, str]:
        """获取用户资料ID"""
        self.logger.info(f"获取 Instagram 用户资料ID: {username}")
        
        try:
            # 构建请求 URL
            url = f"https://www.instagram.com/{username}/"
            
            # 准备请求头
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
                "Connection": "keep-alive",
                "sec-fetch-mode": "navigate",
                "cookie": self.selected_instagram_account.get('cookie', ''),
            }
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
                self.logger.info(f"使用代理: {proxy}")
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers}
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                async with session.get(url, **request_kwargs) as response:
                    self.logger.info(f"请求状态码: {response.status}")
                    if response.status != 200:
                        return (False, f"请求失败，状态码: {response.status}", "")
                    
                    html_content = await response.text()
                    
                    # 检查页面是否存在
                    if "Page Not Found" in html_content:
                        return (False, "用户不存在", "")
                    
                    # 查找所有 <script type="application/json"> 标签
                    script_pattern = r'<script type="application/json"  data-content-len="\d+" data-sjs>(.*?)</script>'
                    script_matches = re.findall(script_pattern, html_content, re.DOTALL)
                    
                    if not script_matches:
                        return (False, "未找到 JSON 数据", "")
                    # 
                    # 遍历所有 JSON 数据，查找 profile_id
                    for script_content in script_matches:
                        try:
                            # 尝试解析 JSON
                            json_data = json.loads(script_content)
                            
                            # 递归查找 profile_id
                            profile_id = self._find_profile_id(json_data)
                            if profile_id:
                                return (True, "Success", profile_id)
                        except json.JSONDecodeError:
                            continue
                    
                    # 如果上述方法失败，尝试其他方法
                    # 方法 1: 从页面中查找包含用户 ID 的 JSON 数据
                    profile_id_pattern = r'"profilePage_(\d+)"'
                    profile_id_match = re.search(profile_id_pattern, html_content)
                    if profile_id_match:
                        profile_id = profile_id_match.group(1)
                        self.logger.info(f"通过正则表达式获取用户 ID: {profile_id}")
                        return (True, "Success", profile_id)
                    
                    # 方法 2: 从页面中查找其他格式的用户 ID
                    id_pattern = r'"id":"(\d+)"'
                    id_match = re.search(id_pattern, html_content)
                    if id_match:
                        profile_id = id_match.group(1)
                        self.logger.info(f"通过正则表达式获取用户 ID: {profile_id}")
                        return (True, "Success", profile_id)
                    
                    return (False, "未找到用户 ID", "")
            
        except asyncio.TimeoutError:
            self.logger.error(f"获取用户资料ID请求超时")
            return (False, "请求超时", "")
        except aiohttp.ClientError as e:
            self.logger.error(f"请求错误: {str(e)}")
            return (False, str(e), "")
        except Exception as e:
            self.logger.error(f"获取用户资料ID失败: {str(e)}")
            return (False, str(e), "")
    
    def _find_profile_id(self, data):
        """递归查找 profile_id"""
        if isinstance(data, dict):
            # 检查当前字典中是否有 profile_id
            if "profile_id" in data:
                return data["profile_id"]
            
            # 递归检查所有值
            for value in data.values():
                result = self._find_profile_id(value)
                if result:
                    return result
        elif isinstance(data, list):
            # 递归检查列表中的所有元素
            for item in data:
                result = self._find_profile_id(item)
                if result:
                    return result
        
        return None

    async def find_similar_users(self, username: str, count: int = 20, uid: str = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """找到与指定用户相似的用户
        
        Args:
            username (str): 用户名
            count (int): 要获取的相似用户数量
            uid (str, optional): 用户ID，如果提供则使用此ID查找相似用户
        
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 是否成功获取用户资料, msg, 相似用户列表
        """
        self.logger.info(f"查找与 {username} 相似的 Instagram 用户，数量: {count}")

        if not await self.select_instagram_account():
            self.logger.error("未选择Instagram账号，无法查找相似用户")
            return (False, "未选择Instagram账号", [])
        
        if not uid:
            try:
                success, msg, uid = await self.fetch_user_profile_id(username)
                if not success:
                    self.logger.error(f"获取用户ID失败: {msg}")
                    return (False, msg, [])
            except Exception as e:
                self.logger.error(f"获取用户ID失败: {str(e)}")
                return (False, str(e), [])
        
        self.logger.info(f"获取用户ID成功: {uid}")
        
        try:
            # 用字典来存储用户ID及其出现次数，用于去重和排序
            user_frequency_map = {}
            all_similar_users = []
            
            # 步骤1: 获取第一层相似用户
            first_level_users = await self._find_similar_users_by_uid(uid)
            self.logger.info(f"获取到第一层相似用户: {len(first_level_users)} 个")

            if len(first_level_users) >= count:
                all_similar_users = first_level_users[:count]
                return (True, "success", all_similar_users)
            
            # 添加第一层用户并记录其 UID
            for user in first_level_users:
                user_uid = user["uid"]
                if user_uid not in user_frequency_map:
                    user_frequency_map[user_uid] = 1
                    all_similar_users.append(user)
                else:
                    user_frequency_map[user_uid] += 1
            
            # 步骤2: 获取第二层相似用户
            second_level_users = []
            
            # 顺序处理每个第一层用户
            for first_level_user in first_level_users:
                if first_level_user["uid"]:
                    # 顺序请求每个用户的相似用户
                    users = await self._find_similar_users_by_uid(first_level_user["uid"])
                    self.logger.info(f"获取到{first_level_user['username']}第二层相似用户: {len(users)} 个")
                    if not isinstance(users, list) or not users:  # 确保结果是有效的
                        continue
                    
                    # 更新用户频率并添加到第二层用户列表
                    for user in users:
                        user_uid = user["uid"]
                        if user_uid not in user_frequency_map:
                            user_frequency_map[user_uid] = 1
                            second_level_users.append(user)
                        else:
                            user_frequency_map[user_uid] += 1

                    if len(user_frequency_map) >= count:
                        break
                    
                    await asyncio.sleep(random.uniform(1, 3))
            
            # 根据用户出现频率排序
            sorted_users = first_level_users + sorted(second_level_users, key=lambda x: user_frequency_map.get(x["uid"], 0), reverse=True)
            
            # 确保返回数量不超过请求数量
            return (True, "success", sorted_users[:count])
            
        except Exception as e:
            self.logger.error(f"查找相似用户失败: {str(e)}")
            return (False, str(e), [])

    async def _find_similar_users_by_uid(self, uid: str) -> List[Dict[str, Any]]:
        """通过用户ID获取相似用户
        
        Args:
            uid (str): 用户ID
        
        Returns:
            List[Dict[str, Any]]: 相似用户列表
        """
        try:
            # 构建请求 URL
            url = self.api_endpoints.get("similar_users", {}).get("url")
            doc_id = self.api_endpoints.get("similar_users", {}).get("doc_id")
            if not url:
                self.logger.error("无法获取 similar_users API 端点")
                return []
            
            # 准备 API 请求头
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "x-ig-app-id": "936619743392459",
                "x-csrftoken": self.selected_instagram_account.get('csrfToken', ''),
                "cookie": self.selected_instagram_account.get('cookie', ''),
            }
            
            # 准备请求参数
            variables = {
                "module": "profile",
                "target_id": uid,
            }
            
            # 准备表单数据
            form_data = {
                "doc_id": doc_id,
                "variables": json.dumps(variables)
            }
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers, "data": form_data}
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                async with session.post(url, **request_kwargs) as response:
                    response_data = await response.json()
            
            # 解析响应数据
            similar_users = []
            users = response_data.get("data", {}).get("xdt_api__v1__discover__chaining", {}).get("users", [])
            
            for user in users:
                uid = user.get("pk", "")
                user_data = await self.fetch_user_profile(uid)
                similar_users.append(user_data)
                # await asyncio.sleep(1)
                
            return similar_users
            
        except Exception as e:
            self.logger.error(f"获取相似用户失败: {str(e)}")
            return []

    async def _get_instagram_accounts_from_admin_service(self) -> bool:
        """通过服务发现获取admin-service-http的IP和端口，然后发送POST请求获取Instagram账号
        
        Returns:
            bool: 是否成功获取账号
        """
        if self.instagram_accounts:
            return True

        try:
            self.logger.info("正在通过服务发现获取Instagram认证信息...")

            # 使用ServiceDiscovery发送POST请求到admin-service-http
            response = await ServiceDiscovery.post(
                service_name="admin-service-http",
                path="/v1/instagram/accounts/lock",
                json={}
            )
            
            # 检查响应是否成功
            if response and response.get('accounts', []) and len(response.get('accounts', [])) > 0:
                self.instagram_accounts = response.get('accounts', [])
                self.logger.info(f"成功获取Instagram账号, 数量: {len(self.instagram_accounts)}")
                return True
            else:
                self.logger.error(f"获取Instagram账号失败: 响应格式不正确")
                return False
                
        except Exception as e:
            self.logger.error(f"获取Instagram账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    async def select_instagram_account(self) -> bool:
        """选择一个Instagram账号
        
        Returns:
            bool: 是否成功选择账号
        """
        try:
            # 如果已经有认证信息，则不需要重新获取
            if self.selected_instagram_account:
                # self.logger.info("已有Instagram账号，无需重新获取")
                return True
                
            # 从admin-service-http获取认证信息
            await self._get_instagram_accounts_from_admin_service()
            if self.instagram_accounts:
                self.selected_instagram_account = self.instagram_accounts[0]
                self.logger.info(f"成功选择Instagram账号: {self.selected_instagram_account.get('username')}")
                return True
            else:
                self.logger.error("获取Instagram账号失败")
                return False
                
        except Exception as e:
            self.logger.error(f"选择Instagram账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        
    async def _clear_instagram_accounts(self) -> bool:
        """清理Instagram账号"""
        if not self.instagram_accounts:
            return True
        try:
            ids = [account.get("id") for account in self.instagram_accounts]
            # 使用ServiceDiscovery发送POST请求到admin-service-http
            response = await ServiceDiscovery.post(
                service_name="admin-service-http",
                path="/v1/instagram/accounts/unlock",
                json={"ids": ids}
            )
            if response.get("success", False):
                self.instagram_accounts = []
                self.logger.info("成功清理Instagram账号")
                return True
            else:
                self.logger.error("清理Instagram账号失败")
                return False
        
        except Exception as e:
            self.logger.error(f"清理Instagram账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        # self.logger.info("清理Instagram账号...")
        # await self._clear_instagram_accounts()
        self.selected_instagram_account = {}
        self.logger.info("资源清理完成") 