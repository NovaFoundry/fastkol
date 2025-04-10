from sqlalchemy import Column, Integer, String, JSON, DateTime, Text, Enum, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class FetchTask(Base):
    """爬取结果模型"""
    __tablename__ = 'fetch_tasks'
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name='status_check'),
        {'sqlite_autoincrement': True},  # 确保自增主键
    )
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(50), unique=True, index=True)  # 添加唯一约束
    platform = Column(String(20))
    action = Column(String(50))
    params = Column(JSON)
    result = Column(JSON, nullable=True)  # 成功的结果
    error = Column(Text, nullable=True)   # 错误信息
    status = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<FetchTask(task_id='{self.task_id}', platform='{self.platform}')>"