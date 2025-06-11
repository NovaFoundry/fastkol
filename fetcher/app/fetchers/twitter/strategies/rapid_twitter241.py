from .base import FetchUserTweetsStrategy
from app.settings import settings
import urllib.parse
import aiohttp
from typing import Dict, Any, Tuple, List
import asyncio
import json
from aiohttp import ClientError
from json import JSONDecodeError
from app.core.distributed_ratelimiter import DistributedRateLimiter

class RapidTwitter241Strategy(FetchUserTweetsStrategy):

    def __init__(self, twitter_fetcher: Any = None):
        super().__init__()
        self.twitter_fetcher = twitter_fetcher # 存储TwitterFetcher实例
        self.config = settings.get_config("twitter", {}).get("third_channels", {}).get("rapid_twitter241", {})
        self.url = self.config.get("url")
        self.x_rapidapi_host = self.config.get("x-rapidapi-host")
        self.x_rapidapi_key = self.config.get("x-rapidapi-key")
        max_requests_per_second = self.config.get("max_requests_per_second", 1)
        self.rate_limiter = DistributedRateLimiter(key='twitter:rapid_twitter241', rate_per_sec=max_requests_per_second)

    def _get_headers(self):
        return {
            "x-rapidapi-host": self.x_rapidapi_host,
            "x-rapidapi-key": self.x_rapidapi_key
        }
    
    async def _extract_tweet_data(self, result: Dict[str, Any], username: str = None) -> Dict[str, Any]:
        """Extract tweet data from a result object
        
        Args:
            result (Dict[str, Any]): The tweet result object
            username (str): The username of the tweet author, used for constructing tweet URL.
            
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
            "url": f"https://x.com/{username}/status/{tweet_id}"# Add tweet URL
        }
        
        return tweet_data

    async def fetch_user_tweets(
        self, uid: str, username: str, pages: int = 1, size: int = 20
    ) -> Tuple[bool, int, str, List[Any], List[Any]]:
        """
        只支持分页模式：调用方传 pages 和 size，返回前 pages 页（每页 size 条）。
        Args:
            uid (str): 用户ID
            username (str): 用户名
            pages (int): 页数，既前几页
            size (int): 每页条数，最大20，默认20
        Returns:
            Tuple[bool, int, str, List[Any], List[Any]]: (是否成功, 状态码, 消息, 置顶推文列表, 普通推文列表)
        """
        pin_tweets = []
        add_tweets = []
        cursor = None

        if not uid:
            self.logger.error("TwitterFetcher instance not provided to RapidTwitter241Strategy.")
            return False, 500, "Internal error: TwitterFetcher not available", pin_tweets, add_tweets
        if size > 20:
            return False, 400, "size 不能大于20", pin_tweets, add_tweets

        for _ in range(pages):
            ok, code, msg, pin_tweets, add_tweets, next_cursor = await self._fetch_user_tweets(
                uid=uid, username=username, count=size, cursor=cursor
            )
            if not ok:
                return ok, code, msg, pin_tweets, add_tweets
            pin_tweets.extend(pin_tweets)
            add_tweets.extend(add_tweets)
            if not next_cursor:
                break
            cursor = next_cursor

        return True, 200, "Success", pin_tweets, add_tweets
    
    async def _fetch_user_tweets(self, uid, username: str, count=20, cursor=None, ) -> Tuple[bool, int, str, List[Any], List[Any], str]:
        """
        获取用户推文列表
        Args:
            uid (str): 用户ID
            count (int): 要获取的推文数量
            cursor (str, optional): 分页游标，用于获取更多推文
            username (str, optional): The username of the tweet author, used for constructing tweet URL.
        Returns:
            Tuple[bool, int, str, List[Any], List[Any], str]: (是否成功, 状态码, 消息, 置顶推文列表, 普通推文列表, 下一页游标)
        """
        pin_tweets = []
        add_tweets = []
        next_cursor = None

        headers = self._get_headers()
        url = f"{self.url}/user-tweets"
        params = {
            "user": uid,
            "count": count
        }
        if cursor:
            params["cursor"] = cursor

        url = f"{url}?{urllib.parse.urlencode(params)}"
        try:
            await self.rate_limiter.acquire()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Rapid Twitter241 API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return (False, response.status, error_text, pin_tweets, add_tweets, next_cursor)
                    # 校验 Content-Type
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}, 内容: {error_text}")
                        return (False, response.status, f"Content-Type is not JSON: {content_type}", pin_tweets, add_tweets, next_cursor)
                    try:
                        response_data = await response.json()
                    except Exception as e:
                        error_text = await response.text()
                        self.logger.error(f"解析 JSON 失败: {e}, 内容: {error_text}")
                        return (False, response.status, f"JSON decode error: {e}", pin_tweets, add_tweets, next_cursor)
                    if not response_data:
                        return (False, response.status, "Empty response", pin_tweets, add_tweets, next_cursor)
                    
                    instructions = response_data.get("result", {}).get("timeline", {}).get("instructions", [])
                    for instruction in instructions:
                        # 提取置顶推文
                        if instruction.get("type") == "TimelinePinEntry":
                            tweet_result = instruction.get("entry", {}).get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                            tweet_data = await self._extract_tweet_data(tweet_result, username)
                            if tweet_data:
                                pin_tweets.append(tweet_data)
                            
                        # 提取普通推文
                        elif instruction.get("type") == "TimelineAddEntries":
                            entries = instruction.get("entries", [])
                            for entry in entries:
                                if entry.get("entryId", "").startswith("tweet-"):
                                    tweet_result = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                                    tweet_data = await self._extract_tweet_data(tweet_result, username)
                                    if tweet_data:
                                        add_tweets.append(tweet_data)
                                    
                                elif entry.get("entryId", "").startswith("profile-conversation-"):
                                    # 自己回复的推文，取原始推文数据
                                    items = entry.get("content", {}).get("items", [])
                                    if not items:
                                        continue
                                    result = items[0].get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                                    tweet_data = await self._extract_tweet_data(result, username)
                                    if tweet_data:
                                        add_tweets.append(tweet_data)
                    
                    return True, 200, "Success", pin_tweets, add_tweets, next_cursor
        except ClientError as e:
            self.logger.error(f"aiohttp ClientError: {e}")
            return (False, 502, f"Network error: {e}", pin_tweets, add_tweets, next_cursor)
        except asyncio.TimeoutError as e:
            self.logger.error(f"aiohttp TimeoutError: {e}")
            return (False, 504, f"Timeout error: {e}", pin_tweets, add_tweets, next_cursor)
        except JSONDecodeError as e:
            self.logger.error(f"JSONDecodeError: {e}")
            return (False, 500, f"JSON decode error: {e}", pin_tweets, add_tweets, next_cursor)
        except Exception as e:
            self.logger.error(f"未知异常: {e}")
            return (False, 500, f"Unknown error: {e}", pin_tweets, add_tweets, next_cursor)
                
    async def fetch_user_followings(
        self, uid: str, username: str, pages: int = 1, size: int = 70
    ) -> Tuple[bool, int, str, List[Any]]:
        """
        支持分页获取关注列表
        Args:
            uid (str): 用户ID
            username (str): 用户名
            pages (int): 页数
            size (int): 每页条数，最大70
        Returns:
            Tuple[bool, int, str, List[Any]]: (是否成功, 状态码, 消息, 关注列表)
        """
        all_followings = []
        cursor = None

        if not uid:
            self.logger.error("TwitterFetcher instance not provided to RapidTwitter241Strategy.")
            return False, 500, "Internal error: TwitterFetcher not available", []
        if size > 70:
            return False, 400, "size 不能大于70", []

        for _ in range(pages):
            ok, code, msg, followings, next_cursor = await self._fetch_user_followings(uid=uid, username=username, count=size, cursor=cursor)
            if not ok:
                return ok, code, msg, all_followings
            all_followings.extend(followings)
            if not next_cursor:
                break
            cursor = next_cursor

        return True, 200, "Success", all_followings

    async def _fetch_user_followings(self, uid, count=20, username: str = None, cursor=None) -> Tuple[bool, int, str, List[Any], str]:
        followings = []
        next_cursor = None

        headers = self._get_headers()
        url = f"{self.url}/followings"
        params = {
            "user": uid,
            "count": count
        }
        if cursor:
            params["cursor"] = cursor
        url = f"{url}?{urllib.parse.urlencode(params)}"

        try:
            await self.rate_limiter.acquire()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"Rapid Twitter241 API 返回非 200 状态码: {response.status}, 内容: {error_text}")
                        return (False, response.status, error_text, followings, next_cursor)
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error_text = await response.text()
                        self.logger.error(f"返回内容类型不是 JSON: {content_type}, 内容: {error_text}")
                        return (False, response.status, f"Content-Type is not JSON: {content_type}", followings, next_cursor)
                    try:
                        response_data = await response.json()
                    except Exception as e:
                        error_text = await response.text()
                        self.logger.error(f"解析 JSON 失败: {e}, 内容: {error_text}")
                        return (False, response.status, f"JSON decode error: {e}", followings, next_cursor)
                    if not response_data:
                        return (False, response.status, "Empty response", followings, next_cursor)

                    # 解析数据结构
                    instructions = response_data.get("result", {}).get("timeline", {}).get("instructions", [])
                    for instruction in instructions:
                        if instruction.get("type") == "TimelineAddEntries":
                            entries = instruction.get("entries", [])
                            for entry in entries:
                                if entry.get("entryId", "").startswith("user-"):
                                    user_result = entry.get("content", {}).get("itemContent", {}).get("user_results", {}).get("result", {})
                                    legacy = user_result.get("legacy", {})
                                    if not user_result or not legacy:
                                        continue
                                    followings.append({
                                        "uid": user_result.get("rest_id", ""),
                                        "username": legacy.get("screen_name", ""),
                                        "nickname": legacy.get("name", ""),
                                        "is_verified": legacy.get("verified", False),
                                        "followers_count": legacy.get("followers_count", 0),
                                        "following_count": legacy.get("friends_count", 0),
                                        "tweet_count": legacy.get("statuses_count", 0),
                                        "bio": legacy.get("description", ""),
                                        "location": legacy.get("location", ""),
                                        "url": f"https://x.com/{legacy.get('screen_name', '')}"
                                    })
                                elif entry.get("entryId", "").startswith("cursor-bottom-"):
                                    next_cursor = entry.get("content", {}).get("value", "")
                    return True, 200, "Success", followings, next_cursor
        except ClientError as e:
            self.logger.error(f"aiohttp ClientError: {e}")
            return (False, 502, f"Network error: {e}", followings, next_cursor)
        except asyncio.TimeoutError as e:
            self.logger.error(f"aiohttp TimeoutError: {e}")
            return (False, 504, f"Timeout error: {e}", followings, next_cursor)
        except JSONDecodeError as e:
            self.logger.error(f"JSONDecodeError: {e}")
            return (False, 500, f"JSON decode error: {e}", followings, next_cursor)
        except Exception as e:
            self.logger.error(f"未知异常: {e}")
            return (False, 500, f"Unknown error: {e}", followings, next_cursor)
                
