import asyncio
import logging
import os
import uuid
import yaml
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager

from app.settings import settings
from app.rabbitmq.consumer import RabbitMQConsumer
from app.db.operations import init_db
from app.fetchers.twitter import TwitterFetcher
from app.core.config_manager import config_manager
from app.core.nacos_client import nacos_client
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
        
        # # 启动RabbitMQ消费者
        # logger.info("Starting RabbitMQ consumer...")
        # consumer = RabbitMQConsumer(
        #     url=settings.get_config("rabbitmq", {}).get("url", ""),
        #     queue=settings.get_config("rabbitmq", {}).get("queue", "")
        # )
        
        # # 启动消费者但不等待它完成
        # asyncio.create_task(consumer.start_consuming())
        
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
        
        # 关闭 RabbitMQ 消费者
        if 'consumer' in locals():
            await consumer.close()

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

async def run_fetcher(task_id: str, request: FetchRequest):
    """
    在后台运行爬虫任务
    
    Args:
        task_id: 任务ID
        request: 爬虫请求参数
    """
    try:
        tasks[task_id]["status"] = "running"
        
        # 根据平台选择对应的爬虫类
        if request.platform == "twitter":
            fetcher = TwitterFetcher()
            
            # 根据类型执行不同的爬虫方法
            if request.type == "similar":
                if not request.query:
                    raise ValueError("查找相似用户需要提供用户名")
                
                # 初始化浏览器
                await fetcher.init_browser()
                
                try:
                    # 执行爬虫
                    results = await fetcher.find_similar_users(request.query, request.count)
                    
                    # 应用关注者筛选
                    if request.follows and (request.follows.min is not None or request.follows.max is not None):
                        filtered_results = []
                        for user in results:
                            followers = user.get("followers_count", 0)
                            if (request.follows.min is None or followers >= request.follows.min) and \
                               (request.follows.max is None or followers <= request.follows.max):
                                filtered_results.append(user)
                        results = filtered_results
                    
                    # 更新任务状态和结果
                    tasks[task_id]["status"] = "completed"
                    tasks[task_id]["results"] = results
                    
                finally:
                    # 确保浏览器关闭
                    await fetcher.close_browser()
                    
            elif request.type == "search":
                # 实现搜索功能
                # ...
                pass
                
            elif request.type == "profile":
                if not request.query:
                    raise ValueError("获取用户资料需要提供用户名")
                
                # 初始化浏览器
                await fetcher.init_browser()
                
                try:
                    # 执行爬虫
                    result = await fetcher.fetch_user_profile(request.query)
                    
                    # 更新任务状态和结果
                    tasks[task_id]["status"] = "completed"
                    tasks[task_id]["results"] = [result]
                    
                finally:
                    # 确保浏览器关闭
                    await fetcher.close_browser()
        
        # 添加其他平台的处理逻辑
        # elif request.platform == "facebook":
        #     ...
        
        else:
            raise ValueError(f"不支持的平台: {request.platform}")
            
    except Exception as e:
        logger.error(f"任务 {task_id} 执行失败: {str(e)}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

# ============= API 路由 =============

# 基础路由
@app.get("/")
async def root():
    return {"message": "Welcome to Fetcher Service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 爬虫任务路由
@app.post("/fetch", response_model=TaskResponse)
async def fetch_data(request: FetchRequest, background_tasks: BackgroundTasks):
    """
    启动爬虫任务
    
    Args:
        request: 爬虫请求参数
        background_tasks: FastAPI 后台任务
        
    Returns:
        任务ID和状态
    """
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 初始化任务状态
    tasks[task_id] = {
        "status": "pending",
        "request": request.dict(),
        "results": None,
        "error": None
    }
    
    # 在后台启动爬虫任务
    background_tasks.add_task(run_fetcher, task_id, request)
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已创建并开始处理"
    )

@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态和结果
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态和结果
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    
    task = tasks[task_id]
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        results=task.get("results"),
        error=task.get("error")
    )

if __name__ == "__main__":
    asyncio.run(main()) 