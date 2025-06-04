from typing import Tuple, List, Dict, Any
import logging
import asyncio
import re
import json
import random
import time
import math
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
        # 账号管理
        self.instagram_accounts = []  # 所有Instagram账号
        self.main_instagram_account = {}  # 主账号
        self.instagram_accounts_need_count = 1  # 需要获取的Instagram账号数量
        self.instagram_accounts_last_used = {}  # 所有Instagram账号上次使用时间
        self.instagram_accounts_cooldown_seconds = 5  # 所有Instagram账号冷却时间
    
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
    
    async def _extract_email_from_text(self, text: str) -> str:
        """Extract email address from text if present
        
        Args:
            text (str): Text to extract email from
            
        Returns:
            str: Extracted email or empty string if none found
        """
        if not text:
            return ""
            
        # Regular expression for email matching
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        
        if match:
            return match.group(0)
        return ""

    async def fetch_user_profile(self, uid: str) -> Tuple[bool, int, str, Dict[str, Any]]:
        """获取用户主页信息
        Args:
            uid (str): 用户ID
        Returns:
            Tuple[bool, int, str, Dict[str, Any]]: 返回(success, code, msg, profile)格式
        """
        if not await self._set_instagram_accounts():
            self.logger.error("未选择Instagram账号，无法获取用户资料")
            return False, 500, "未选择Instagram账号", {}
        try:    
             # 构建请求 URL
            url = self.api_endpoints.get("user_by_uid", {}).get("url")
            doc_id = self.api_endpoints.get("user_by_uid", {}).get("doc_id")
            if not url:
                self.logger.error("无法获取 user_by_uid API 端点")
                return False, 500, "API端点未配置", {}
            headers = self._get_headers()
            variables = {
                "id": uid,
                "render_surface": "PROFILE",
            }
            form_data = {
                "doc_id": doc_id,
                "variables": json.dumps(variables)
            }
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers, "data": form_data}
                if proxy:
                    request_kwargs["proxy"] = proxy
                async with session.post(url, **request_kwargs) as response:
                    if self.is_suspended_redirect(response):
                        self.logger.error(f"请求被重定向到账号挂起页面: {response.url}")
                        await self.handle_suspended_account()
                        return False, 403, "账号被挂起", {}
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Instagram API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return False, response.status, f"API返回非200: {response.status}", {}
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}")
                        return False, 500, f"Content-Type错误: {content_type}", {}
                    response_data = await response.json()
            
            # 解析响应数据
            user_data = response_data.get("data", {}).get("user", {})
            if not user_data:
                self.logger.error("无法获取用户资料")
                return False, 404, "未获取到用户资料", {}
            
            # 获取用户简介
            bio = user_data.get("biography", "")
            
            # 从简介中提取邮箱
            email_in_bio = await self._extract_email_from_text(bio)
            
            # 构建用户资料
            profile_data = {
                "uid":uid,
                "username": user_data.get("username", ""),
                "nickname": user_data.get("full_name", ""),
                "is_verified": user_data.get("is_verified", False),
                "followers_count": user_data.get("follower_count", 0),
                "following_count": user_data.get("following_count", 0),
                "post_count": user_data.get("media_count", 0),
                "bio": bio,
                "email_in_bio": email_in_bio,
                "url": f"https://www.instagram.com/{user_data.get('username', '')}"
            }
            return True, 200, "success", profile_data
            
        except asyncio.TimeoutError:
            self.logger.error(f"获取用户资料请求超时")
            return False, 504, "请求超时", {}
        except aiohttp.ClientError as e:
            self.logger.error(f"API请求错误: {str(e)}")
            return False, 502, f"API请求错误: {str(e)}", {}
        except Exception as e:
            self.logger.error(f"获取用户资料失败: {str(e)}")
            return False, 500, f"获取用户资料失败: {str(e)}", {}
        
    async def fetch_user_profile_id(self, username: str) -> Tuple[bool, str, str]:
        """获取用户资料ID"""
        self.logger.info(f"获取 Instagram 用户资料ID: {username}")
        
        try:
            # 构建请求 URL
            url = f"https://www.instagram.com/{username}/"
            
            # 准备请求头
            headers = self._get_headers()
            
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
        """找到与指定用户相似的用户（包括二度关系用户，第一层不直接返回，始终尝试补全第二层）
        
        Args:
            username (str): 用户名
            count (int): 要获取的相似用户数量
            uid (str, optional): 用户ID，如果提供则使用此ID查找相似用户
        
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 是否成功获取用户资料, msg, 相似用户列表
        """
        self.logger.info(f"查找与 {username} 相似的 Instagram 用户，数量: {count}")

        if not await self._set_instagram_accounts():
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
        
        result_users = []
        try:
            # 用集合来存储已处理的用户ID，用于去重
            processed_uids = set()
            all_similar_users = []
            
            # 步骤1: 获取第一层相似用户
            first_level_users = await self._find_similar_users_by_uid(uid)
            self.logger.info(f"获取到第一层相似用户: {len(first_level_users)} 个")
            processed_uids = set(user["uid"] for user in first_level_users)
            all_similar_users = first_level_users

            # 步骤2: 获取第二层相似用户
            second_level_users = []
            if len(first_level_users) < count:
                for first_level_user in first_level_users:
                    if first_level_user["uid"]:
                        users = await self._find_similar_users_by_uid(first_level_user["uid"])
                        self.logger.info(f"获取到{first_level_user['username']}第二层相似用户: {len(users)} 个")
                        if not isinstance(users, list) or not users:
                            continue
                        for user in users:
                            user_uid = user["uid"]
                            if user_uid and user_uid not in processed_uids:
                                processed_uids.add(user_uid)
                                all_similar_users.append(user)
                        if len(all_similar_users) >= count:
                            break
                        await asyncio.sleep(random.uniform(1, 3))

            result_users = all_similar_users[:count]
            for user in result_users:
                success, code, msg, reels = await self.fetch_user_reels(user["username"], 15, user["uid"])
                if not success or not reels:
                    self.logger.error(f"获取用户 {user.get('username')} reels失败, code: {code}, msg: {msg}, reels count: {len(reels)}")
                    user["avg_play_last_10_reels"] = None
                else:
                    user["avg_play_last_10_reels"] = await self._calculate_avg_views(reels)
            return (True, "success", result_users)
        
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
            headers = self._get_headers()
            
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
                    if self.is_suspended_redirect(response):
                        self.logger.error(f"请求被重定向到账号挂起页面: {response.url}")
                        await self.handle_suspended_account()
                        return []
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Instagram API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return []
                    # 校验 Content-Type
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}")
                        return []
                    response_data = await response.json()
            
            # 解析响应数据
            similar_users = []
            users = response_data.get("data", {}).get("xdt_api__v1__discover__chaining", {}).get("users", [])
            
            for user in users:
                uid = user.get("pk", "")
                success, code, msg, user_data = await self.fetch_user_profile(uid)
                if not success or not user_data:
                    self.logger.error(f"获取用户 {user.get('username')} 资料失败, code: {code}, msg: {msg}")
                    continue
                similar_users.append(user_data)
                # await asyncio.sleep(1)
                
            return similar_users
            
        except Exception as e:
            self.logger.error(f"获取相似用户失败: {str(e)}")
            return []

    def is_suspended_redirect(self, response) -> bool:
        """判断是否被重定向到 Instagram suspended 页面"""
        return str(response.url).startswith("https://www.instagram.com/accounts/suspended")

    def _get_headers(self, instagram_account: dict = None) -> Dict[str, str]:
        """获取请求头"""
        account = instagram_account if instagram_account else self.main_instagram_account
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "x-ig-app-id": "936619743392459",
            "x-csrftoken": account.get('headers', {}).get('x-csrftoken', ''),
            "cookie": account.get('headers', {}).get('cookie', ''),
        }

    async def _get_instagram_accounts_from_admin_service(self, count: int = 1) -> list:
        """通过服务发现获取admin-service-http的IP和端口，然后发送POST请求获取Instagram账号
        Args:
            count (int): 账号数量，默认为 1
        Returns:
            list: 账号列表，失败时返回空列表
        """
        try:
            self.logger.info(f"正在通过服务发现获取Instagram认证信息... count={count}")
            response = await ServiceDiscovery.post(
                service_name="admin",
                path="/v1/instagram/accounts/lock",
                json={"count": count}
            )
            if response and response.get('accounts', []) and len(response.get('accounts', [])) > 0:
                self.logger.info(f"成功获取Instagram账号, 数量: {len(response.get('accounts', []))}")
                return response.get('accounts', [])
            else:
                self.logger.error(f"获取Instagram账号失败: 响应格式不正确")
                return []
        except Exception as e:
            self.logger.error(f"获取Instagram账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []

    async def _set_instagram_accounts(self) -> bool:
        """设置Instagram账号"""
        try:
            if self.instagram_accounts:
                return True
            self.instagram_accounts = await self._get_instagram_accounts_from_admin_service(self.instagram_accounts_need_count)
            if self.instagram_accounts:
                self.main_instagram_account = self.instagram_accounts[0]
                self.logger.info(f"成功获取Instagram账号, 数量: {len(self.instagram_accounts)}, 主账号: {self.main_instagram_account.get('username', '')}")
                return True
            else:
                self.logger.error("获取Instagram账号失败")
                return False
        except Exception as e:
            self.logger.error(f"设置Instagram账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    async def _clear_instagram_accounts(self) -> bool:
        """清理Instagram账号"""
        if not self.instagram_accounts:
            return True
        try:
            ids = [account.get("id") for account in self.instagram_accounts]
            response = await ServiceDiscovery.post(
                service_name="admin",
                path="/v1/instagram/accounts/unlock",
                json={"ids": ids}
            )
            if response.get("success", False):
                self.instagram_accounts = []
                self.main_instagram_account = {}
                self.instagram_accounts_last_used = {}
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
        await self._clear_instagram_accounts()
        self.main_instagram_account = {}
        self.logger.info("资源清理完成") 

    async def find_users_by_search(self, query: str, count: int = 20) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """搜索用户
        
        Args:
            query (str): 搜索关键词
            count (int): 要获取的用户数量
            
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 成功状态，msg，用户列表
        """
        self.logger.info(f"搜索用户: {query}, 数量: {count}")
        
        if not await self._set_instagram_accounts():
            self.logger.error("未选择Instagram账号，无法搜索用户")
            return (False, "未选择Instagram账号", []) 
        
        result_users = []
        try:
            # 存储所有获取的用户
            all_users = []
            # 用于去重的用户ID集合
            processed_uids = set()
            # 记录连续没有新数据的次数
            no_new_data_count = 0
            # 上一次获取的用户数量
            last_user_count = 0

            rank_token = None
            next_max_id = None
            
            self.logger.info(f"获取用户: {len(processed_uids)}/{count}")
            # 循环获取用户，直到达到请求的数量或没有更多用户
            while len(processed_uids) < count:
                # 使用新的方法获取用户
                users, rank_token, next_max_id = await self._find_users_by_search(query, rank_token, next_max_id)

                for user in users:
                    uid = user.get("uid")
                    if uid and uid not in processed_uids:
                        processed_uids.add(uid)
                        all_users.append(user)

                self.logger.info(f"获取用户: {len(processed_uids)}/{count}")

                if len(processed_uids) == last_user_count:
                    no_new_data_count += 1
                else:
                    no_new_data_count = 0
                    last_user_count = len(processed_uids)
                
                # 如果已经达到请求的数量，退出循环
                if len(all_users) >= count:
                    break

                if no_new_data_count >= 3:
                    self.logger.info("连续3次没有获取到新数据，停止搜索")
                    break
                
                # 添加随机延迟，避免请求过于频繁
                await self._random_delay(2, 5)
            
            # 确保返回数量不超过请求数量
            result_users = all_users[:count]
            for user in result_users:
                success, code, msg, reels = await self.fetch_user_reels(user["username"], 15, user["uid"])
                if not success or not reels:
                    self.logger.error(f"获取用户 {user.get('username')} reels失败, code: {code}, msg: {msg}, reels count: {len(reels)}")
                    user["avg_play_last_10_reels"] = None
                else:
                    user["avg_play_last_10_reels"] = await self._calculate_avg_views(reels)
            return (True, "success", result_users)
            
        except Exception as e:
            error_msg = f"搜索用户失败: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            return (False, error_msg, [])

    async def _find_users_by_search(self, query: str, rank_token: str = None, next_max_id: str = None) -> Tuple[List[Dict[str, Any]], str, str]:
        """通过搜索获取用户
        
        Args:
            query (str): 搜索关键词
            rank_token (str, optional): 排名令牌
            next_max_id (str, optional): 下一页ID
        
        Returns:
            Tuple[List[Dict[str, Any]], str, str]: 用户列表，排名令牌，下一页ID
        """
        try:
            # 构建请求 URL
            url = self.api_endpoints.get("top_serp", {}).get("url")
            if not url:
                self.logger.error("无法获取 top_serp API 端点")
                return []
            
            # 准备 API 请求头
            headers = self._get_headers()
            
            # 准备请求参数
            params = {
                "enable_metadata": "true",
                "query": query,
            }
            if rank_token:
                params["rank_token"] = rank_token
            if next_max_id:
                params["next_max_id"] = next_max_id
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers, "params": params}
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                async with session.get(url, **request_kwargs) as response:
                    if self.is_suspended_redirect(response):
                        self.logger.error(f"请求被重定向到账号挂起页面: {response.url}")
                        await self.handle_suspended_account()
                        return [], None, None
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Instagram API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return [], None, None
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}")
                        return [], None, None
                    response_data = await response.json()
            
            # 解析响应数据
            rank_token = response_data.get('media_grid', {}).get("rank_token")
            next_max_id = response_data.get('media_grid', {}).get("next_max_id")
            users = []
            sections = response_data.get('media_grid', {}).get("sections", [])
            
            for section in sections:
                medias = section.get('layout_content', {}).get("medias", [])
                if not medias:
                    continue
                for media in medias:
                    user = media.get('media', {}).get('user')
                    if not user or not user.get('pk'):
                        continue
                
                    uid = user.get('pk')
                    success, code, msg, user_data = await self.fetch_user_profile(uid)
                    if not success or not user_data:
                        self.logger.error(f"获取用户 {user.get('username')} 资料失败, code: {code}, msg: {msg}")
                        continue
                    users.append(user_data)

            return users, rank_token, next_max_id
            
        except Exception as e:
            self.logger.error(f"获取搜索用户失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
        
    async def _fetch_user_reels_by_uid(self, uid: str, count: int, cursor: str = None, instagram_account: dict = None) -> Tuple[bool, int, Dict[str, Any]]:
        """通过用户ID获取Reels列表
        
        Args:
            uid (str): 用户ID
            count (int): 要获取的Reels数量
            cursor (str, optional): 分页游标
            instagram_account (dict, optional): 指定Instagram账号
        Returns:
            Tuple[bool, int, Dict[str, Any]]: (是否成功, 状态码, 包含Reels列表和分页信息的字典)
        """
        try:
            url = self.api_endpoints.get("user_reels", {}).get("url")
            doc_id = self.api_endpoints.get("user_reels", {}).get("doc_id")
            if not url or not doc_id:
                self.logger.error("无法获取 user_reels API 端点")
                return False, 500, {"reels": [], "next_cursor": None}

            headers = self._get_headers(instagram_account)

            variables = {
                "data": {
                    "include_feed_video": True,
                    "page_size": min(12, count),
                    "target_user_id": uid
                }
            }
            if cursor:
                variables["after"] = cursor
                variables["before"] = None
                variables["first"] = 4
                variables["last"] = None

            form_data = {
                "doc_id": doc_id,
                "variables": json.dumps(variables)
            }

            proxy = self.proxy_url if self.proxy_enabled and self.proxy_url else None

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers, "data": form_data}
                if proxy:
                    request_kwargs["proxy"] = proxy
                async with session.post(url, **request_kwargs) as response:
                    if self.is_suspended_redirect(response):
                        self.logger.error(f"请求被重定向到账号挂起页面: {response.url}")
                        await self.handle_suspended_account()
                        return False, 403, {"reels": [], "next_cursor": None}
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Instagram API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return False, response.status, {"reels": [], "next_cursor": None}
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}")
                        return False, 500, {"reels": [], "next_cursor": None}
                    response_data = await response.json()

            reels = []
            next_cursor = None
            # 解析结构，兼容不同返回格式
            edges = response_data.get("data", {}).get("xdt_api__v1__clips__user__connection_v2", {}).get("edges", [])
            page_info = response_data.get("data", {}).get("xdt_api__v1__clips__user__connection_v2", {}).get("page_info", {})
            next_cursor = page_info.get("end_cursor") if page_info.get("has_next_page") else None

            for edge in edges:
                media = edge.get("node", {}).get('media', {})
                if not media:
                    continue
                clips_tab_pinned_user_ids = media.get("clips_tab_pinned_user_ids", [])
                reel = {
                    "id": media.get("id"),
                    "shortcode": media.get("code"),
                    "like_count": media.get("like_count") or 0,
                    "comment_count": media.get("comment_count") or 0,
                    "play_count": media.get("play_count") or 0,
                    "is_pinned": True if uid in clips_tab_pinned_user_ids else False,
                    "url": f"https://www.instagram.com/reel/{media.get('code', '')}/"
                }
                reels.append(reel)

            return True, 200, {"reels": reels, "next_cursor": next_cursor}
        except Exception as e:
            self.logger.error(f"获取用户Reels失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, 500, {"reels": [], "next_cursor": None}

    async def fetch_user_reels(self, username: str, count: int = 20, uid: str = None, instagram_account: dict = None) -> Tuple[bool, int, str, List[Any]]:
        """获取用户的Reels列表
        
        Args:
            username (str): 用户名
            count (int): 要获取的Reels数量
            uid (str, optional): 用户ID
            instagram_account (dict, optional): 指定Instagram账号
        Returns:
            Tuple[bool, int, str, List[Any]]: (是否成功, 状态码, 消息, Reels列表)
        """
        try:
            if not await self._set_instagram_accounts():
                return False, 500, "未获取到Instagram账号", []
            if not instagram_account:
                instagram_account = self.main_instagram_account

            if not uid:
                success, msg, uid = await self.fetch_user_profile_id(username)
                if not success or not uid:
                    return False, 404, "无法获取用户uid", []

            all_reels = []
            next_cursor = None

            while len(all_reels) < count:
                success, code, result = await self._fetch_user_reels_by_uid(uid, 12, next_cursor, instagram_account)
                self.logger.info(f"获取用户 {username} 的 Reels，cursor: {next_cursor}, 数量: {len(result.get('reels', []))}")
                if not success:
                    return False, code, f"获取Reels失败: HTTP {code}", all_reels 

                all_reels.extend(result.get("reels", []))
                next_cursor = result.get("next_cursor")

                if not next_cursor or len(all_reels) >= count:
                    break

                await self._random_delay(1, 3)

            return True, 200, "success", all_reels[:count]
        except Exception as e:
            self.logger.error(f"获取用户Reels失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, 500, f"获取Reels失败: {str(e)}", []

    async def _calculate_avg_views(self, reels: List[Dict[str, Any]], limit: int = 10) -> float:
        """计算前limit个非置顶Reels的平均播放量（向上取整）
        Args:
            reels (List[Dict[str, Any]]): Reels列表
            limit (int): 要计算的Reels数量限制，默认为10
        Returns:
            float: 平均播放量（向上取整），如果没有则返回0
        """
        if not reels:
            return 0
        # 过滤掉置顶Reels并获取前N条
        non_pinned_reels = [reel for reel in reels if not reel.get('is_pinned', False)][:limit]
        if not non_pinned_reels:
            return 0
        total_views = sum((reel.get('play_count') or 0) for reel in non_pinned_reels)
        avg_views = total_views / len(non_pinned_reels)
        return math.ceil(avg_views)

    async def handle_suspended_account(self):
        """处理账号被挂起的情况"""
        from app.celery_app import update_instagram_account_status
        update_instagram_account_status.delay(self.main_instagram_account.get("id"), self.main_instagram_account.get("username"), "disabled")
        self.logger.error(f"账号 {self.main_instagram_account.get('username')} 被挂起，已触发状态更新任务")