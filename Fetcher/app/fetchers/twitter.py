from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, Browser
import logging
import asyncio
from app.fetchers.base import BaseFetcher
from app.proxy.pool import ProxyPool
from app.account_pool.manager import AccountManager
from app.similarity.calculator import calculate_similarity

logger = logging.getLogger(__name__)

class TwitterFetcher(BaseFetcher):
    def __init__(self, proxy_pool: ProxyPool, account_manager: AccountManager):
        super().__init__(proxy_pool, account_manager)
        self.platform = "twitter"
    
    async def setup_browser(self):
        """设置浏览器实例"""
        proxy = await self.proxy_pool.get_proxy()
        account = await self.account_manager.get_account(self.platform)
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            proxy={
                "server": f"{proxy['host']}:{proxy['port']}",
                "username": proxy.get("username"),
                "password": proxy.get("password"),
            } if proxy else None
        )
        self.context = await self.browser.new_context()
        
        # 如果有账号信息，执行登录
        if account:
            await self.login(account)
    
    async def login(self, account: Dict[str, str]):
        """登录Twitter账号"""
        page = await self.context.new_page()
        
        try:
            await page.goto("https://twitter.com/i/flow/login")
            await page.wait_for_load_state("networkidle")
            
            # 输入用户名
            await page.fill('input[autocomplete="username"]', account["username"])
            await page.click('div[role="button"]:has-text("Next")')
            
            # 处理可能的电话号码验证
            try:
                phone_input = await page.wait_for_selector('input[autocomplete="tel"]', timeout=3000)
                if phone_input:
                    await phone_input.fill(account["phone"])
                    await page.click('div[role="button"]:has-text("Next")')
            except:
                # 无需电话验证，继续
                pass
            
            # 输入密码
            await page.fill('input[type="password"]', account["password"])
            await page.click('div[role="button"]:has-text("Log in")')
            
            # 等待登录完成
            await page.wait_for_selector('a[aria-label="Profile"]', timeout=10000)
            logger.info(f"成功登录Twitter账号: {account['username']}")
            
        except Exception as e:
            logger.error(f"Twitter登录失败: {str(e)}")
            await page.close()
            raise
        
        await page.close()
    
    async def fetch_user_profile(self, username: str) -> Dict[str, Any]:
        """获取用户主页信息"""
        page = await self.context.new_page()
        
        try:
            await page.goto(f"https://twitter.com/{username}")
            await page.wait_for_load_state("networkidle")
            
            # 获取基础信息
            follower_count = await self._get_follower_count(page)
            following_count = await self._get_following_count(page)
            tweet_count = await self._get_tweet_count(page)
            
            # 获取用户简介
            try:
                bio = await page.text_content('div[data-testid="UserDescription"]')
            except:
                bio = ""
            
            # 获取其他可见信息
            profile_data = {
                "username": username,
                "follower_count": follower_count,
                "following_count": following_count,
                "tweet_count": tweet_count,
                "bio": bio,
                # 可以添加更多数据字段
            }
            
            return profile_data
            
        except Exception as e:
            logger.error(f"获取用户资料失败 {username}: {str(e)}")
            raise
        finally:
            await page.close()
    
    async def get_recommended_users(self, username: str) -> List[Dict[str, Any]]:
        """获取推荐关注列表"""
        page = await self.context.new_page()
        recommended_users = []
        
        try:
            # 访问用户主页
            await page.goto(f"https://twitter.com/{username}")
            await page.wait_for_load_state("networkidle")
            
            # 寻找并点击"你可能喜欢"部分的"显示更多"按钮
            try:
                show_more_button = await page.wait_for_selector('span:has-text("Show more")', timeout=5000)
                if show_more_button:
                    await show_more_button.click()
            except:
                logger.info("没有找到'显示更多'按钮")
            
            # 获取推荐用户列表
            user_elements = await page.query_selector_all('div[data-testid="UserCell"]')
            
            for user_element in user_elements:
                # 获取用户名
                username_element = await user_element.query_selector('div[dir="ltr"] > span')
                if username_element:
                    username_text = await username_element.text_content()
                    # 去掉@符号
                    username_clean = username_text.replace('@', '')
                    
                    recommended_users.append({
                        "username": username_clean,
                    })
            
            return recommended_users
            
        except Exception as e:
            logger.error(f"获取推荐用户失败: {str(e)}")
            return []
        finally:
            await page.close()
    
    async def find_similar_users(self, username: str, count: int = 5) -> List[Dict[str, Any]]:
        """找到与指定用户相似的用户"""
        # 获取目标用户信息
        target_user = await self.fetch_user_profile(username)
        
        # 获取推荐用户列表
        recommended_users = await self.get_recommended_users(username)
        
        # 获取每个推荐用户的详细信息
        detailed_users = []
        for rec_user in recommended_users:
            try:
                user_profile = await self.fetch_user_profile(rec_user["username"])
                detailed_users.append(user_profile)
            except Exception as e:
                logger.error(f"获取用户 {rec_user['username']} 信息失败: {str(e)}")
        
        # 计算相似度
        for user in detailed_users:
            user["similarity"] = calculate_similarity(target_user, user)
        
        # 按相似度排序并返回前N个
        similar_users = sorted(detailed_users, key=lambda x: x["similarity"], reverse=True)
        return similar_users[:count]
    
    async def _get_follower_count(self, page: Page) -> int:
        """获取关注者数量"""
        try:
            followers_text = await page.text_content('a[href$="/followers"] span span')
            return self._parse_count(followers_text)
        except:
            return 0
    
    async def _get_following_count(self, page: Page) -> int:
        """获取正在关注的数量"""
        try:
            following_text = await page.text_content('a[href$="/following"] span span')
            return self._parse_count(following_text)
        except:
            return 0
    
    async def _get_tweet_count(self, page: Page) -> int:
        """获取推文数量"""
        try:
            tweet_count_text = await page.text_content('div[role="tablist"] a[role="tab"]:first-child div span span')
            return self._parse_count(tweet_count_text)
        except:
            return 0
    
    def _parse_count(self, count_text: str) -> int:
        """将数字文本转换为整数（处理 K, M 等缩写）"""
        count_text = count_text.replace(',', '')
        if 'K' in count_text:
            return int(float(count_text.replace('K', '')) * 1000)
        elif 'M' in count_text:
            return int(float(count_text.replace('M', '')) * 1000000)
        elif 'B' in count_text:
            return int(float(count_text.replace('B', '')) * 1000000000)
        else:
            try:
                return int(count_text)
            except:
                return 0 