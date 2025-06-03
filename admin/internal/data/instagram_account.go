package data

import (
	"time"

	"gorm.io/gorm"
)

// InstagramAccountStatus 表示 Instagram 账号的状态
type InstagramAccountStatus string

const (
	// InstagramAccountStatusNormal 账号状态正常
	InstagramAccountStatusNormal InstagramAccountStatus = "normal"
	// InstagramAccountStatusLoginExpired 登录已失效
	InstagramAccountStatusLoginExpired InstagramAccountStatus = "login_expired"
	// InstagramAccountStatusDisabled 账号被禁用
	InstagramAccountStatusDisabled InstagramAccountStatus = "disabled"
	// InstagramAccountStatusDeprecated 账号已废弃
	InstagramAccountStatusDeprecated InstagramAccountStatus = "deprecated"
)

type InstagramAccountHeaders struct {
	Cookie     string `json:"cookie" gorm:"column:cookie;comment:Instagram会话cookie"`
	XCsrftoken string `json:"x-csrftoken" gorm:"column:x-csrftoken;comment:Instagram CSRF token"`
}

// InstagramAccount 是Instagram账号数据模型
type InstagramAccount struct {
	ID        uint           `gorm:"primarykey;comment:主键ID"`
	CreatedAt time.Time      `gorm:"not null;default:CURRENT_TIMESTAMP;comment:创建时间"`
	UpdatedAt time.Time      `gorm:"not null;default:CURRENT_TIMESTAMP;comment:更新时间"`
	DeletedAt gorm.DeletedAt `gorm:"index;comment:删除时间（软删除）"`

	Username string                  `gorm:"type:varchar(255);not null;uniqueIndex:idx_username,where:deleted_at IS NULL;comment:Instagram用户名"`
	Email    string                  `gorm:"type:varchar(255);not null;default:'';index;comment:邮箱地址"`
	Phone    string                  `gorm:"type:varchar(20);not null;default:'';index;comment:手机号码"`
	Password string                  `gorm:"type:varchar(255);not null;comment:密码"`
	Headers  InstagramAccountHeaders `gorm:"type:jsonb;serializer:json;comment:HTTP请求头信息，包含cookie和x-csrftoken"`
	Status   InstagramAccountStatus  `gorm:"type:varchar(20);not null;default:'normal';index;comment:账号状态：normal-正常，login_expired-登录已失效，disabled-已禁用，deprecated-已废弃"`
}

// TableName 指定表名
func (InstagramAccount) TableName() string {
	return "instagram_accounts"
}
