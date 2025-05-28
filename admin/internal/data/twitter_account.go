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
	// AccountStatusSuspended 账号被暂停，可执行similar，无法执行search
	AccountStatusSuspended AccountStatus = "suspended"
)

type TwitterAccountHeaders struct {
	Authorization        string `json:"authorization" gorm:"column:authorization;comment:Twitter授权token"`
	XCsrfToken           string `json:"x-csrf-token" gorm:"column:x-csrf-token;comment:Twitter CSRF token"`
	Cookie               string `json:"cookie" gorm:"column:cookie;comment:Twitter会话cookie"`
	XClientTransactionID string `json:"x-client-transaction-id" gorm:"column:x-client-transaction-id;comment:Twitter客户端事务ID"`
}

// TwitterAccount represents a Twitter account in the database
type TwitterAccount struct {
	ID        uint           `gorm:"primarykey;comment:主键ID"`
	CreatedAt time.Time      `gorm:"not null;default:CURRENT_TIMESTAMP;comment:创建时间"`
	UpdatedAt time.Time      `gorm:"not null;default:CURRENT_TIMESTAMP;comment:更新时间"`
	DeletedAt gorm.DeletedAt `gorm:"index;comment:删除时间（软删除）"`

	Username string                `gorm:"type:varchar(255);not null;uniqueIndex:idx_username,where:deleted_at IS NULL;comment:Twitter用户名"`
	Email    string                `gorm:"type:varchar(255);not null;default:'';index;comment:邮箱地址"`
	Phone    string                `gorm:"type:varchar(20);not null;default:'';index;comment:手机号码"`
	Password string                `gorm:"type:varchar(255);not null;comment:密码"`
	Headers  TwitterAccountHeaders `gorm:"type:jsonb;serializer:json;comment:HTTP请求头信息，包含authorization、x-csrf-token、cookie和x-client-transaction-id"`
	Status   AccountStatus         `gorm:"type:varchar(20);not null;default:'normal';index;comment:账号状态：normal-正常，login_expired-登录已失效，disabled-已禁用，deprecated-已废弃，suspended-已暂停"`
}

// TableName specifies the table name for TwitterAccount
func (TwitterAccount) TableName() string {
	return "twitter_accounts"
}
