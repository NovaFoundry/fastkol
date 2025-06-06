from typing import Tuple, List, Dict, Any, Optional
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

class TwitterFetcher(BaseFetcher):
    def __init__(self):
        super().__init__()
        self.platform = "twitter"
        # 用户代理列表，模拟不同浏览器和设备
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        # 加载 API 配置
        self._load_config()
        self.page = None
        self.browser = None
        self.logger = logger  # Ensure logger is properly set
        # 初始化时获取Twitter认证信息
        self.twitter_accounts = []     # 所有Twitter账号
        self.main_twitter_account = {} # 主账号
        self.twitter_accounts_need_count = 1 # 需要获取的Twitter账号数量
        self.twitter_accounts_last_used = {} # 所有Twitter账号上次使用时间
        self.twitter_accounts_cooldown_seconds = 5 # 所有Twitter账号冷却时间

        # 新增normal账号管理
        self.normal_accounts = []
        self.normal_accounts_need_count = 10 # 需要获取的normal账号数量
        self.normal_accounts_last_used = {} # 所有normal账号上次使用时间
        self.normal_accounts_cooldown_seconds = 60 # 所有normal账号冷却时间
        
        # 记录每个账号的连续429错误次数
        self.account_rate_limit_count = {}

    def _load_config(self):
        """加载 Twitter API 配置"""
        try:
            # 加载代理配置
            proxy_config = settings.get_config('proxy', {})
            self.proxy_enabled = proxy_config.get('enabled', False)
            self.proxy_url = proxy_config.get('url', '')
            if self.proxy_enabled and self.proxy_url:
                self.logger.info(f"代理已启用: {self.proxy_url}")
            
            # 获取 Twitter API 配置
            twitter_config = settings.get_config('twitter', {})
            self.api_endpoints = twitter_config.get('endpoints', {})
            self.logger.info("成功加载 Twitter配置")
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 设置默认值
            self.api_endpoints = {}
            self.proxy_enabled = False
            self.proxy_url = ''
    
    def _get_headers(self, twitter_account: dict = None) -> Dict[str, str]:
        """获取请求头
        
        Returns:
            Dict[str, str]: 请求头字典
        """
        return {
                "authorization": twitter_account.get('headers', {}).get('authorization', '') if twitter_account else self.main_twitter_account.get('headers', {}).get('authorization', ''),
                "x-csrf-token": twitter_account.get('headers', {}).get('x-csrf-token', '') if twitter_account else self.main_twitter_account.get('headers', {}).get('x-csrf-token', ''),
                "cookie": twitter_account.get('headers', {}).get('cookie', '') if twitter_account else self.main_twitter_account.get('headers', {}).get('cookie', ''),
                "user-agent": self.user_agent,
                "content-type": "application/json",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "zh-cn",
        }
    
    async def _random_delay(self, min_seconds=1, max_seconds=5):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def fetch_user_profile(self, username: str, twitter_account: dict = None) -> Dict[str, Any]:
        """获取用户主页信息"""
        self.logger.info(f"获取 Twitter 用户资料: {username}")
        ok, _ = await self._set_twitter_accounts()
        if not ok:
            self.logger.error("未选择Twitter账号，无法获取用户资料")
            return {}
        
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
            headers = self._get_headers(twitter_account)
            
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
    
    async def _extract_hashtags(self, text: str) -> List[str]:
        """从文本中提取 hashtag
        
        Args:
            text (str): 要提取 hashtag 的文本
            
        Returns:
            List[str]: hashtag 列表
        """
        if not text:
            return []
        
        # 使用正则表达式匹配 hashtag
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
        return hashtags

    # async def _get_user_hashtags(self, username: str, uid: str, bio: str = None) -> List[str]:
    #     """获取用户的 hashtag
        
    #     Args:
    #         username (str): 用户名
    #         uid (str): 用户ID
            
    #     Returns:
    #         List[str]: 用户最常用的 3-5 个 hashtag
    #     """
    #     try:
    #         # 如果 bio 为空，说明调用时没传bio，需要获取用户资料; 
    #         # 如果是空字符串，说明没获取到bio，没必要再去获取用户资料
    #         if bio is None:
    #             # 获取用户资料
    #             user_profile = await self.fetch_user_profile(username)
    #             bio = user_profile.get('bio', '')

    #         if bio:
    #             bio_hashtags = await self._extract_hashtags(bio)
    #         else:
    #             bio_hashtags = []
            
    #         # 获取用户最近的推文
    #         tweets = await self.fetch_user_tweets(username=username, count=20, uid=uid)
            
    #         # 从推文中提取 hashtag
    #         tweet_hashtags = []
    #         for tweet in tweets:
    #             tweet_hashtags.extend(await self._extract_hashtags(tweet.get('text', '')))
            
    #         # 合并所有 hashtag
    #         all_hashtags = bio_hashtags + tweet_hashtags
            
    #         # 统计 hashtag 出现频率
    #         hashtag_count = {}
    #         for tag in all_hashtags:
    #             hashtag_count[tag] = hashtag_count.get(tag, 0) + 1
            
    #         # 按频率排序并获取前 3-5 个
    #         sorted_hashtags = sorted(hashtag_count.items(), key=lambda x: x[1], reverse=True)
    #         top_hashtags = [tag for tag, _ in sorted_hashtags[:5]]
    #         print(f"用户 {username} 的 hashtag: {top_hashtags}")
            
    #         return top_hashtags
            
    #     except Exception as e:
    #         self.logger.error(f"获取用户 hashtag 失败: {str(e)}")
    #         return []

    async def _handle_rate_limit(self, twitter_account: Dict[str, Any], username: str) -> None:
        """处理频率限制
        
        Args:
            twitter_account: Twitter账号信息
            username: 用户名
        """
        account_id = twitter_account.get("id")
        if not account_id:
            return
            
        # 增加连续429错误计数
        self.account_rate_limit_count[account_id] = self.account_rate_limit_count.get(account_id, 0) + 1
        
        # 只有当连续3次出现429时才更新账号状态
        if self.account_rate_limit_count[account_id] >= 3:
            # 在函数内部导入，避免循环导入
            from app.celery_app import update_twitter_account_status
            # 触发异步任务更新账号状态
            update_twitter_account_status.delay(account_id, twitter_account.get('username', ''), "suspended")
            
            self.logger.warning(f"账号 {twitter_account.get('username')} 连续3次遇到频率限制，已触发状态更新任务")
            # 重置计数器
            self.account_rate_limit_count[account_id] = 0
        else:
            self.logger.warning(f"账号 {twitter_account.get('username')} 第 {self.account_rate_limit_count[account_id]} 次遇到频率限制")

    async def find_similar_users(self, username: str, count: int = 20, uid: str = None) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """找到与指定用户相似的用户,包括二度关系用户
        
        Args:
            username (str): 用户名
            count (int): 要获取的相似用户数量
            uid (str, optional): 用户ID，如果提供则使用此ID查找相似用户
        
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 是否成功获取用户资料, msg, 相似用户列表
        """
        self.logger.info(f"查找与 {username} 相似的 Twitter 用户，数量: {count}")
        try:
            # 获取 similar 专用账号，默认取 10 个
            ok, _ = await self._set_twitter_accounts()
            if not ok or not self.twitter_accounts:
                return (False, "未获取到twitter账号", [])

            # 如果没有提供 uid，先获取用户资料以获取 uid
            if not uid:
                self.logger.info(f"未提供 uid，尝试获取用户 {username} 的资料以获取 uid")
                user_profile = await self.fetch_user_profile(username, twitter_account=self.main_twitter_account)
                if user_profile and "uid" in user_profile:
                    uid = user_profile["uid"]
                    self.logger.info(f"成功获取用户 {username} 的 uid: {uid}")
                else:
                    self.logger.warning(f"无法获取用户 {username} 的 uid，将使用默认 uid")
                    return (False, "无法获取用户 uid", [])

            # 用集合来存储已处理的用户ID，用于去重
            processed_uids = set()
            all_similar_users = []

            # 步骤1: 获取第一层相似用户
            first_level_users = await self._find_similar_users_by_uid(uid, twitter_account=self.main_twitter_account)
            self.logger.info(f"获取到第一层相似用户: {len(first_level_users)} 个")
            processed_uids = set(user["uid"] for user in first_level_users)
            all_similar_users = first_level_users

            second_level_users = []
            if len(first_level_users) < count:
                for first_level_user in first_level_users[:20]:
                    if first_level_user["uid"]:
                        users = await self._find_similar_users_by_uid(first_level_user["uid"], twitter_account=self.main_twitter_account)
                        self.logger.info(f"获取到{first_level_user['username']}第二层相似用户: {len(users)} 个")
                        if isinstance(users, list):
                            second_level_users.extend(users)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                # 添加第二层用户(去重)
                for user in second_level_users:
                    if user["uid"] not in processed_uids:
                        processed_uids.add(user["uid"])
                        all_similar_users.append(user)

            # for user in all_similar_users:
            #     # 记录已尝试过的账号ID
            #     tried_account_ids = set()
            #     success = False
            #     code = 200
            #     tweets = []
                
            #     while not success:
            #         twitter_account = await self._get_available_normal_account()
            #         if not twitter_account:
            #             self.logger.warning(f"无法获取可用的normal账号，无法获取用户的推文")
            #             break
                        
            #         # 如果这个账号已经尝试过，跳过
            #         if twitter_account.get("id") in tried_account_ids:
            #             continue
                        
            #         tried_account_ids.add(twitter_account.get("id"))
            #         success, code, _, tweets = await self.fetch_user_tweets(user["username"], 10, user["uid"], twitter_account)
                    
            #         if success:
            #             # 重置该账号的429错误计数
            #             account_id = twitter_account.get("id")
            #             if account_id:
            #                 self.account_rate_limit_count[account_id] = 0
            #             # 计算平均浏览量
            #             user["avg_views_last_10_tweets"] = await self._calculate_avg_views(tweets)
            #             break
            #         else:
            #             # 只有在遇到频率限制时才尝试下一个账号
            #             if code == 429:
            #                 # 处理频率限制
            #                 await self._handle_rate_limit(twitter_account, user["username"])
            #                 continue
            #             else:
            #                 # 其他错误时重置429错误计数
            #                 account_id = twitter_account.get("id")
            #                 if account_id:
            #                     self.account_rate_limit_count[account_id] = 0
            #                 self.logger.warning(f"使用账号 {twitter_account.get('username')} 获取用户 {user['username']} 的推文失败，错误码: {code}")
            #                 break
            return (True, "success", all_similar_users[:count])
        except Exception as e:
            self.logger.error(f"查找相似用户失败: {str(e)}")
            return (False, str(e), [])

    async def _calculate_avg_views(self, tweets: List[Dict[str, Any]], limit: int = 10) -> float:
        """计算非置顶推文的平均浏览量
        
        Args:
            tweets (List[Dict[str, Any]]): 推文列表
            limit (int): 要计算的推文数量限制，默认为10
            
        Returns:
            float: 平均浏览量（向上取整），如果没有符合条件的推文则返回0
        """
        if not tweets:
            return 0
            
        # 过滤掉置顶推文并获取前N条
        non_pinned_tweets = [tweet for tweet in tweets if not tweet.get('is_pinned', False)][:limit]
        if not non_pinned_tweets:
            return 0
            
        # 确保views_count是整数
        total_views = sum(tweet.get('views_count', 0) for tweet in non_pinned_tweets)
        avg_views = total_views / len(non_pinned_tweets)
        return math.ceil(avg_views)  # 向上取整

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

    async def _find_similar_users_by_uid(self, uid: str, twitter_account) -> List[Dict[str, Any]]:
        """通过用户ID获取相似用户
        
        Args:
            uid (str): 用户ID
            twitter_account (dict, optional): 推特账号, 如果为空则使用默认账号
        Returns:
            List[Dict[str, Any]]: 相似用户列表
        """
        try:
            # 准备 API 请求头
            if not twitter_account:
                raise Exception("twitter_account 不能为空")
            headers = self._get_headers(twitter_account)
            
            # 准备请求参数
            variables = {
                "count": 20,
                "context": json.dumps({"contextualUserId": uid})
            }
            
            features = {
                "rweb_video_screen_enabled":False,"profile_label_improvements_pcf_label_in_post_enabled":True,"rweb_tipjar_consumption_enabled":True,"verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,
                "premium_content_api_read_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"responsive_web_grok_analyze_button_fetch_trends_enabled":False,"responsive_web_grok_analyze_post_followups_enabled":True,"responsive_web_jetfuel_frame":False,"responsive_web_grok_share_attachment_enabled":True,"articles_preview_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"responsive_web_grok_show_grok_translated_post":False,"responsive_web_grok_analysis_button_from_backend":True,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,
                "longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_grok_image_annotation_enabled":True,"responsive_web_enhance_cards_enabled":False
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
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Twitter API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return []
                    # 校验 Content-Type
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}, 内容: {error_text}")
                        return []
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
                            username = result.get('core', {}).get('screen_name', '')
                            
                            user_data = {
                                "uid": result.get("rest_id", ""),
                                "username": username,
                                "nickname": result.get('core', {}).get('name', ''),
                                "is_verified": result.get('is_blue_verified', False),
                                "followers_count": legacy.get('followers_count', 0),
                                "following_count": legacy.get('friends_count', 0),
                                "tweet_count": legacy.get('statuses_count', 0),
                                "bio": bio,
                                "email_in_bio": email_in_bio,
                                "location": result.get('location', '').get('location', ''),
                                "url": f"https://x.com/{username}"
                            }
                            similar_users.append(user_data)
            
            return similar_users
            
        except Exception as e:
            self.logger.error(f"获取相似用户失败: {str(e)}")
            return []
    
    async def _extract_tweet_data(self, result: Dict[str, Any], username: str) -> Dict[str, Any]:
        """Extract tweet data from a result object
        
        Args:
            result (Dict[str, Any]): The tweet result object
            username (str): The username of the tweet author
            
        Returns:
            Dict[str, Any]: Extracted tweet data or None if invalid
        """
        tweet_id = result.get("rest_id", "")
        tweet_type = result.get("__typename", "")
        if not tweet_id or tweet_type != "Tweet":
            return {}
            
        legacy = result.get("legacy", {})
        if not legacy:
            return {}
            
        # Skip retweets
        if legacy.get("is_retweet"):
            return {}
            
        # Extract tweet data
        tweet_data = {
            "id": tweet_id,
            "text": legacy.get("full_text", ""),
            "created_at": legacy.get("created_at", ""),
            "favorite_count": legacy.get("favorite_count", 0),
            "retweet_count": legacy.get("retweet_count", 0),
            "reply_count": legacy.get("reply_count", 0),
            "quote_count": legacy.get("quote_count", 0),
            "views_count": int(result.get("views", {}).get("count", '0')),
            "url": f"https://x.com/{username}/status/{tweet_id}"
        }
        
        return tweet_data

    async def _fetch_user_tweets_by_uid(self, uid: str, username: str, count: int, cursor: str = None, twitter_account: Dict[str, Any] = None) -> Tuple[bool, int, Dict[str, Any]]:
        """通过用户ID获取推文列表
        
        Args:
            uid (str): 用户ID
            count (int): 要获取的推文数量
            cursor (str, optional): 分页游标，用于获取更多推文
            twitter_account (dict, optional): 指定推特账号
        Returns:
            Tuple[bool, int, Dict[str, Any]]: (是否成功, 状态码, 包含推文列表和分页信息的字典)
        """
        self.logger.info(f"获取用户 {username} 的推文列表，cursor: {cursor}")
        try:
            # 准备 API 请求头
            headers = self._get_headers(twitter_account)
            
            # 准备请求参数
            variables = {
                "userId": uid,
                "count": count,
                "includePromotedContent": False,
                "withQuickPromoteEligibilityTweetFields": False,
                "withVoice": True,
                "withV2Timeline": True
            }
            
            # 如果提供了游标，添加到变量中
            if cursor:
                variables["cursor"] = cursor
            
            features = {
                "rweb_video_screen_enabled":False,"profile_label_improvements_pcf_label_in_post_enabled":False,"rweb_tipjar_consumption_enabled":True,"responsive_web_graphql_exclude_directive_enabled":True,"verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"premium_content_api_read_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"responsive_web_grok_analyze_button_fetch_trends_enabled":False,"responsive_web_grok_analyze_post_followups_enabled":True,"responsive_web_jetfuel_frame":False,"responsive_web_grok_share_attachment_enabled":True,"articles_preview_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"responsive_web_grok_show_grok_translated_post":False,"responsive_web_grok_analysis_button_from_backend":False,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,"longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_grok_image_annotation_enabled":True,"responsive_web_enhance_cards_enabled":False
            }
            
            # 构建请求 URL
            endpoint = self.api_endpoints.get("user_tweets")
            if not endpoint:
                self.logger.error("无法获取 user_tweets API 端点")
                return False, 500, {"tweets": [], "next_cursor": None}
            
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
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Twitter API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return False, response.status, {"tweets": [], "next_cursor": None}
                    response_data = await response.json()
            
            # 解析响应数据
            tweets = []
            next_cursor = None
            
            # 提取推文数据
            instructions = response_data.get("data", {}).get("user", {}).get("result", {}).get("timeline", {}).get("timeline", {}).get("instructions", [])
            
            for instruction in instructions:
                # 提取置顶推文
                if instruction.get("type") == "TimelinePinEntry":
                    result = instruction.get("entry", {}).get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                    tweet_data = await self._extract_tweet_data(result, username)
                    if tweet_data:
                        tweet_data["is_pinned"] = True
                        tweets.append(tweet_data)

                elif instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        if entry.get("entryId", "").startswith("tweet-"):
                            result = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                            tweet_data = await self._extract_tweet_data(result, username)
                            if tweet_data:
                                tweets.append(tweet_data)
                            
                        elif entry.get("entryId", "").startswith("profile-conversation-"):
                            # 自己回复的推文，取原始推文数据
                            items = entry.get("content", {}).get("items", [])
                            if not items:
                                continue
                            result = items[0].get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                            tweet_data = await self._extract_tweet_data(result, username)
                            if tweet_data:
                                tweets.append(tweet_data)
                                    
                        # 提取下一页游标
                        elif entry.get("entryId", "").startswith("cursor-bottom-"):
                            next_cursor = entry.get("content", {}).get("value", "")
            
            return True, 200, {
                "tweets": tweets,
                "next_cursor": next_cursor
            }
            
        except Exception as e:
            self.logger.error(f"获取用户推文失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, 500, {"tweets": [], "next_cursor": None}

    async def fetch_user_tweets(self, username: str, count: int = 20, uid: str = None, twitter_account: Dict[str, Any] = None) -> Tuple[bool, int, str, List[Any]]:
        """获取用户的推文列表
        
        Args:
            username (str): 用户名
            count (int): 要获取的推文数量）
            uid (str, optional): 用户ID，如果提供则使用此ID获取推文
            twitter_account (dict, optional): 指定推特账号
        Returns:
            Tuple[bool, int, str, List[Any]]: (是否成功, 状态码, 消息, 推文列表)
        """
        try:
            ok, _ = await self._set_twitter_accounts()
            if not ok or not self.twitter_accounts:
                return False, 500, "未获取到twitter账号", []
            if not twitter_account:
                twitter_account = await self._get_available_normal_account()
                if not twitter_account:
                    return False, 500, "未获取到normal账号", []

            # 如果没有提供 uid，先获取用户资料以获取 uid
            if not uid:
                self.logger.info(f"未提供 uid，尝试获取用户 {username} 的资料以获取 uid")
                user_profile = await self.fetch_user_profile(username, twitter_account)
                if user_profile and "uid" in user_profile:
                    uid = user_profile["uid"]
                    self.logger.info(f"成功获取用户 {username} 的 uid: {uid}")
                else:
                    self.logger.warning(f"无法获取用户 {username} 的 uid，将使用默认方式获取推文")
                    return False, 404, "无法获取用户uid", []

            # 存储所有获取的推文
            all_tweets = []
            next_cursor = None

            # 循环获取推文，直到达到请求的数量或没有更多推文
            while len(all_tweets) < count:
                # 使用新的方法获取推文
                success, code, result = await self._fetch_user_tweets_by_uid(uid, username, min(100, count - len(all_tweets)), next_cursor, twitter_account)
                
                if not success:
                    return False, code, f"获取推文失败: HTTP {code}", all_tweets

                # 添加本次获取的推文到总列表
                all_tweets.extend(result.get("tweets", []))

                # 更新下一页游标
                next_cursor = result.get("next_cursor")

                # 如果没有更多推文或已经达到请求的数量，退出循环
                if not next_cursor or len(all_tweets) >= count:
                    break

                # 添加随机延迟，避免请求过于频繁
                await self._random_delay(1, 3)

            # 确保返回数量不超过请求数量
            return True, 200, "success", all_tweets[:count]
        except Exception as e:
            self.logger.error(f"获取用户推文失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, 500, f"获取推文失败: {str(e)}", []

    # 获取可用的 normal 账号，每个账号冷却时间60秒
    async def _get_available_normal_account(self) -> Optional[Dict[str, Any]] | None:
        if not self.normal_accounts:
            ok = await self._set_normal_accounts()
            if not ok or not self.normal_accounts:
                self.logger.info("没有获取到normal账号")
                return None
        while True:
            current_time = time.time()
            available_accounts = [acc for acc in self.normal_accounts if acc.get("id") not in self.normal_accounts_last_used or current_time - self.normal_accounts_last_used[acc.get("id")] >= self.normal_accounts_cooldown_seconds]
            if available_accounts:
                acc = available_accounts[0]
                self.normal_accounts_last_used[acc.get("id")] = time.time()
                return acc
            self.logger.info(f"所有normal账号都在冷却中，等待 10 秒...")
            await asyncio.sleep(10)

    async def find_users_by_search(self, query: str, count: int = 20) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """搜索用户
        
        Args:
            query (str): 搜索关键词
            count (int): 要获取的用户数量
            
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 成功状态，msg，用户列表
        """
        self.logger.info(f"搜索用户: {query}, 数量: {count}")
        try:
            # 获取 search 专用账号，默认取 10 个
            ok = await self._set_normal_accounts()
            if not ok or not self.normal_accounts:
                self.logger.error("未获取到search账号")
                return (False, "未获取到search账号", [])
            self.logger.info(f"获取到 {len(self.normal_accounts)} 个 normal 账号")

            # 存储所有获取的用户
            all_users = []
            # 用于去重的用户ID集合
            processed_uids = set()
            cursor = None
            # 记录连续没有新数据的次数
            no_new_data_count = 0
            # 上一次获取的用户数量
            last_user_count = 0
            # 记录每个账号最后使用时间
            account_last_used = {}
            
            self.logger.info(f"获取用户: {len(processed_uids)}/{count}")
            # 循环获取用户，直到达到请求的数量或没有更多用户
            while len(processed_uids) < count:
                # 选择下一个可用的账号
                search_account = await self._get_available_normal_account()
                if not search_account:
                    # 如果没有可用账号，每 10 秒检测一次
                    self.logger.info("所有账号都在冷却中，等待 10 秒...")
                    await asyncio.sleep(10)
                    continue
                account_last_used[search_account.get("id")] = time.time()

                # 使用新的方法获取用户
                success, msg, users, cursor = await self._find_users_by_search(query, cursor, search_account)
                if not success:
                    self.logger.error(f"搜索用户失败: {msg}")
                    return (False, msg, all_users)

                for user in users:
                    uid = user.get("uid")
                    if uid and uid not in processed_uids:
                        processed_uids.add(uid)
                        all_users.append(user)

                self.logger.info(f"获取用户: {len(processed_uids)}/{count}, next cursor: {cursor}")

                if len(processed_uids) == last_user_count:
                    no_new_data_count += 1
                else:
                    no_new_data_count = 0
                    last_user_count = len(processed_uids)

                # 如果没有cursor或已经达到请求的数量，退出循环
                if not cursor or len(all_users) >= count:
                    break

                if no_new_data_count >= 3:
                    self.logger.info("连续3次没有获取到新数据，停止搜索")
                    break
                
                # 添加随机延迟，避免请求过于频繁
                await self._random_delay(1, 3)
            
            ok, use_normal_accounts_fallback = await self._set_twitter_accounts(use_normal_accounts_fallback=True)
            if not use_normal_accounts_fallback:
                await self._clear_normal_accounts()
            if ok:
                self.logger.info("成功获取Twitter账号, 数量: {len(self.twitter_accounts)}")
            else:
                self.logger.error("获取Twitter账号失败")
                return (True, "success", all_users[:count])

            # 确保返回数量不超过请求数量
            return (True, "success", all_users[:count])
        except Exception as e:
            error_msg = f"搜索用户失败: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            return (False, error_msg, [])

    async def _find_users_by_search(self, query: str, cursor: str = None, search_account: dict = None) -> Tuple[bool, str, List[Dict[str, Any]], str]:
        """通过搜索获取一页用户
        
        Args:
            query (str): 搜索关键词
            count (int): 要获取的用户数量
            cursor (str, optional): 分页游标，用于获取更多用户
            search_account (dict, optional): search专用账号
        
        Returns:
            Tuple[bool, str, List[Dict[str, Any]], str]: 成功状态, msg, 用户列表, 下一页游标
        """
        try:
            # 准备 API 请求头
            if not search_account:
                raise Exception("search_account 不能为空")
            headers = self._get_headers(search_account)
            headers["x-client-transaction-id"] = search_account.get('headers', {}).get('x-client-transaction-id', '')
            
            # 准备请求参数
            variables = {
                "rawQuery": query,
                "count": 20,
                "querySource": "recent_search_click" if query and query[0] == '#' else "typed_query",
                "product": "Top"
            }
            
            # 如果提供了游标，添加到变量中
            if cursor:
                variables["cursor"] = cursor
            
            features = {
                "rweb_video_screen_enabled": False,"profile_label_improvements_pcf_label_in_post_enabled":False,"rweb_tipjar_consumption_enabled":True,
                "verified_phone_label_enabled":False,"creator_subscriptions_tweet_preview_api_enabled":True,"responsive_web_graphql_timeline_navigation_enabled":True,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":False,"premium_content_api_read_enabled":False,"communities_web_enable_tweet_community_results_fetch":True,"c9s_tweet_anatomy_moderator_badge_enabled":True,"responsive_web_grok_analyze_button_fetch_trends_enabled":False,"responsive_web_grok_analyze_post_followups_enabled":True,"responsive_web_jetfuel_frame":False,"responsive_web_grok_share_attachment_enabled":True,"articles_preview_enabled":True,"responsive_web_edit_tweet_api_enabled":True,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":True,"view_counts_everywhere_api_enabled":True,"longform_notetweets_consumption_enabled":True,"responsive_web_twitter_article_tweet_consumption_enabled":True,"tweet_awards_web_tipping_enabled":False,"responsive_web_grok_show_grok_translated_post":False,"responsive_web_grok_analysis_button_from_backend":True,"creator_subscriptions_quote_tweet_preview_enabled":False,"freedom_of_speech_not_reach_fetch_enabled":True,"standardized_nudges_misinfo":True,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":True,
                "longform_notetweets_rich_text_read_enabled":True,"longform_notetweets_inline_media_enabled":True,"responsive_web_grok_image_annotation_enabled":True,"responsive_web_enhance_cards_enabled":False
            }
            
            # 构建请求 URL
            endpoint = self.api_endpoints.get("search_timeline")
            if not endpoint:
                self.logger.error("无法获取 search_timeline API 端点")
                return (False, "无法获取 search_timeline API 端点", [], None)
            
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
                    if response.status != 200:
                        error_text = await response.text()
                        curl_command = self._generate_curl_command(url, headers)
                        self.logger.error(f"Twitter API 返回非 200 状态码: {response.status}, 内容: {error_text}, curl: {curl_command}")
                        return (False, f"HTTP {response.status}", [], None)
                    # 校验 Content-Type
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}, 内容: {error_text}")
                        return (False, f"Content-Type is not JSON: {content_type}", [], None)
                    response_data = await response.json()
            
            # 解析响应数据
            users = []
            next_cursor = None
            
            instructions = response_data.get("data", {}).get("search_by_raw_query", {}).get("search_timeline", {}).get("timeline", {}).get("instructions", [])
            
            for instruction in instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        # 提取下一页游标
                        if entry.get("entryId", "").startswith("cursor-bottom-"):
                            next_cursor = entry.get("content", {}).get("value", "")
                            continue
                            
                        if entry.get("entryId", "").startswith("tweet-"):
                            result = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                            user_result = result.get("core", {}).get("user_results", {}).get("result", {})
                            legacy = user_result.get("legacy", {})
                            if not user_result or not legacy:
                                continue
                            
                            # 获取用户简介
                            bio = legacy.get('description', '')
                            
                            # 从简介中提取邮箱
                            email_in_bio = await self._extract_email_from_text(bio)
                            username = user_result.get('core', {}).get('screen_name', '')
                            
                            user_data = {
                                "uid": user_result.get("rest_id", ""),
                                "username": username,
                                "nickname": user_result.get('core', {}).get('name', ''),
                                "is_verified": user_result.get('is_blue_verified', False),
                                "followers_count": legacy.get('followers_count', 0),
                                "following_count": legacy.get('friends_count', 0),
                                "tweet_count": legacy.get('statuses_count', 0),
                                "bio": bio,
                                "email_in_bio": email_in_bio,
                                "location": user_result.get('location', '').get('location', ''),
                                "url": f"https://x.com/{username}"
                            }
                            users.append(user_data)

                elif instruction.get("type") == "TimelineReplaceEntry":
                    entry = instruction.get("entry", {})
                    if not next_cursor and entry.get("entryId", "").startswith("cursor-bottom-"):
                        next_cursor = entry.get("content", {}).get("value", "")
                        continue

            return (True, "success", users, next_cursor)
            
        except Exception as e:
            self.logger.error(f"获取搜索用户页面失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return (False, str(e), [], None)

    async def _get_twitter_acounts_from_admin_service(self, account_type: str = "", count: int = 1) -> list:
        """通过服务发现获取admin的IP和端口，然后发送POST请求获取Twitter账号
        
        Args:
            account_type (str): 账号类型，'normal' 表示正常账号，'suspended' 表示挂起账号，空字符串''表示 'suspended' + 'normal', 默认为 ''
            count (int): 账号数量，默认为 1
        Returns:
            list: 账号列表，失败时返回空列表
        """

        try:
            self.logger.info(f"正在通过服务发现获取Twitter认证信息... account_type={account_type}")

            # 使用ServiceDiscovery发送POST请求到admin
            response = await ServiceDiscovery.post(
                service_name="admin",
                path="/v1/twitter/accounts/lock",
                json={
                    "count": count,
                    "account_type": account_type
                }  # 如果需要请求体，可以在这里添加
            )
            
            # 检查响应是否成功
            if response and response.get('accounts', []) and len(response.get('accounts', [])) > 0:
                twitter_accounts = response.get('accounts', [])
                self.logger.info(f"成功获取Twitter账号, 数量: {len(twitter_accounts)}, 类型: {account_type}")
                return twitter_accounts
            else:
                self.logger.error(f"获取Twitter账号失败: 响应格式不正确")
                return []
                
        except Exception as e:
            self.logger.error(f"获取Twitter账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
        
    async def _set_twitter_accounts(self, use_normal_accounts_fallback: bool = False) -> Tuple[bool, bool]:
        """设置Twitter账号

        Args:
            use_normal_fallback (bool): 是否用normal账号补充，默认为False
        Returns:
            Tuple[bool, bool]: (是否成功, 是否用normal账号补充)
        """
        try:
            if self.twitter_accounts:
                return True, False
            
            self.twitter_accounts = await self._get_twitter_acounts_from_admin_service("", self.twitter_accounts_need_count)
            if self.twitter_accounts:
                self.main_twitter_account = self.twitter_accounts[0]
                self.logger.info(f"成功获取Twitter账号, 数量: {len(self.twitter_accounts)}, 主账号: {self.main_twitter_account.get('username')}")
                return True, False
            else:
                # 如果允许用normal账号补充
                if use_normal_accounts_fallback and self.normal_accounts:
                    self.logger.info("尝试用normal账号补充...")
                    self.twitter_accounts = self.normal_accounts.copy()
                    self.main_twitter_account = self.twitter_accounts[0]
                    self.logger.info(f"成功用normal账号补充, 数量: {len(self.twitter_accounts)}, 主账号: {self.main_twitter_account.get('username')}")
                    return True, True
                else:
                    self.logger.error("获取Twitter账号失败")
                return False, False
        except Exception as e:
            self.logger.error(f"设置Twitter账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, False
    
    async def _set_normal_accounts(self) -> bool:
        """设置search专用Twitter账号

        Returns:
            bool: 是否成功
        """
        try:
            if self.normal_accounts:
                return True
            
            self.normal_accounts = await self._get_twitter_acounts_from_admin_service("normal", self.normal_accounts_need_count)
            if self.normal_accounts:
                self.logger.info(f"成功获取normal账号, 数量: {len(self.normal_accounts)}")
                return True
            else:
                self.logger.error("获取normal账号失败")
                return False
        except Exception as e:
            self.logger.error(f"设置normal账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
        
    async def _clear_twitter_accounts(self) -> bool:
        cleared = True
        # 清理通用账号
        if self.twitter_accounts:
            ids = [account.get("id") for account in self.twitter_accounts]
            response = await ServiceDiscovery.post(
                service_name="admin",
                path="/v1/twitter/accounts/unlock",
                json={"ids": ids}
            )
            if response.get("success", False):
                self.twitter_accounts = []
                # 重置账号的429错误计数
                self.account_rate_limit_count = {}
                self.logger.info("成功清理Twitter账号")
            else:
                self.logger.error("清理Twitter账号失败")
                cleared = False
        return cleared
    
    async def _clear_normal_accounts(self, delay: int = 60) -> bool:
        """清理search专用Twitter账号"""
        try:
            if self.normal_accounts:
                ids = [account.get("id") for account in self.normal_accounts]
                response = await ServiceDiscovery.post(
                    service_name="admin",
                    path="/v1/twitter/accounts/unlock",
                    json={"ids": ids, "delay": delay}  # 新增 delay 参数
                )
                if response.get("success", False):
                    self.normal_accounts = []
                    # 重置账号的429错误计数
                    self.account_rate_limit_count = {}
                    self.logger.info("成功清理Normal Twitter账号")
                    return True
                else:
                    self.logger.error("清理Normal Twitter账号失败")
                    return False
        except Exception as e:
            self.logger.error(f"清理Normal Twitter账号时发生错误: {str(e)}")
            
    async def cleanup(self):
        await super().cleanup()
        """清理Twitter账号"""
        self.logger.info("清理Twitter账号...")
        await self._clear_twitter_accounts()
        await self._clear_normal_accounts()
        self.selected_twitter_account = {}
        self.logger.info("资源清理完成")

    async def _get_available_twitter_account(self) -> Optional[Dict[str, Any]] | None:
        """获取可用的 similar 账号（自动冷却等待）
        Returns:
            Optional[Dict[str, Any]]: 可用的账号，如果没有则等待直到有
        """
        if not self.twitter_accounts:
            self.logger.info("没有twitter账号，请先获取...")
            return None
        while True:
            current_time = time.time()
            available_accounts = [acc for acc in self.twitter_accounts if acc.get("id") not in self.twitter_accounts_last_used or current_time - self.twitter_accounts_last_used[acc.get("id")] >= self.twitter_accounts_cooldown_seconds]
            if available_accounts:
                acc = available_accounts[0]
                self.twitter_accounts_last_used[acc.get("id")] = time.time()
                return acc
            self.logger.info(f"所有similar账号都在冷却中，等待 {self.twitter_accounts_cooldown_seconds} 秒...")
            await asyncio.sleep(self.twitter_accounts_cooldown_seconds)
