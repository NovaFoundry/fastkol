package data

import (
	"time"

	"gorm.io/gorm"
)

// TikTokAccountStatus 表示 TikTok 账号的状态
type TikTokAccountStatus string

const (
	// TikTokAccountStatusNormal 账号状态正常
	TikTokAccountStatusNormal TikTokAccountStatus = "normal"
	// TikTokAccountStatusLoginExpired 登录已失效
	TikTokAccountStatusLoginExpired TikTokAccountStatus = "login_expired"
	// TikTokAccountStatusDisabled 账号被禁用
	TikTokAccountStatusDisabled TikTokAccountStatus = "disabled"
	// TikTokAccountStatusDeprecated 账号已废弃
	TikTokAccountStatusDeprecated TikTokAccountStatus = "deprecated"
)

// TikTokAccount represents a TikTok account in the database
type TikTokAccount struct {
	ID        uint           `gorm:"primarykey;comment:主键ID"`
	CreatedAt time.Time      `gorm:"not null;default:CURRENT_TIMESTAMP;comment:创建时间"`
	UpdatedAt time.Time      `gorm:"not null;default:CURRENT_TIMESTAMP;comment:更新时间"`
	DeletedAt gorm.DeletedAt `gorm:"index;comment:删除时间（软删除）"`

	Username string                 `gorm:"type:varchar(255);not null;uniqueIndex:idx_tiktok_username,where:deleted_at IS NULL;comment:TikTok用户名"`
	Email    string                 `gorm:"type:varchar(255);not null;default:'';index;comment:邮箱地址"`
	Phone    string                 `gorm:"type:varchar(20);not null;default:'';index;comment:手机号码"`
	Password string                 `gorm:"type:varchar(255);not null;comment:密码"`
	Headers  map[string]string      `gorm:"type:jsonb;serializer:json;comment:HTTP请求头信息"`
	Params   map[string]string      `gorm:"type:jsonb;serializer:json;comment:HTTP请求参数"`
	Status   TikTokAccountStatus    `gorm:"type:varchar(20);not null;default:'normal';index;comment:账号状态：normal-正常，login_expired-登录已失效，disabled-已禁用，deprecated-已废弃"`
}

// TableName specifies the table name for TikTokAccount
func (TikTokAccount) TableName() string {
	return "tiktok_accounts"
}