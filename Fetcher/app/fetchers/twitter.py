from typing import List, Dict, Any
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

logger = logging.getLogger(__name__)

class TwitterFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        self.platform = "twitter"
        # 用户代理列表，模拟不同浏览器和设备
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ]
        # 从配置文件加载 API 配置
        self._load_config()
        self.page = None
        self.browser = None
        self.logger = logger  # Ensure logger is properly set
    
    def _load_config(self):
        """从配置文件加载 Twitter API 配置"""
        try:
            import yaml
            config_path = 'config/config.yaml'
            self.logger.info(f"尝试加载配置文件: {config_path}")
            self.logger.info(f"当前工作目录: {os.getcwd()}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 加载代理配置
            proxy_config = config.get('proxy', {})
            self.proxy_enabled = proxy_config.get('enabled', False)
            self.proxy_url = proxy_config.get('url', '')
            if self.proxy_enabled and self.proxy_url:
                self.logger.info(f"代理已启用: {self.proxy_url}")
            
            # 获取 Twitter API 配置
            twitter_config = config.get('twitter', {})
            self.api_endpoints = twitter_config.get('endpoints', {})
            self.auth_params = twitter_config.get('auth_params', {})
            self.logger.info("成功加载 Twitter配置")
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 设置默认值
            self.api_endpoints = {
                "similar_users": "https://x.com/i/api/graphql/WIeRrT1lB03IHxrLKXcY3g/ConnectTabTimeline"
            }
            self.proxy_enabled = False
            self.proxy_url = ''
    
    async def _random_delay(self, min_seconds=1, max_seconds=5):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"随机延迟 {delay:.2f} 秒")
        await asyncio.sleep(delay)
    
    async def _simulate_human_scroll(self, min_scrolls=2, max_scrolls=5):
        """模拟人类滚动行为"""
        num_scrolls = random.randint(min_scrolls, max_scrolls)
        for i in range(num_scrolls):
            # 随机滚动距离
            scroll_distance = random.randint(300, 700)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            # 随机滚动停顿
            await self._random_delay(0.5, 2)
    
    async def _simulate_mouse_movement(self):
        """模拟鼠标随机移动"""
        viewport_size = await self.page.evaluate("() => { return {width: window.innerWidth, height: window.innerHeight} }")
        x = random.randint(0, viewport_size['width'])
        y = random.randint(0, viewport_size['height'])
        await self.page.mouse.move(x, y)
    
    async def _rotate_user_agent(self):
        """轮换用户代理"""
        user_agent = random.choice(self.user_agents)
        await self.page.evaluate(f"() => {{ Object.defineProperty(navigator, 'userAgent', {{ get: () => '{user_agent}' }}) }}")
        self.logger.debug(f"设置用户代理: {user_agent}")
    
    async def _bypass_cloudflare(self):
        """尝试绕过 Cloudflare 检测"""
        # 等待页面加载完成
        await self.page.wait_for_load_state('networkidle')
        
        # 检查是否存在 Cloudflare 挑战
        if await self.page.query_selector('div.cf-browser-verification') is not None:
            self.logger.info("检测到 Cloudflare 挑战，等待解决...")
            # 等待挑战完成
            await self.page.wait_for_selector('div.cf-browser-verification', state='detached', timeout=30000)
            await self.page.wait_for_load_state('networkidle')
    
    async def _setup_browser_session(self):
        """设置浏览器会话，添加反检测措施"""
        # 轮换用户代理
        await self._rotate_user_agent()
        
        # 禁用 WebDriver
        await self.page.evaluate("""() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            delete navigator.__proto__.webdriver;
        }""")
        
        # 添加随机指纹信息
        await self.page.evaluate("""() => {
            // 模拟随机的屏幕分辨率
            Object.defineProperty(window.screen, 'width', { get: () => 1920 });
            Object.defineProperty(window.screen, 'height', { get: () => 1080 });
            
            // 模拟随机的插件
            Object.defineProperty(navigator, 'plugins', { 
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' }
                ]
            });
        }""")
    
    async def fetch_user_profile(self, username: str) -> Dict[str, Any]:
        """获取用户主页信息"""
        self.logger.info(f"获取 Twitter 用户资料: {username}")
        
        try:
            # 准备 API 请求参数
            variables = {
                "screen_name": username,
            }
            
            features = {
                "hidden_profile_subscriptions_enabled":True,
                "profile_label_improvements_pcf_label_in_post_enabled":True,
                "rweb_tipjar_consumption_enabled":True,
                "responsive_web_graphql_exclude_directive_enabled":True,
                "verified_phone_label_enabled":False,
                "subscriptions_verification_info_is_identity_verified_enabled":True,
                "subscriptions_verification_info_verified_since_enabled":True,
                "highlights_tweets_tab_ui_enabled":True,
                "responsive_web_twitter_article_notes_tab_enabled":True,
                "subscriptions_feature_can_gift_premium":True,
                "creator_subscriptions_tweet_preview_api_enabled":True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,
                "responsive_web_graphql_timeline_navigation_enabled":True
            }
            # 准备请求头
            user_agent = random.choice(self.user_agents)
            headers = {
                "authorization": self.auth_params.get('auth_token'),
                "x-csrf-token": self.auth_params.get('csrf_token'),
                "cookie": self.auth_params.get('cookie'),
                "user-agent": user_agent,
                "content-type": "application/json",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "zh-cn"
            }
            
            # 构建请求 URL
            endpoint = self.api_endpoints.get("user_by_screen_name")
            if not endpoint:
                self.logger.error("无法获取 user_by_screen_name API 端点")
                return {}
                
            # URL 参数编码
            params = {
                "variables": json.dumps(variables),
                "features": json.dumps(features)
            }
            query_string = urllib.parse.urlencode(params)
            url = f"{endpoint}?{query_string}"
            
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
                    self.logger.info(f"API 请求状态码: {response.status}")
                    response_data = await response.json()
            
            # 解析响应数据
            user_data = response_data.get("data", {}).get("user", {}).get("result", {})
            legacy_data = user_data.get("legacy", {})
            
            # 构建用户资料
            profile_data = {
                "platform": self.platform,
                "uid": user_data.get("rest_id", ""),
                "username": legacy_data.get("screen_name", ""),
                "nickname": legacy_data.get("name", ""),
                "is_verified": legacy_data.get("verified", False),
                "followers_count": legacy_data.get("followers_count", 0),
                "following_count": legacy_data.get("friends_count", 0),
                "tweet_count": legacy_data.get("statuses_count", 0),
                "bio": legacy_data.get("description", ""),
                "location": legacy_data.get("location", ""),
                "url": f"https://x.com/{legacy_data.get('screen_name', '')}"
            }
            
            self.logger.info(f"成功获取用户资料: {username}")
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
    
    def _generate_curl_command(self, url: str, headers: Dict[str, str], method: str = "GET") -> str:
        """
        生成等效的 cURL 命令用于调试
        
        Args:
            url (str): 请求 URL
            headers (Dict[str, str]): 请求头
            method (str): HTTP 方法，默认为 GET
            
        Returns:
            str: 格式化的 cURL 命令
        """
        curl_command = f"curl -X {method} '{url}' \\\n"
        for key, value in headers.items():
            curl_command += f"  -H '{key}: {value}' \\\n"
        
        # 如果启用了代理，添加代理参数
        if self.proxy_enabled and self.proxy_url:
            curl_command += f"  --proxy '{self.proxy_url}' \\\n"
        
        curl_command = curl_command.rstrip(" \\\n")
        return curl_command
    
    async def find_similar_users(self, username: str, count: int = 20, uid: str = None) -> List[Dict[str, Any]]:
        """找到与指定用户相似的用户,包括二度关系用户
        
        Args:
            username (str): 用户名
            count (int): 要获取的相似用户数量
            uid (str, optional): 用户ID，如果提供则使用此ID查找相似用户
        
        Returns:
            List[Dict[str, Any]]: 相似用户列表
        """
        self.logger.info(f"查找与 {username} 相似的 Twitter 用户，数量: {count}")
        
        try:
            # 如果没有提供 uid，先获取用户资料以获取 uid
            if not uid:
                self.logger.info(f"未提供 uid，尝试获取用户 {username} 的资料以获取 uid")
                user_profile = await self.fetch_user_profile(username)
                if user_profile and "uid" in user_profile:
                    uid = user_profile["uid"]
                    self.logger.info(f"成功获取用户 {username} 的 uid: {uid}")
                else:
                    self.logger.warning(f"无法获取用户 {username} 的 uid，将使用默认 uid")
                    return []

            # 用集合来存储已处理的用户ID，用于去重
            processed_uids = set()
            all_similar_users = []
            
            # 步骤1: 获取第一层相似用户
            first_level_users = await self._fetch_similar_users_by_uid(uid, count)
            self.logger.info(f"获取到第一层相似用户: {len(first_level_users)} 个")
            
            # 添加第一层用户并记录其 UID
            for user in first_level_users:
                if user["uid"] not in processed_uids:
                    processed_uids.add(user["uid"])
                    all_similar_users.append(user)
            
            # 步骤2: 获取第二层相似用户
            second_level_users = []
            
            # 顺序处理每个第一层用户
            for first_level_user in first_level_users[:20]:
                if first_level_user["uid"]:
                    # 顺序请求每个用户的相似用户
                    users = await self._fetch_similar_users_by_uid(first_level_user["uid"], 20)
                    print(333333, len(users))
                    if isinstance(users, list):  # 确保结果是有效的
                        second_level_users.extend(users)
            
            # 添加第二层用户(去重)
            for user in second_level_users:
                if user["uid"] not in processed_uids:
                    processed_uids.add(user["uid"])
                    all_similar_users.append(user)
            
            # 确保返回数量不超过请求数量
            return all_similar_users[:count]
            
        except Exception as e:
            self.logger.error(f"查找相似用户失败: {str(e)}")
            return []

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

    async def _fetch_similar_users_by_uid(self, uid: str, count: int) -> List[Dict[str, Any]]:
        """通过用户ID获取相似用户
        
        Args:
            uid (str): 用户ID
            count (int): 要获取的用户数量
        
        Returns:
            List[Dict[str, Any]]: 相似用户列表
        """
        try:
            # 准备 API 请求头
            user_agent = random.choice(self.user_agents)
            headers = {
                "authorization": self.auth_params.get('auth_token'),
                "x-csrf-token": self.auth_params.get('csrf_token'),
                "cookie": self.auth_params.get('cookie'),
                "user-agent": user_agent,
                "content-type": "application/json",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "zh-cn"
            }
            
            # 准备请求参数
            variables = {
                "count": count,
                "context": json.dumps({"contextualUserId": uid})
            }
            
            features = {
                "rweb_video_screen_enabled": False,
                "profile_label_improvements_pcf_label_in_post_enabled": True,
                "rweb_tipjar_consumption_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "premium_content_api_read_enabled": False,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
                "responsive_web_grok_analyze_post_followups_enabled": True,
                "responsive_web_jetfuel_frame": False,
                "responsive_web_grok_share_attachment_enabled": True,
                "articles_preview_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "responsive_web_grok_analysis_button_from_backend": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_grok_image_annotation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            }
            
            # 构建请求 URL
            endpoint = self.api_endpoints.get("similar_users")
            if not endpoint:
                self.logger.error("无法获取 similar_users API 端点")
                return []
            
            # URL 参数编码
            params = {
                "variables": json.dumps(variables),
                "features": json.dumps(features)
            }
            query_string = urllib.parse.urlencode(params)
            url = f"{endpoint}?{query_string}"
            
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
                    response_data = await response.json()
            
            # 解析响应数据
            similar_users = []
            instructions = response_data.get("data", {}).get("connect_tab_timeline", {}).get("timeline", {}).get("instructions", [])
            
            for instruction in instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        if entry.get("entryId") != "similartomodule-1" or not \
                            entry.get("content", {}).get("items", []):
                            continue
                        for item in entry.get("content", {}).get("items", []):
                            result = item.get("item", {}).get("itemContent", {}).get("user_results", {}).get("result", {})
                            legacy = result.get("legacy", {})
                            if not result or not legacy:
                                continue
                            
                            # 获取用户简介
                            bio = legacy.get('description', '')
                            
                            # 从简介中提取邮箱
                            email_in_bio = await self._extract_email_from_text(bio)
                            
                            user_data = {
                                "uid": result.get("rest_id", ""),
                                "username": legacy.get('screen_name', ''),
                                "nickname": legacy.get('name', ''),
                                "is_verified": legacy.get('verified', False),
                                "followers_count": legacy.get('followers_count', 0),
                                "following_count": legacy.get('friends_count', 0),
                                "tweet_count": legacy.get('statuses_count', 0),
                                "bio": bio,
                                "email_in_bio": email_in_bio,
                                "location": legacy.get('location', ''),
                                "url": f"https://x.com/{legacy.get('screen_name', '')}"
                            }
                            similar_users.append(user_data)
            
            return similar_users
            
        except Exception as e:
            self.logger.error(f"获取相似用户失败: {str(e)}")
            return []
    
    async def login(self, email, password):
        """
        登录 Twitter 账号
        
        Args:
            email (str): Twitter 账号邮箱
            password (str): Twitter 账号密码
            
        Returns:
            bool: 登录是否成功
        """
        try:
            # 设置浏览器会话
            await self._setup_browser_session()
            
            # 导航到 Twitter 登录页面
            await self.page.goto('https://x.com/i/flow/login', wait_until='networkidle')
            
            # 尝试绕过 Cloudflare
            await self._bypass_cloudflare()
            
            # 随机延迟
            await self._random_delay(2, 4)
            
            # 等待邮箱输入框出现并输入邮箱
            email_input = await self.page.wait_for_selector('input[autocomplete="username"]')
            
            # 模拟人类输入 - 逐个字符输入并有随机延迟
            for char in email:
                await email_input.type(char, delay=random.uniform(50, 150))
                await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # 随机延迟
            await self._random_delay(1, 2)
            
            # 点击"下一步"按钮 - 使用更精确的选择器
            next_button = await self.page.wait_for_selector('button[role="button"] div span span:has-text("下一步")')
            
            # 模拟鼠标移动到按钮上
            await self._simulate_mouse_movement()
            await next_button.click()
            
            # 随机延迟
            await self._random_delay(2, 3)
            
            # 等待密码输入框出现并输入密码
            password_input = await self.page.wait_for_selector('input[type="password"]', timeout=5000)
            
            # 模拟人类输入密码 - 逐个字符输入并有随机延迟
            for char in password:
                await password_input.type(char, delay=random.uniform(50, 150))
                await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # 随机延迟
            await self._random_delay(1, 2)
            
            # 点击"登录"按钮
            login_button = await self.page.wait_for_selector('div[role="button"]:has-text("登录")')
            
            # 模拟鼠标移动到按钮上
            await self._simulate_mouse_movement()
            await login_button.click()
            
            # 等待页面加载完成，检查是否登录成功
            await self.page.wait_for_load_state('networkidle')
            
            # 检查是否存在主页元素，判断登录是否成功
            home_timeline = await self.page.query_selector('div[aria-label="主页时间线"]')
            
            if home_timeline:
                self.logger.info("Twitter 登录成功")
                # 登录成功后随机浏览一下，更像人类行为
                await self._simulate_human_scroll(3, 6)
                return True
            else:
                self.logger.error("Twitter 登录失败")
                return False
            
        except Exception as e:
            self.logger.error(f"Twitter 登录过程中出错: {str(e)}")
            return False
    
    async def handle_captcha(self):
        """处理可能出现的验证码"""
        # 检查是否存在验证码
        captcha_selector = await self.page.query_selector('iframe[title*="recaptcha"]')
        if captcha_selector:
            self.logger.warning("检测到验证码，尝试处理...")
            # 这里可以集成验证码解决服务
            # 例如: 2Captcha, Anti-Captcha 等
            # 或者提醒用户手动处理
            self.logger.warning("需要手动处理验证码")
            # 等待验证码消失
            await self.page.wait_for_selector('iframe[title*="recaptcha"]', state='detached', timeout=60000)
            return True
        return False

    async def init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright
        
        self.logger.info("初始化浏览器...")
        playwright = await async_playwright().start()
        
        # 设置浏览器选项 - 将 headless 设置为 False 使浏览器可见
        browser_options = {
            "headless": True,  # 改为可见模式
        }
        
        # 如果启用了代理，添加代理配置
        if self.proxy_enabled and self.proxy_url:
            browser_options["proxy"] = {
                "server": self.proxy_url
            }
        
        # 启动浏览器
        self.browser = await playwright.chromium.launch(**browser_options)
        
        # 创建新页面
        self.page = await self.browser.new_page()
        
        # 设置页面视口大小
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        
        self.logger.info("浏览器初始化完成")
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.logger.info("关闭浏览器...")
            await self.browser.close()
            self.browser = None
            self.page = None
            self.logger.info("浏览器已关闭")

# def search_tweets(query: str, limit: int = 10, config: dict = None):
#     """
#     搜索 Twitter 上的推文
    
#     Args:
#         query: 搜索查询
#         limit: 返回结果数量限制
#         config: Twitter API 配置
        
#     Returns:
#         搜索结果列表
#     """
#     # 使用传入的配置或默认配置
#     if config is None:
#         # 使用默认配置
#         # 现有代码...
#     else:
#         # 使用传入的配置
#         api_key = config.get("api_key")
#         api_secret = config.get("api_secret")
#         access_token = config.get("access_token")
#         access_token_secret = config.get("access_token_secret")
    
#     # 现有的 Twitter API 调用代码...
    
#     # 返回结果
#     return results 