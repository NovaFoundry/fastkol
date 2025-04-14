package data

import (
	"time"

	"gorm.io/gorm"
)

// AccountStatus 表示 Twitter 账号的状态
type AccountStatus string

const (
	// AccountStatusNormal 账号状态正常
	AccountStatusNormal AccountStatus = "normal"
	// AccountStatusLoginExpired 登录已失效
	AccountStatusLoginExpired AccountStatus = "login_expired"
	// AccountStatusDisabled 账号被禁用
	AccountStatusDisabled AccountStatus = "disabled"
	// AccountStatusDeprecated 账号已废弃
	AccountStatusDeprecated AccountStatus = "deprecated"
)

// TwitterAccount represents a Twitter account in the database
type TwitterAccount struct {
	ID        uint           `gorm:"primarykey"`
	CreatedAt time.Time      `gorm:"not null"`
	UpdatedAt time.Time      `gorm:"not null"`
	DeletedAt gorm.DeletedAt `gorm:"index"`

	Username  string        `gorm:"type:varchar(255);not null;uniqueIndex"`
	Email     string        `gorm:"type:varchar(255);not null;uniqueIndex"`
	Phone     string        `gorm:"type:varchar(20);not null;uniqueIndex"`
	Password  string        `gorm:"type:varchar(255);not null"`
	AuthToken string        `gorm:"type:text"`
	CsrfToken string        `gorm:"type:text"`
	Cookie    string        `gorm:"type:text"`
	Status    AccountStatus `gorm:"type:varchar(20);not null;default:'normal'"`
}

// TableName specifies the table name for TwitterAccount
func (TwitterAccount) TableName() string {
	return "twitter_accounts"
}
