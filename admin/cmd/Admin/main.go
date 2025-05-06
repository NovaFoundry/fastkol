package main

import (
	"flag"
	"fmt"
	"os"

	"Admin/internal/conf"

	"github.com/go-kratos/kratos/contrib/registry/consul/v2"
	"github.com/go-kratos/kratos/v2"
	"github.com/go-kratos/kratos/v2/config"
	"github.com/go-kratos/kratos/v2/config/file"
	"github.com/go-kratos/kratos/v2/log"
	"github.com/go-kratos/kratos/v2/middleware/tracing"
	"github.com/go-kratos/kratos/v2/registry"
	"github.com/go-kratos/kratos/v2/transport/grpc"
	"github.com/go-kratos/kratos/v2/transport/http"
	consulapi "github.com/hashicorp/consul/api"

	_ "go.uber.org/automaxprocs"
)

// go build -ldflags "-X main.Version=x.y.z"
var (
	// Name is the name of the compiled software.
	Name string = "admin"
	// Version is the version of the compiled software.
	Version string = "1.0.0"
	// flagconf is the config flag.
	flagconf string

	// id, _ = os.Hostname()
	id = "admin"
)

func init() {
	flag.StringVar(&flagconf, "conf", "../../configs/config.yaml", "config path, eg: -conf config.yaml")
}

func newApp(bc *conf.Bootstrap, logger log.Logger, gs *grpc.Server, hs *http.Server, registrar registry.Registrar) *kratos.App {
	cfg := consulapi.DefaultConfig()
	cfg.Address = fmt.Sprintf("%s:%d", bc.Registry.Consul.Server.Host, bc.Registry.Consul.Server.Port)
	cfg.Scheme = bc.Registry.Consul.Server.Scheme
	cfg.Token = bc.Registry.Consul.Server.Token
	cfg.Datacenter = bc.Registry.Consul.Server.Datacenter

	// new consul client
	client, err := consulapi.NewClient(cfg)
	if err != nil {
		panic(err)
	}
	// new reg with consul client
	reg := consul.New(client)
	gs.Endpoint()
	return kratos.New(
		kratos.ID(id),
		kratos.Name(Name),
		kratos.Version(Version),
		kratos.Metadata(bc.Registry.Consul.Service.Metadata),
		kratos.Logger(logger),
		kratos.Server(
			hs,
			gs,
		),
		kratos.Registrar(reg),
	)
}

func main() {
	flag.Parse()
	logger := log.With(log.NewStdLogger(os.Stdout),
		"ts", log.DefaultTimestamp,
		"caller", log.DefaultCaller,
		"service.id", id,
		"service.name", Name,
		"service.version", Version,
		"trace.id", tracing.TraceID(),
		"span.id", tracing.SpanID(),
	)
	c := config.New(
		config.WithSource(
			file.NewSource(flagconf),
		),
	)
	defer c.Close()

	if err := c.Load(); err != nil {
		panic(err)
	}

	var bc conf.Bootstrap
	if err := c.Scan(&bc); err != nil {
		panic(err)
	}

	app, cleanup, err := wireApp(bc.Server, bc.Data, bc.Registry, logger, &bc)
	if err != nil {
		panic(err)
	}
	defer cleanup()

	// start and wait for stop signal
	if err := app.Run(); err != nil {
		panic(err)
	}
}
