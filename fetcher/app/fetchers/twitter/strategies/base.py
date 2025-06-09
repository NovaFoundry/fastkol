from typing import Tuple, List, Any, Dict
from app.fetchers.base import BaseFetcher

class FetchUserTweetsStrategy(BaseFetcher):
    async def fetch_user_tweets(self, username: str, count: int = 20, uid: str = None, twitter_account: Dict[str, Any] = None) -> Tuple[bool, int, str, List[Any]]:
        raise NotImplementedError 