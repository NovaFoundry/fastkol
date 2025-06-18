package server

import (
	v1 "Admin/api/helloworld/v1"
	instagramv1 "Admin/api/instagram/v1"
	tiktokv1 "Admin/api/tiktok/v1"
	twitterv1 "Admin/api/twitter/v1"
	"Admin/internal/conf"
	"Admin/internal/service"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/go-kratos/kratos/v2/middleware/recovery"
	"github.com/go-kratos/kratos/v2/transport/grpc"
)

// NewGRPCServer new a gRPC server.
func NewGRPCServer(c *conf.Server, greeter *service.GreeterService, twitterAccount *service.TwitterAccountService, instagramAccount *service.InstagramAccountService, tikTokAccount *service.TikTokAccountService, logger log.Logger) *grpc.Server {
	var opts = []grpc.ServerOption{
		grpc.Middleware(
			recovery.Recovery(),
		),
	}
	if c.Grpc.Network != "" {
		opts = append(opts, grpc.Network(c.Grpc.Network))
	}
	if c.Grpc.Addr != "" {
		opts = append(opts, grpc.Address(c.Grpc.Addr))
	}
	if c.Grpc.Timeout != nil {
		opts = append(opts, grpc.Timeout(c.Grpc.Timeout.AsDuration()))
	}
	srv := grpc.NewServer(opts...)
	v1.RegisterGreeterServer(srv, greeter)
	twitterv1.RegisterTwitterAccountServer(srv, twitterAccount)
	instagramv1.RegisterInstagramAccountServer(srv, instagramAccount)
	tiktokv1.RegisterTikTokAccountServer(srv, tikTokAccount)
	return srv
}
