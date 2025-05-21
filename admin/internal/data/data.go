package data

import (
	"Admin/internal/conf"
	"context"
	"time"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/postgres"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	"github.com/google/wire"
	"github.com/redis/go-redis/v9"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// ProviderSet is data providers.
var ProviderSet = wire.NewSet(NewData, NewGreeterRepo, NewTwitterAccountRepo)

// Data .
type Data struct {
	db    *gorm.DB
	redis *redis.Client
	log   *log.Helper
}

// NewData .
func NewData(c *conf.Data, logger log.Logger) (*Data, func(), error) {
	helper := log.NewHelper(log.With(logger, "module", "data"))

	db, err := gorm.Open(postgres.Open(c.Database.Source), &gorm.Config{})
	if err != nil {
		return nil, nil, err
	}

	// 设置连接池参数
	sqlDB, err := db.DB()
	if err != nil {
		return nil, nil, err
	}
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)

	// 运行数据库迁移
	m, err := migrate.New(
		"file://../../migrations",
		c.Database.Source,
	)
	if err != nil {
		return nil, nil, err
	}

	if err := m.Up(); err != nil && err != migrate.ErrNoChange {
		return nil, nil, err
	}

	// 初始化Redis客户端
	redisClient := redis.NewClient(&redis.Options{
		Addr:         c.Redis.Addr,
		DB:           int(c.Redis.Db),
		ReadTimeout:  c.Redis.ReadTimeout.AsDuration(),
		WriteTimeout: c.Redis.WriteTimeout.AsDuration(),
	})

	// 测试Redis连接
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := redisClient.Ping(ctx).Err(); err != nil {
		return nil, nil, err
	}

	d := &Data{
		db:    db,
		redis: redisClient,
		log:   helper,
	}

	cleanup := func() {
		log.NewHelper(logger).Info("closing the data resources")
		sqlDB, err := d.db.DB()
		if err != nil {
			log.NewHelper(logger).Error(err)
			return
		}
		err = sqlDB.Close()
		if err != nil {
			log.NewHelper(logger).Error(err)
		}
		err = d.redis.Close()
		if err != nil {
			log.NewHelper(logger).Error(err)
		}
	}
	return d, cleanup, nil
}
