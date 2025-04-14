def calculate_similarity(user1, user2):
    """
    计算两个用户之间的相似度
    这是一个简化的实现，实际应用中可能需要更复杂的算法
    """
    # 简单的相似度计算，基于关注者数量和关注数量的差异
    follower_diff = abs(user1.get("follower_count", 0) - user2.get("follower_count", 0))
    following_diff = abs(user1.get("following_count", 0) - user2.get("following_count", 0))
    
    # 归一化差异值
    max_followers = max(user1.get("follower_count", 1), user2.get("follower_count", 1), 1)
    max_following = max(user1.get("following_count", 1), user2.get("following_count", 1), 1)
    
    normalized_follower_diff = follower_diff / max_followers
    normalized_following_diff = following_diff / max_following
    
    # 计算相似度 (1 - 平均差异)
    similarity = 1 - ((normalized_follower_diff + normalized_following_diff) / 2)
    
    return similarity 