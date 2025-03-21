package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/your-username/social-crawler/gateway/pkg/utils"
)

func JWTAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := c.GetHeader("Authorization")
		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "未提供认证token"})
			c.Abort()
			return
		}

		// 去掉Bearer前缀
		if len(token) > 7 && token[:7] == "Bearer " {
			token = token[7:]
		}

		// 验证JWT
		claims, err := utils.ParseJWT(token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "无效的token"})
			c.Abort()
			return
		}

		// 将用户信息存入上下文
		c.Set("userId", claims.UserId)
		c.Set("username", claims.Username)

		c.Next()
	}
}
