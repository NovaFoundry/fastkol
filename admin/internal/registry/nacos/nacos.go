package nacos

import (
	"Admin/internal/conf"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/go-kratos/kratos/v2/registry"
	"github.com/nacos-group/nacos-sdk-go/v2/clients"
	"github.com/nacos-group/nacos-sdk-go/v2/clients/naming_client"
	"github.com/nacos-group/nacos-sdk-go/v2/common/constant"
	"github.com/nacos-group/nacos-sdk-go/v2/vo"
)

// NewNacosRegistry 创建 Nacos 服务注册实例
func NewNacosRegistry(c *conf.Registry) (registry.Registrar, error) {
	// 获取当前工作目录
	workDir, err := os.Getwd()
	if err != nil {
		return nil, fmt.Errorf("获取工作目录失败: %v", err)
	}

	// 如果当前在cmd目录下，则回退到项目根目录
	if strings.HasSuffix(workDir, "/cmd") || strings.HasSuffix(workDir, "/cmd/Admin") {
		workDir = filepath.Dir(filepath.Dir(workDir))
	}

	// 设置默认的日志和缓存目录
	logDir := "log/nacos"
	cacheDir := "cache/nacos"

	// 如果配置中指定了日志和缓存目录，则使用配置中的值
	if c.Nacos.Client.LogDir != "" {
		logDir = c.Nacos.Client.LogDir
	}

	if c.Nacos.Client.CacheDir != "" {
		cacheDir = c.Nacos.Client.CacheDir
	}

	// 判断路径是否为绝对路径
	isAbsLogDir := filepath.IsAbs(logDir)
	isAbsCacheDir := filepath.IsAbs(cacheDir)

	// 如果是相对路径，则加上工作目录
	if !isAbsLogDir {
		logDir = filepath.Join(workDir, logDir)
	}

	if !isAbsCacheDir {
		cacheDir = filepath.Join(workDir, cacheDir)
	}

	clientConfig := constant.ClientConfig{
		NamespaceId:         c.Nacos.Client.Namespace,
		NotLoadCacheAtStart: true,
		LogDir:              logDir,
		CacheDir:            cacheDir,
		Username:            c.Nacos.Client.Username,
		Password:            c.Nacos.Client.Password,
	}

	serverConfigs := []constant.ServerConfig{
		{
			IpAddr:   c.Nacos.Client.Address,
			Port:     uint64(c.Nacos.Client.Port),
			GrpcPort: uint64(c.Nacos.Client.GrpcPort),
		},
	}

	client, err := clients.NewNamingClient(
		vo.NacosClientParam{
			ClientConfig:  &clientConfig,
			ServerConfigs: serverConfigs,
		},
	)
	if err != nil {
		return nil, fmt.Errorf("创建 Nacos 客户端失败: %v", err)
	}

	return &NacosRegistry{
		client: client,
		config: c,
	}, nil
}

// NacosRegistry Nacos 服务注册结构体
type NacosRegistry struct {
	client naming_client.INamingClient
	config *conf.Registry
}

// Register 注册服务到 Nacos
func (r *NacosRegistry) Register(ctx context.Context, service *registry.ServiceInstance) error {
	var errs []error

	// 注册 HTTP 服务
	if r.config.Nacos.Service.Port != 0 {
		httpParam := vo.RegisterInstanceParam{
			Ip:          r.config.Nacos.Service.Ip,
			Port:        uint64(r.config.Nacos.Service.Port),
			Weight:      float64(r.config.Nacos.Service.Weight),
			Enable:      r.config.Nacos.Service.Enabled,
			Healthy:     r.config.Nacos.Service.Healthy,
			Metadata:    service.Metadata,
			ServiceName: r.config.Nacos.Service.Name + "-http",
			GroupName:   r.config.Nacos.Service.Group,
			Ephemeral:   r.config.Nacos.Service.Ephemeral,
		}

		success, err := r.client.RegisterInstance(httpParam)
		if err != nil {
			errs = append(errs, fmt.Errorf("注册 HTTP 服务失败: %v", err))
		} else if !success {
			errs = append(errs, fmt.Errorf("注册 HTTP 服务失败: 返回失败"))
		}
	}

	// 注册 gRPC 服务
	if r.config.Nacos.Service.GrpcPort != 0 {
		grpcParam := vo.RegisterInstanceParam{
			Ip:          r.config.Nacos.Service.Ip,
			Port:        uint64(r.config.Nacos.Service.GrpcPort),
			Weight:      float64(r.config.Nacos.Service.Weight),
			Enable:      r.config.Nacos.Service.Enabled,
			Healthy:     r.config.Nacos.Service.Healthy,
			Metadata:    service.Metadata,
			ServiceName: r.config.Nacos.Service.Name + "-grpc",
			GroupName:   r.config.Nacos.Service.Group,
			Ephemeral:   r.config.Nacos.Service.Ephemeral,
		}

		success, err := r.client.RegisterInstance(grpcParam)
		if err != nil {
			errs = append(errs, fmt.Errorf("注册 gRPC 服务失败: %v", err))
		} else if !success {
			errs = append(errs, fmt.Errorf("注册 gRPC 服务失败: 返回失败"))
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("服务注册失败: %v", errs)
	}

	return nil
}

// Deregister 从 Nacos 注销服务
func (r *NacosRegistry) Deregister(ctx context.Context, service *registry.ServiceInstance) error {
	var errs []error

	// 注销 HTTP 服务
	if r.config.Nacos.Service.Port != 0 {
		httpParam := vo.DeregisterInstanceParam{
			Ip:          r.config.Nacos.Service.Ip,
			Port:        uint64(r.config.Nacos.Service.Port),
			ServiceName: r.config.Nacos.Service.Name + "-http",
			GroupName:   r.config.Nacos.Service.Group,
			Ephemeral:   r.config.Nacos.Service.Ephemeral,
		}

		success, err := r.client.DeregisterInstance(httpParam)
		if err != nil {
			errs = append(errs, fmt.Errorf("注销 HTTP 服务失败: %v", err))
		} else if !success {
			errs = append(errs, fmt.Errorf("注销 HTTP 服务失败: 返回失败"))
		}
	}

	// 注销 gRPC 服务
	if r.config.Nacos.Service.GrpcPort != 0 {
		grpcParam := vo.DeregisterInstanceParam{
			Ip:          r.config.Nacos.Service.Ip,
			Port:        uint64(r.config.Nacos.Service.GrpcPort),
			ServiceName: r.config.Nacos.Service.Name + "-grpc",
			GroupName:   r.config.Nacos.Service.Group,
			Ephemeral:   r.config.Nacos.Service.Ephemeral,
		}

		success, err := r.client.DeregisterInstance(grpcParam)
		if err != nil {
			errs = append(errs, fmt.Errorf("注销 gRPC 服务失败: %v", err))
		} else if !success {
			errs = append(errs, fmt.Errorf("注销 gRPC 服务失败: 返回失败"))
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("服务注销失败: %v", errs)
	}

	return nil
}
