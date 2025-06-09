from .rapid_twitter241 import RapidTwitter241Strategy
from typing import Any

def get_fetch_user_tweets_strategy(channel: str, twitter_fetcher: Any = None):
    if channel == "rapid_twitter241":
        return RapidTwitter241Strategy(twitter_fetcher)
    return None 