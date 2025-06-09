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
from sqlalchemy import text

from app.settings import settings
from app.db.operations import init_db, update_fetch_task, SessionLocal, get_fetch_task
from app.fetchers.twitter import TwitterFetcher
# from app.core.config_manager import config_manager
from app.core.consul_client import consul_client
from app.celery_app import app as celery_app
from celery.result import AsyncResult
from app.db.operations import create_fetch_task
from sqlalchemy.future import select
import uvicorn
from uvicorn.logging import DefaultFormatter
# 导入其他平台的爬虫类

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置 FastAPI 的访问日志
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(logging.INFO)
formatter = DefaultFormatter(
    fmt="%(asctime)s - %(levelprefix)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    use_colors=True
)
for handler in uvicorn_logger.handlers:
    handler.setFormatter(formatter)

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
        # config_manager.initialize()
        
        # # 注册服务到 Nacos
        # logger.info("Registering service to Nacos...")
        # if not nacos_client.register_service():
        #     logger.warning("Failed to register service to Nacos")
            
        # 注册服务到 Consul
        logger.info("Registering service to Consul...")
        try:
            consul_client.register_service()
            logger.info("Successfully registered service to Consul")
        except Exception as e:
            logger.error(f"Failed to register service to Consul: {e}")
        
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
        
        # # 注销 Nacos 服务
        # logger.info("Deregistering service from Nacos...")
        # nacos_client.deregister_service()
        
        # 注销 Consul 服务
        logger.info("Deregistering service from Consul...")
        try:
            consul_client.deregister_service()
            logger.info("Successfully deregistered service from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister service from Consul: {e}")

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

class FetchSimilarRequest(BaseModel):
    """爬虫请求模型"""
    platform: str = Field(..., description="平台名称，例如 'twitter'")
    username: str = Field(..., description="用户名")
    uid: Optional[str] = Field(None, description="用户ID")
    count: int = Field(50, description="返回结果数量")
    follows: Optional[FollowsFilter] = Field(None, description="关注者数量筛选")
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        valid_platforms = ['twitter', 'facebook', 'instagram']
        if v.lower() not in valid_platforms:
            raise ValueError(f'不支持的平台: {v}. 支持的平台: {", ".join(valid_platforms)}')
        return v.lower()
    
    @field_validator('count')
    @classmethod
    def validate_count(cls, v):
        if v <= 0:
            raise ValueError('count 必须大于 0')
        if v > 100:
            raise ValueError('count 不能超过 100')
        return v
    
class FetchSearchRequest(BaseModel):
    """爬虫请求模型"""
    platform: str = Field(..., description="平台名称，例如 'twitter'")
    query: str = Field(..., description="搜索关键词")
    count: int = Field(20, description="返回结果数量")
    follows: Optional[FollowsFilter] = Field(None, description="关注者数量筛选")
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        valid_platforms = ['twitter', 'facebook', 'instagram']
        if v.lower() not in valid_platforms:
            raise ValueError(f'不支持的平台: {v}. 支持的平台: {", ".join(valid_platforms)}')
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
    """健康检查端点
    
    Returns:
        dict: 包含服务健康状态的详细信息
    """
    # 获取当前时间戳
    current_time = int(time.time())
    
    # 检查数据库连接
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # 检查 Celery 状态
    try:
        celery_status = "healthy" if celery_app.control.ping() else "unhealthy"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        celery_status = "unhealthy"
    
    return {
        "status": "ok",
        "timestamp": current_time,
        "components": {
            "database": {
                "status": db_status
            },
            "celery": {
                "status": celery_status
            }
        }
    }

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
@app.post("/fetch/similar", response_model=TaskResponse)
async def fetch_similar(request: FetchSimilarRequest):
    """
    启动相似用户查找任务
    
    Args:
        request: 爬虫请求参数
        
    Returns:
        任务ID和状态
    """
    # 生成任务ID
    task_id = generate_task_id(request.platform, "similar")
    
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
        "action": "similar",
        "params": {
            "username": request.username,
            "uid": request.uid,
            "count": request.count,
            "follows": request.follows.dict() if request.follows else None
        }
    }
    
    await create_fetch_task(task_data, "pending")

    # 将任务发送到专门的 Celery 任务
    celery_task = celery_app.send_task('app.celery_app.process_similar_task', args=[task_data])
    logger.info(f"{request.platform} 平台 similar 任务已发送, task_id: {task_id}, celery_task_id: {celery_task.id}")

    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已创建"
    )

@app.post("/fetch/search", response_model=TaskResponse)
async def fetch_search(request: FetchSearchRequest):
    """
    启动用户搜索任务
    
    Args:
        request: 爬虫请求参数
        
    Returns:
        任务ID和状态
    """
    # 生成任务ID
    task_id = generate_task_id(request.platform, "search")
    
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
        "action": "search",
        "params": {
            "query": request.query,
            "count": request.count,
            "follows": request.follows.dict() if request.follows else None
        }
    }
    
    await create_fetch_task(task_data, "pending")

    # 将任务发送到专门的 Celery 任务
    celery_task = celery_app.send_task('app.celery_app.process_search_task', args=[task_data])
    logger.info(f"{request.platform} 平台 search 任务已发送, task_id: {task_id}, celery_task_id: {celery_task.id}")

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