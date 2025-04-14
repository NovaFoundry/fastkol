package main

import (
	"log"

	"github.com/gin-gonic/gin"
	"github.com/your-username/social-crawler/gateway/internal/config"
	"github.com/your-username/social-crawler/gateway/internal/handlers"
	"github.com/your-username/social-crawler/gateway/internal/middleware"
	"github.com/your-username/social-crawler/gateway/internal/services"
	"github.com/your-username/social-crawler/gateway/pkg/rabbitmq"
)

func main() {
	// 加载配置
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 初始化RabbitMQ
	mqClient, err := rabbitmq.NewClient(cfg.RabbitMQ.URL)
	if err != nil {
		log.Fatalf("Failed to connect to RabbitMQ: %v", err)
	}
	defer mqClient.Close()

	// 初始化数据库
	// db, err := database.Connect(cfg.Database)

	// 设置Gin路由
	r := gin.Default()

	// 注册中间件
	r.Use(middleware.Logger())

	// 公开API
	public := r.Group("/api/v1")
	{
		authHandler := handlers.NewAuthHandler( /* dependencies */ )
		public.POST("/register", authHandler.Register)
		public.POST("/login", authHandler.Login)
	}

	// 需要鉴权的API
	authorized := r.Group("/api/v1")
	authorized.Use(middleware.JWTAuth())
	{
		crawlerHandler := handlers.NewCrawlerHandler(mqClient /* other dependencies */)
		authorized.POST("/tasks", crawlerHandler.CreateTask)
		authorized.GET("/tasks", crawlerHandler.ListTasks)
		authorized.GET("/tasks/:id", crawlerHandler.GetTask)
		authorized.GET("/tasks/:id/results", crawlerHandler.GetTaskResults)
	}

	// 初始化资源服务
	resourceService := services.NewResourceService(db, mqClient)
	resourceHandler := handlers.NewResourceHandler(resourceService)

	// 资源管理API (需要管理员权限)
	admin := r.Group("/api/v1/resources")
	admin.Use(middleware.JWTAuth(), middleware.AdminRequired())
	{
		// 代理管理
		admin.GET("/proxies", resourceHandler.GetProxies)
		admin.POST("/proxies", resourceHandler.AddProxy)
		admin.DELETE("/proxies/:id", resourceHandler.DeleteProxy)
		admin.POST("/proxies/report", resourceHandler.ReportProxyStatus)

		// 账号管理
		admin.GET("/accounts", resourceHandler.GetAccounts)
		admin.POST("/accounts", resourceHandler.AddAccount)
		admin.DELETE("/accounts/:id", resourceHandler.DeleteAccount)
		admin.PUT("/accounts/:id/status", resourceHandler.UpdateAccountStatus)

		// 资源统计
		admin.GET("/stats", resourceHandler.GetResourceStats)
	}

	// 启动服务器
	if err := r.Run(cfg.Server.Address); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
