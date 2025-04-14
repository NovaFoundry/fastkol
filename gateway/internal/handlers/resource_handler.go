package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/your-username/social-crawler/gateway/internal/services"
)

type ResourceHandler struct {
	resourceService *services.ResourceService
}

func NewResourceHandler(resourceService *services.ResourceService) *ResourceHandler {
	return &ResourceHandler{
		resourceService: resourceService,
	}
}

// 获取所有代理IP
func (h *ResourceHandler) GetProxies(c *gin.Context) {
	proxies, err := h.resourceService.GetAllProxies()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取代理列表失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"data": proxies})
}

// 添加新代理
func (h *ResourceHandler) AddProxy(c *gin.Context) {
	var proxy services.ProxyInfo
	if err := c.ShouldBindJSON(&proxy); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.resourceService.AddProxy(proxy); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "添加代理失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "代理添加成功"})
}

// 获取所有账号
func (h *ResourceHandler) GetAccounts(c *gin.Context) {
	platform := c.Query("platform")
	accounts, err := h.resourceService.GetAccounts(platform)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取账号列表失败"})
		return
	}

	// 敏感信息脱敏
	var safeAccounts []map[string]interface{}
	for _, acc := range accounts {
		safeAccounts = append(safeAccounts, map[string]interface{}{
			"id":       acc.ID,
			"platform": acc.Platform,
			"username": acc.Username,
			"status":   acc.Status,
			// 不返回密码等敏感信息
		})
	}

	c.JSON(http.StatusOK, gin.H{"data": safeAccounts})
}

// 添加新账号
func (h *ResourceHandler) AddAccount(c *gin.Context) {
	var account services.AccountInfo
	if err := c.ShouldBindJSON(&account); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.resourceService.AddAccount(account); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "添加账号失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "账号添加成功"})
}

// 获取代理和账号使用情况统计
func (h *ResourceHandler) GetResourceStats(c *gin.Context) {
	stats, err := h.resourceService.GetResourceStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "获取资源统计失败"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"data": stats})
}
