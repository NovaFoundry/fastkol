package registry

import (
	"Admin/internal/conf"
	"Admin/internal/registry/nacos"

	"github.com/go-kratos/kratos/v2/registry"
	"github.com/google/wire"
)

// ProviderSet 是 registry 的提供者集合
var ProviderSet = wire.NewSet(NewNacosRegistry)

// NewNacosRegistry 创建 Nacos 服务注册实例
func NewNacosRegistry(c *conf.Registry) (registry.Registrar, error) {
	return nacos.NewNacosRegistry(c)
}
