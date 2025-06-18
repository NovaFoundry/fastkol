from typing import Tuple, List, Dict, Any
import logging
import asyncio
import re
import json
import random
import time
import aiohttp
import urllib.parse
from app.fetchers.base import BaseFetcher
from app.settings import settings

logger = logging.getLogger(__name__)

class TiktokFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        self.platform = "tiktok"
        # 用户代理列表，模拟不同浏览器和设备
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
        # 加载 API 配置
        self._load_config()
        self.page = None
        self.browser = None
        self.logger = logger
    
    def _load_config(self):
        """加载 TikTok API 配置"""
        try:
            # 加载代理配置
            proxy_config = settings.get_config('proxy', {})
            self.proxy_enabled = proxy_config.get('enabled', False)
            self.proxy_url = proxy_config.get('url', '')
            if self.proxy_enabled and self.proxy_url:
                self.logger.info(f"代理已启用: {self.proxy_url}")
            
            # 获取 TikTok API 配置
            tiktok_config = settings.get_config('tiktok', {})
            self.api_endpoints = tiktok_config.get('endpoints', {})
            self.logger.info("成功加载 TikTok配置")
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

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
        }

    async def fetch_user_profile(self, username: str) -> Tuple[bool, int, str, Dict[str, Any]]:
        """获取TikTok用户资料
        
        Args:
            username (str): 用户名，不包含@符号
            
        Returns:
            Tuple[bool, int, str, Dict[str, Any]]: 返回(success, status_code, msg, user_data)格式
        """
        self.logger.info(f"获取 TikTok 用户资料: {username}")
        
        try:
            # 构建请求 URL
            url = f"https://www.tiktok.com/@{username}"
            
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
                        return (False, response.status, f"请求失败，状态码: {response.status}", {})
                    
                    html_content = await response.text()
                    
                    # 检查页面是否存在
                    # if "Couldn't find this account" in html_content:
                    #     return (False, 404, "用户不存在", {})
                    
                    # 查找 <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"> 标签
                    script_pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>'
                    script_match = re.search(script_pattern, html_content, re.DOTALL)
                    
                    if not script_match:
                        return (False, 404, "未找到用户数据", {})
                    
                    try:
                        # 尝试解析 JSON
                        script_content = script_match.group(1)
                        json_data = json.loads(script_content)
                        
                        # 从 __DEFAULT_SCOPE__.webapp.user-detail 获取用户数据
                        user_data = self._extract_user_data(json_data)
                        if not user_data:
                            return (False, 404, "未找到用户数据", {})
                        
                        return (True, 200, "Success", user_data)
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON解析错误: {str(e)}")
                        return (False, 500, f"JSON解析错误: {str(e)}", {})
            
        except asyncio.TimeoutError:
            self.logger.error(f"获取用户资料请求超时")
            return (False, 408, "请求超时", {})
        except aiohttp.ClientError as e:
            self.logger.error(f"请求错误: {str(e)}")
            return (False, 500, str(e), {})
        except Exception as e:
            self.logger.error(f"获取用户资料失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return (False, 500, str(e), {})
    
    def _extract_user_data(self, data: Dict) -> Dict:
        """从JSON数据中提取用户信息
        
        Args:
            data (Dict): JSON数据
            
        Returns:
            Dict: 用户数据
        """
        try:
            # 尝试从 __DEFAULT_SCOPE__.webapp.user-detail 获取用户数据
            user_info = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get('userInfo')
            
            if not user_info:
                return {}
            
            # 提取用户数据
            user = user_info.get("user", {})
            stats = user_info.get("statsV2", {}) if user_info.get("statsV2") else user_info.get("stats", {})
            
            # 构建用户资料
            user_data = {
                "uid": user.get("id", ""),
                "sec_uid": user.get("secUid", ""),
                "username": user.get("uniqueId", ""),
                "nickname": user.get("nickname", ""),
                "is_verified": user.get("verified", False),
                "followers_count": stats.get("followerCount", 0),
                "following_count": stats.get("followingCount", 0),
                "post_count": stats.get("videoCount", 0),
                "bio": user.get("signature", ""),
                "country_code": user.get("region", ""),
                "url": f"https://www.tiktok.com/@{user.get('uniqueId', '')}"
            }
            
            return user_data
        except Exception as e:
            self.logger.error(f"提取用户数据失败: {str(e)}")
            return {}
    
    async def find_similar_users(self, username: str, count: int = 20) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """找到与指定用户相似的用户
        
        Args:
            username (str): 用户名
            count (int): 要获取的相似用户数量
        
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 是否成功获取用户资料, msg, 相似用户列表
        """
        self.logger.info(f"查找与 {username} 相似的 TikTok 用户，数量: {count}")

        result_users = []
        try:
            # 构建请求 URL
            url = self.api_endpoints.get("similar_users", {}).get("url")
            if not url:
                self.logger.error("无法获取 similar_users API 端点")
                return False, "API端点未配置", []
            
            # 替换URL中的用户名和数量
            url = url.replace("{username}", username).replace("{count}", str(count))
            
            # 准备请求头
            headers = self._get_headers()
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers}
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                async with session.get(url, **request_kwargs) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"TikTok API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return False, f"API返回非200: {response.status}", []
                    
                    response_data = await response.json()
            
            # 解析响应数据
            similar_users_data = response_data.get("similar_users", [])
            
            # 处理每个相似用户
            for user_data in similar_users_data:
                username = user_data.get("unique_id", "")
                if not username:
                    continue
                
                # 获取详细资料
                success, code, msg, profile = await self.fetch_user_profile(username)
                if not success or not profile:
                    self.logger.error(f"获取用户 {username} 资料失败, code: {code}, msg: {msg}")
                    continue
                
                result_users.append(profile)
                
                # 添加随机延迟，避免请求过于频繁
                await self._random_delay(1, 3)
                
                # 如果已经达到请求的数量，退出循环
                if len(result_users) >= count:
                    break
            
            return True, "success", result_users
        
        except Exception as e:
            self.logger.error(f"查找相似用户失败: {str(e)}")
            return False, str(e), []

    async def find_users_by_search(self, query: str, count: int = 20) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """搜索用户
        
        Args:
            query (str): 搜索关键词
            count (int): 要获取的用户数量
            
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 成功状态，msg，用户列表
        """
        self.logger.info(f"搜索用户: {query}, 数量: {count}")
        
        result_users = []
        try:
            # 构建请求 URL
            url = self.api_endpoints.get("search_users", {}).get("url")
            if not url:
                self.logger.error("无法获取 search_users API 端点")
                return False, "API端点未配置", []
            
            # 替换URL中的查询和数量
            url = url.replace("{query}", urllib.parse.quote(query)).replace("{count}", str(count))
            
            # 准备请求头
            headers = self._get_headers()
            
            # 设置代理
            proxy = None
            if self.proxy_enabled and self.proxy_url:
                proxy = self.proxy_url
            
            # 发送请求
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_kwargs = {"headers": headers}
                if proxy:
                    request_kwargs["proxy"] = proxy
                
                async with session.get(url, **request_kwargs) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"TikTok API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return False, f"API返回非200: {response.status}", []
                    
                    response_data = await response.json()
            
            # 解析响应数据
            users_data = response_data.get("user_list", [])
            
            # 处理每个用户
            for user_data in users_data:
                username = user_data.get("unique_id", "")
                if not username:
                    continue
                
                # 获取详细资料
                success, code, msg, profile = await self.fetch_user_profile(username)
                if not success or not profile:
                    self.logger.error(f"获取用户 {username} 资料失败, code: {code}, msg: {msg}")
                    continue
                
                result_users.append(profile)
                
                # 添加随机延迟，避免请求过于频繁
                await self._random_delay(1, 3)
                
                # 如果已经达到请求的数量，退出循环
                if len(result_users) >= count:
                    break
            
            return True, "success", result_users[:count]
        
        except Exception as e:
            self.logger.error(f"搜索用户失败: {str(e)}")
            return False, str(e), []
            
    async def fetch_user_followings(
        self, username: str, sec_uid: str = None, pages: int = 1, size: int = 30
    ) -> Tuple[bool, int, str, List[Dict[str, Any]]]:
        """
        获取TikTok用户的关注列表，支持分页
        
        Args:
            username (str): 用户名
            sec_uid (str, optional): 用户的secUid，如果提供则使用此ID获取关注列表
            pages (int): 要获取的页数，默认1
            size (int): 每页获取的数量，默认30
            
        Returns:
            Tuple[bool, int, str, List[Dict[str, Any]]]: (是否成功, 状态码, 消息, 关注列表)
        """
        self.logger.info(f"获取 TikTok 用户 {username} 的关注列表，页数: {pages}, 每页数量: {size}")
        
        all_followings = []
        max_cursor = 0
        min_cursor = 0
        
        try:
            # 如果没有提供 sec_uid，先获取用户资料以获取 sec_uid
            if not sec_uid:
                success, code, msg, user_profile = await self.fetch_user_profile(username)
                if not success or not user_profile:
                    return False, code, f"获取用户资料失败: {msg}", []
                sec_uid = user_profile.get("sec_uid", "")
                if not sec_uid:
                    return False, 404, "无法获取用户 sec_uid", []
            
            # 分页获取关注列表
            for _ in range(pages):
                ok, code, msg, followings, next_max_cursor, next_min_cursor = await self._fetch_user_followings(
                    username=username, 
                    sec_uid=sec_uid, 
                    count=size, 
                    max_cursor=max_cursor, 
                    min_cursor=min_cursor
                )
                
                if not ok:
                    return ok, code, msg, all_followings
                
                all_followings.extend(followings)
                
                # 更新游标值用于下一页请求
                max_cursor = next_max_cursor
                min_cursor = next_min_cursor
                
                # 如果没有更多数据，退出循环
                if not next_max_cursor or next_max_cursor == max_cursor:
                    break
                    
                # 添加随机延迟，避免请求过于频繁
                await self._random_delay(1, 2)
            
            self.logger.info(f"成功获取用户 {username} 的关注列表，总数量: {len(all_followings)}")
            return True, 200, "success", all_followings
            
        except Exception as e:
            self.logger.error(f"获取用户关注列表失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, 500, str(e), []
    
    async def _fetch_user_followings(
        self, username: str, sec_uid: str, count: int = 30, max_cursor: int = 0, min_cursor: int = 0
    ) -> Tuple[bool, int, str, List[Dict[str, Any]], int, int]:
        """
        获取TikTok用户的单页关注列表
        
        Args:
            username (str): 用户名
            sec_uid (str): 用户的secUid
            count (int): 获取的数量，默认30
            max_cursor (int): 最大游标值，用于分页，默认0
            min_cursor (int): 最小游标值，用于分页，默认0
            
        Returns:
            Tuple[bool, int, str, List[Dict[str, Any]], int, int]: (是否成功, 状态码, 消息, 关注列表, 下一页最大游标, 下一页最小游标)
        """
        followings = []
        next_max_cursor = max_cursor
        next_min_cursor = min_cursor
        
        try:
            # 构建请求 URL
            endpoint = self.api_endpoints.get("user_followings")
            if not endpoint:
                self.logger.error("无法获取 user_followings API 端点")
                return False, 500, "API端点未配置", [], next_max_cursor, next_min_cursor
            
            # 准备请求参数
            params = {
                "app_language": "zh-Hans",
                "app_name": "tiktok_web",
                "browser_language": "zh-CN",
                "browser_name": "Mozilla",
                "browser_online": "true",
                "browser_platform": "MacIntel",
                "browser_version": "5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "channel": "tiktok_web",
                "cookie_enabled": "true",
                "count": str(count),
                "data_collection_enabled": "true",
                "device_platform": "web_pc",
                "focus_state": "true",
                "from_page": "user",
                "history_len": "6",
                "is_fullscreen": "false",
                "is_page_visible": "true",
                "maxCursor": str(max_cursor),
                "minCursor": str(min_cursor),
                "os": "mac",
                "priority_region": "US",
                "region": "US",
                "secUid": sec_uid
            }
            
            # 构建完整URL
            query_string = urllib.parse.urlencode(params)
            url = f"{endpoint}?{query_string}"
            
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
                        return False, response.status, f"请求失败，状态码: {response.status}", [], next_max_cursor, next_min_cursor
                    
                    response_data = await response.json()
            
            # 解析响应数据
            status_code = response_data.get("statusCode", 0)
            if status_code != 0:
                return False, status_code, response_data.get("statusMsg", "请求失败"), [], next_max_cursor, next_min_cursor
            
            # 提取关注列表
            users_data = response_data.get("userList", [])
            for user_data in users_data:
                user = user_data.get("user", {})
                stats = user_data.get("stats", {})
                
                following_user = {
                    "uid": user.get("id", ""),
                    "sec_uid": user.get("secUid", ""),
                    "username": user.get("uniqueId", ""),
                    "nickname": user.get("nickname", ""),
                    "is_verified": user.get("verified", False),
                    "followers_count": stats.get("followerCount", 0),
                    "following_count": stats.get("followingCount", 0),
                    "post_count": stats.get("videoCount", 0),
                    "bio": user.get("signature", ""),
                    "country_code": user.get("region", ""),
                    "url": f"https://www.tiktok.com/@{user.get('uniqueId', '')}"
                }
                
                followings.append(following_user)
            
            # 获取分页信息
            has_more = response_data.get("hasMore", False)
            next_max_cursor = response_data.get("maxCursor", max_cursor)
            next_min_cursor = response_data.get("minCursor", min_cursor)
            
            self.logger.info(f"成功获取用户 {username} 的关注列表，当前页数量: {len(followings)}")
            return True, 200, "success", followings, next_max_cursor, next_min_cursor
            
        except asyncio.TimeoutError:
            self.logger.error(f"获取用户关注列表请求超时")
            return False, 408, "请求超时", [], next_max_cursor, next_min_cursor
        except aiohttp.ClientError as e:
            self.logger.error(f"请求错误: {str(e)}")
            return False, 500, str(e), [], next_max_cursor, next_min_cursor
        except Exception as e:
            self.logger.error(f"获取用户关注列表失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, 500, str(e), [], next_max_cursor, next_min_cursor