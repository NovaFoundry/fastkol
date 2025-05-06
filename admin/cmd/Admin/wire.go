//go:build wireinject
// +build wireinject

// The build tag makes sure the stub is not built in the final build.

package main

import (
	"Admin/internal/biz"
	"Admin/internal/conf"
	"Admin/internal/data"
	"Admin/internal/registry"
	"Admin/internal/server"
	"Admin/internal/service"

	"github.com/go-kratos/kratos/v2"
	"github.com/go-kratos/kratos/v2/log"
	"github.com/google/wire"
)

// wireApp init kratos application.
func wireApp(confServer *conf.Server, confData *conf.Data, confRegistry *conf.Registry, logger log.Logger, bc *conf.Bootstrap) (*kratos.App, func(), error) {
	panic(wire.Build(server.ProviderSet, data.ProviderSet, biz.ProviderSet, service.ProviderSet, registry.ProviderSet, newApp))
}
