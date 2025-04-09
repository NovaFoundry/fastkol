from sqlalchemy import Column, Integer, String, JSON, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class FetchResult(Base):
    """爬取结果模型"""
    __tablename__ = 'fetch_results'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(50), index=True)
    platform = Column(String(20), index=True)
    action = Column(String(50))
    params = Column(JSON)
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<FetchResult(task_id='{self.task_id}', platform='{self.platform}')>"

class Proxy(Base):
    """代理模型"""
    __tablename__ = 'proxies'
    
    id = Column(Integer, primary_key=True)
    host = Column(String(100))
    port = Column(Integer)
    username = Column(String(100), nullable=True)
    password = Column(String(100), nullable=True)
    protocol = Column(String(10), default='http')
    is_active = Column(Integer, default=1)
    
    def __repr__(self):
        return f"<Proxy(host='{self.host}', port={self.port})>" 