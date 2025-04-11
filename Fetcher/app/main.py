import asyncio
import logging
import os
import uuid
import yaml
import time
import hashlib
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

from app.settings import settings
from app.rabbitmq.consumer import RabbitMQConsumer
from app.db.operations import init_db, update_fetch_task, SessionLocal, get_fetch_task
from app.fetchers.twitter import TwitterFetcher
from app.core.config_manager import config_manager
from app.core.nacos_client import nacos_client
from app.celery_app import app as celery_app
from celery.result import AsyncResult
from app.db.operations import create_fetch_task
from sqlalchemy.future import select
# 导入其他平台的爬虫类

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 存储爬虫任务状态和结果
tasks = {}

# 定义 lifespan 上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    logger.info("Fetcher Service starting up")
    
    try:
        # 初始化配置管理器
        logger.info("Initializing configuration manager...")
        config_manager.initialize()
        
        # 注册服务到 Nacos
        logger.info("Registering service to Nacos...")
        if not nacos_client.register_service():
            logger.warning("Failed to register service to Nacos")
        
        # 初始化数据库连接
        logger.info("Initializing database connection...")
        await init_db()
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # 关闭逻辑
        logger.info("Fetcher Service shutting down")
        
        # 注销 Nacos 服务
        logger.info("Deregistering service from Nacos...")
        nacos_client.deregister_service()

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.get_config("fastapi", {}).get("title", "Fetcher Service"),
    description=settings.get_config("fastapi", {}).get("description", "Service for fetching data from various sources"),
    version=settings.get_config("fastapi", {}).get("version", "0.1.0"),
    docs_url=settings.get_config("fastapi", {}).get("docs_url", "/docs"),
    redoc_url=settings.get_config("fastapi", {}).get("redoc_url", "/redoc"),
    openapi_url=settings.get_config("fastapi", {}).get("openapi_url", "/openapi.json"),
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============= 爬虫 API 模型 =============

class FollowsFilter(BaseModel):
    """关注者数量筛选模型"""
    min: Optional[int] = Field(None, description="最小关注者数量")
    max: Optional[int] = Field(None, description="最大关注者数量")
    
    @field_validator('min', 'max')
    @classmethod
    def validate_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('关注者数量不能为负数')
        return v

class FetchRequest(BaseModel):
    """爬虫请求模型"""
    platform: str = Field(..., description="平台名称，例如 'twitter'")
    type: str = Field(..., description="爬虫类型，例如 'similar' 或 'search'")
    query: Optional[str] = Field(None, description="搜索查询或用户名")
    count: int = Field(10, description="返回结果数量")
    follows: Optional[FollowsFilter] = Field(None, description="关注者数量筛选")
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        valid_platforms = ['twitter', 'facebook', 'instagram']
        if v.lower() not in valid_platforms:
            raise ValueError(f'不支持的平台: {v}. 支持的平台: {", ".join(valid_platforms)}')
        return v.lower()
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        valid_types = ['similar', 'search', 'profile']
        if v.lower() not in valid_types:
            raise ValueError(f'不支持的类型: {v}. 支持的类型: {", ".join(valid_types)}')
        return v.lower()
    
    @field_validator('count')
    @classmethod
    def validate_count(cls, v):
        if v <= 0:
            raise ValueError('count 必须大于 0')
        if v > 100:
            raise ValueError('count 不能超过 100')
        return v

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

# ============= 爬虫任务处理函数 =============

# ============= API 路由 =============

# 基础路由
@app.get("/")
async def root():
    return {"message": "Welcome to Fetcher Service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def generate_task_id(platform: str, action: str) -> str:
    """
    生成基于时间、平台和操作类型的32位任务ID
    
    Args:
        platform: 平台名称 (如 'twitter')
        action: 操作类型 (如 'similar', 'search', 'profile')
        
    Returns:
        32位的任务ID字符串
    """
    # 获取当前时间戳（精确到毫秒）
    timestamp = int(time.time() * 1000)
    
    # 构建原始字符串：时间戳_平台_操作类型
    raw_string = f"{timestamp}_{platform}_{action}"
    
    # 使用 MD5 生成 32 位的哈希值
    task_id = hashlib.md5(raw_string.encode()).hexdigest()
    
    return task_id

# 爬虫任务路由
@app.post("/fetch", response_model=TaskResponse)
async def fetch_data(request: FetchRequest):
    """
    启动爬虫任务
    
    Args:
        request: 爬虫请求参数
        
    Returns:
        任务ID和状态
    """
    # 生成任务ID
    task_id = generate_task_id(request.platform, request.type)
    
    # 初始化任务状态
    tasks[task_id] = {
        "status": "pending",
        "request": request.dict(),
        "results": None,
        "error": None
    }
    
    # 准备任务数据
    task_data = {
        "task_id": task_id,
        "platform": request.platform,
        "action": request.type,
        "params": {
            "username": request.query,
            "count": request.count,
            "follows_min": request.follows.min if request.follows else None,
            "follows_max": request.follows.max if request.follows else None
        }
    }
    
    await create_fetch_task(task_data, "pending")

    # 将任务发送到 Celery
    celery_task = celery_app.send_task('app.celery_app.process_task', args=[task_data])
    logger.info(f"任务已发送, task_id: {task_id}, celery_task_id: {celery_task.id}")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已创建"
    )

@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态和结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态和结果
        
    Raises:
        HTTPException: 当任务不存在时返回404错误
    """
    # 从数据库获取任务信息
    task = await get_fetch_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task with ID {task_id} not found"
        )
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task.status,
        results=task.result,
        error=task.error
    )

if __name__ == "__main__":
    asyncio.run(main()) 