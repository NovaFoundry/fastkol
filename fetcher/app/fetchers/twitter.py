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
        self.twitter_accounts = []  # 所有Twitter账号
        self.selected_twitter_account = {}
    
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
    
    async def _random_delay(self, min_seconds=1, max_seconds=5):
        """随机延迟，模拟人类行为"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def fetch_user_profile(self, username: str) -> Dict[str, Any]:
        """获取用户主页信息"""
        self.logger.info(f"获取 Twitter 用户资料: {username}")
        if not await self.select_twitter_account():
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
            headers = {
                "authorization": self.selected_twitter_account.get('authToken', ''),
                "x-csrf-token": self.selected_twitter_account.get('csrfToken', ''),
                "cookie": self.selected_twitter_account.get('cookie', ''),
                "user-agent": self.user_agent,
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

    async def _get_user_hashtags(self, username: str, uid: str, bio: str = None) -> List[str]:
        """获取用户的 hashtag
        
        Args:
            username (str): 用户名
            uid (str): 用户ID
            
        Returns:
            List[str]: 用户最常用的 3-5 个 hashtag
        """
        try:
            # 如果 bio 为空，说明调用时没传bio，需要获取用户资料; 
            # 如果是空字符串，说明没获取到bio，没必要再去获取用户资料
            if bio is None:
                # 获取用户资料
                user_profile = await self.fetch_user_profile(username)
                bio = user_profile.get('bio', '')

            if bio:
                bio_hashtags = await self._extract_hashtags(bio)
            else:
                bio_hashtags = []
            
            # 获取用户最近的推文
            tweets = await self.fetch_user_tweets(username=username, count=20, uid=uid)
            
            # 从推文中提取 hashtag
            tweet_hashtags = []
            for tweet in tweets:
                tweet_hashtags.extend(await self._extract_hashtags(tweet.get('text', '')))
            
            # 合并所有 hashtag
            all_hashtags = bio_hashtags + tweet_hashtags
            
            # 统计 hashtag 出现频率
            hashtag_count = {}
            for tag in all_hashtags:
                hashtag_count[tag] = hashtag_count.get(tag, 0) + 1
            
            # 按频率排序并获取前 3-5 个
            sorted_hashtags = sorted(hashtag_count.items(), key=lambda x: x[1], reverse=True)
            top_hashtags = [tag for tag, _ in sorted_hashtags[:5]]
            print(f"用户 {username} 的 hashtag: {top_hashtags}")
            
            return top_hashtags
            
        except Exception as e:
            self.logger.error(f"获取用户 hashtag 失败: {str(e)}")
            return []

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

        if not await self.select_twitter_account():
            self.logger.error("未选择Twitter账号，无法查找相似用户")
            return (False, "未选择Twitter账号", [])
        
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
                    return (False, "无法获取用户 uid", [])

            # 用集合来存储已处理的用户ID，用于去重
            processed_uids = set()
            all_similar_users = []
            
            # 步骤1: 获取第一层相似用户
            first_level_users = await self._find_similar_users_by_uid(uid)
            self.logger.info(f"获取到第一层相似用户: {len(first_level_users)} 个")

            if len(first_level_users) >= count:
                all_similar_users = first_level_users[:count]
                # 获取用户的 hashtag
                # for user in all_similar_users:
                #     user["hashtags"] = await self._get_user_hashtags(user["username"], user["uid"], user["bio"])
                return (True, "success", all_similar_users)
            
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
                    users = await self._find_similar_users_by_uid(first_level_user["uid"])
                    self.logger.info(f"获取到{first_level_user['username']}第二层相似用户: {len(users)} 个")
                    if isinstance(users, list):  # 确保结果是有效的
                        second_level_users.extend(users)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 添加第二层用户(去重)
            for user in second_level_users:
                if user["uid"] not in processed_uids:
                    processed_uids.add(user["uid"])
                    all_similar_users.append(user)

            # 获取用户的 hashtag
            # for user in all_similar_users:
            #     user["hashtags"] = await self._get_user_hashtags(user["username"], user["uid"], user["bio"])
            #     # 添加随机延迟，避免请求过于频繁
            #     await self._random_delay(1, 2)
            
            # 确保返回数量不超过请求数量
            return (True, "success", all_similar_users[:count])
            
        except Exception as e:
            self.logger.error(f"查找相似用户失败: {str(e)}")
            return (False, str(e), [])

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

    async def _find_similar_users_by_uid(self, uid: str) -> List[Dict[str, Any]]:
        """通过用户ID获取相似用户
        
        Args:
            uid (str): 用户ID
            count (int): 要获取的用户数量
        
        Returns:
            List[Dict[str, Any]]: 相似用户列表
        """
        try:
            # 准备 API 请求头
            headers = {
                "authorization": self.selected_twitter_account.get('authToken', ''),
                "x-csrf-token": self.selected_twitter_account.get('csrfToken', ''),
                "cookie": self.selected_twitter_account.get('cookie', ''),
                "user-agent": self.user_agent,
                "content-type": "application/json",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "zh-cn"
            }
            
            # 准备请求参数
            variables = {
                "count": 20,
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
            "url": f"https://x.com/{username}/status/{tweet_id}"
        }
        
        return tweet_data

    async def _fetch_user_tweets_by_uid(self, uid: str, username: str, count: int, cursor: str = None) -> Dict[str, Any]:
        """通过用户ID获取推文列表
        
        Args:
            uid (str): 用户ID
            count (int): 要获取的推文数量
            cursor (str, optional): 分页游标，用于获取更多推文
            
        Returns:
            Dict[str, Any]: 包含推文列表和分页信息的字典
        """
        self.logger.info(f"获取用户 {username} 的推文列表，cursor: {cursor}")
        try:
            # 准备 API 请求头
            headers = {
                "authorization": self.selected_twitter_account.get('authToken', ''),
                "x-csrf-token": self.selected_twitter_account.get('csrfToken', ''),
                "cookie": self.selected_twitter_account.get('cookie', ''),
                "user-agent": self.user_agent,
                "content-type": "application/json",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "zh-cn"
            }
            
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
                return {"tweets": [], "next_cursor": None}
            
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
                            items = entry.get("content", {}).get("items", [])
                            for item in items:
                                result = item.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                                tweet_data = await self._extract_tweet_data(result, username)
                                if tweet_data:
                                    tweets.append(tweet_data)
                                    
                        # 提取下一页游标
                        elif entry.get("entryId", "").startswith("cursor-bottom-"):
                            next_cursor = entry.get("content", {}).get("value", "")
            
            return {
                "tweets": tweets,
                "next_cursor": next_cursor
            }
            
        except Exception as e:
            self.logger.error(f"获取用户推文失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"tweets": [], "next_cursor": None}

    async def fetch_user_tweets(self, username: str, count: int = 20, uid: str = None) -> List[Any]:
        """获取用户的推文列表
        
        Args:
            username (str): 用户名
            count (int): 要获取的推文数量）
            uid (str, optional): 用户ID，如果提供则使用此ID获取推文
            
        Returns:
            Dict[str, Any]: 包含推文列表和分页信息的字典
        """
        self.logger.info(f"获取用户 {username} 的推文列表，数量: {count}")
        
        try:
            # 如果没有提供 uid，先获取用户资料以获取 uid
            if not uid:
                self.logger.info(f"未提供 uid，尝试获取用户 {username} 的资料以获取 uid")
                user_profile = await self.fetch_user_profile(username)
                if user_profile and "uid" in user_profile:
                    uid = user_profile["uid"]
                    self.logger.info(f"成功获取用户 {username} 的 uid: {uid}")
                else:
                    self.logger.warning(f"无法获取用户 {username} 的 uid，将使用默认方式获取推文")
                    return []
            
            # 存储所有获取的推文
            all_tweets = []
            next_cursor = None
            
            # 循环获取推文，直到达到请求的数量或没有更多推文
            while len(all_tweets) < count:
                # 使用新的方法获取推文
                result = await self._fetch_user_tweets_by_uid(uid, username, min(100, count - len(all_tweets)), next_cursor)
                
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
            return all_tweets[:count]
            
        except Exception as e:
            self.logger.error(f"获取用户推文失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []

    async def find_users_by_search(self, query: str, count: int = 20) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """搜索用户
        
        Args:
            query (str): 搜索关键词
            count (int): 要获取的用户数量
            
        Returns:
            Tuple[bool, str, List[Dict[str, Any]]]: 成功状态，msg，用户列表
        """
        self.logger.info(f"搜索用户: {query}, 数量: {count}")
        
        if not await self.select_twitter_account():
            self.logger.error("未选择Twitter账号，无法搜索用户")
            return (False, "未选择Twitter账号", []) 
        
        try:
            # 存储所有获取的用户
            all_users = []
            # 用于去重的用户ID集合
            processed_uids = set()
            cursor = None
            # 记录连续没有新数据的次数
            no_new_data_count = 0
            # 上一次获取的用户数量
            last_user_count = 0
            
            self.logger.info(f"获取用户: {len(processed_uids)}/{count}")
            # 循环获取用户，直到达到请求的数量或没有更多用户
            while len(processed_uids) < count:
                # 使用新的方法获取用户
                users, cursor = await self._find_users_by_search(query, cursor)

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
                await self._random_delay(2, 5)
            
            # 确保返回数量不超过请求数量
            return (True, "success", all_users[:count])
            
        except Exception as e:
            error_msg = f"搜索用户失败: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            return (False, error_msg, [])

    async def _find_users_by_search(self, query: str, cursor: str = None) -> Tuple[List[Dict[str, Any]], str]:
        """通过搜索获取一页用户
        
        Args:
            query (str): 搜索关键词
            count (int): 要获取的用户数量
            cursor (str, optional): 分页游标，用于获取更多用户
            
        Returns:
            Tuple[List[Dict[str, Any]], str]: 用户列表, 下一页游标
        """
        try:
            # 准备 API 请求头
            headers = {
                "authorization": self.selected_twitter_account.get('authToken', ''),
                "x-csrf-token": self.selected_twitter_account.get('csrfToken', ''),
                "cookie": self.selected_twitter_account.get('cookie', ''),
                "user-agent": self.user_agent,
                "content-type": "application/json",
                "x-twitter-active-user": "yes",
                "x-twitter-client-language": "zh-cn"
            }
            
            # 准备请求参数
            variables = {
                "rawQuery": query,
                "count": 20,
                "querySource": "typed_query",
                "product": "Top"
            }
            
            # 如果提供了游标，添加到变量中
            if cursor:
                variables["cursor"] = cursor
            
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
                "responsive_web_grok_show_grok_translated_post": False,
                "responsive_web_grok_analysis_button_from_backend": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_grok_image_annotation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            }
            
            # 构建请求 URL
            endpoint = self.api_endpoints.get("search_timeline")
            if not endpoint:
                self.logger.error("无法获取 search_timeline API 端点")
                return ([], None)
            
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
                            
                            user_data = {
                                "uid": user_result.get("rest_id", ""),
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
                            users.append(user_data)

                elif instruction.get("type") == "TimelineReplaceEntry":
                    entry = instruction.get("entry", {})
                    if not next_cursor and entry.get("entryId", "").startswith("cursor-bottom-"):
                        next_cursor = entry.get("content", {}).get("value", "")
                        continue

            return (users, next_cursor)
            
        except Exception as e:
            self.logger.error(f"获取搜索用户页面失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return ([], None)

    async def _get_twitter_acounts_from_admin_service(self) -> bool:
        """通过服务发现获取admin的IP和端口，然后发送POST请求获取Twitter账号
        
        Returns:
            Dict[str, str]: 包含authToken、csrfToken和cookie的字典
        """
        if self.twitter_accounts:
            return True

        try:
            self.logger.info("正在通过服务发现获取Twitter认证信息...")

            # 使用ServiceDiscovery发送POST请求到admin
            response = await ServiceDiscovery.post(
                service_name="admin",
                path="/v1/twitter/accounts/lock",
                json={}  # 如果需要请求体，可以在这里添加
            )
            
            # 检查响应是否成功
            if response and response.get('accounts', []) and len(response.get('accounts', [])) > 0:
                self.twitter_accounts = response.get('accounts', [])
                self.logger.info(f"成功获取Twitter账号, 数量: {len(self.twitter_accounts)}")
                return True
            else:
                self.logger.error(f"获取Twitter账号失败: 响应格式不正确")
                return False
                
        except Exception as e:
            self.logger.error(f"获取Twitter账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    async def select_twitter_account(self) -> bool:
        """选择一个Twitter账号
        
        Returns:
            Dict[str, str]: 包含authToken、csrfToken和cookie的字典
        """
        try:
            
            # 如果已经有认证信息，则不需要重新获取
            if self.selected_twitter_account:
                self.logger.info("已有Twitter账号，无需重新获取")
                return True
                
            # 从admin获取认证信息
            await self._get_twitter_acounts_from_admin_service()
            if self.twitter_accounts:
                self.selected_twitter_account = self.twitter_accounts[0]
                self.logger.info(f"成功选择Twitter账号: {self.selected_twitter_account.get('username')}")
                return True
            else:
                self.logger.error("获取Twitter账号失败")
                return False
                
        except Exception as e:
            self.logger.error(f"选择Twitter账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        
    async def _clear_twitter_accounts(self) -> bool:
        if not self.twitter_accounts:
            return True
        try:
            ids = [account.get("id") for account in self.twitter_accounts]
            # 使用ServiceDiscovery发送POST请求到admin
            response = await ServiceDiscovery.post(
                service_name="admin",
                path="/v1/twitter/accounts/unlock",
                json={"ids": ids}  # 如果需要请求体，可以在这里添加
            )
            if response.get("success", False):
                self.twitter_accounts = []
                self.logger.info("成功清理Twitter账号")
                return True
            else:
                self.logger.error("清理Twitter账号失败")
                return False
        
        except Exception as e:
            self.logger.error(f"清理Twitter账号时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    async def cleanup(self):
        await super().cleanup()
        """清理Twitter账号"""
        self.logger.info("清理Twitter账号...")
        await self._clear_twitter_accounts()
        self.selected_twitter_account = {}
        self.logger.info("资源清理完成")
