package data

import (
	"Admin/internal/conf"

	"github.com/go-kratos/kratos/v2/log"
	"github.com/google/wire"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// ProviderSet is data providers.
var ProviderSet = wire.NewSet(NewData, NewGreeterRepo, NewTwitterAccountRepo)

// Data .
type Data struct {
	db  *gorm.DB
	log *log.Helper
}

// NewData .
func NewData(c *conf.Data, logger log.Logger) (*Data, func(), error) {
	helper := log.NewHelper(log.With(logger, "module", "data"))

	db, err := gorm.Open(postgres.Open(c.Database.Source), &gorm.Config{})
	if err != nil {
		return nil, nil, err
	}

	// Auto migrate the schema
	err = db.AutoMigrate(&TwitterAccount{})
	if err != nil {
		return nil, nil, err
	}

	d := &Data{
		db:  db,
		log: helper,
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
	}
	return d, cleanup, nil
}
