package biz

import (
	"context"
	"fmt"
	"time"

	v1 "Admin/api/twitter/v1"

	"github.com/go-kratos/kratos/v2/errors"
	"github.com/go-kratos/kratos/v2/log"
)

var (
	// ErrTwitterAccountNotFound 是Twitter账号未找到的错误
	ErrTwitterAccountNotFound = errors.NotFound(v1.ErrorReason_TWITTER_ACCOUNT_NOT_FOUND.String(), "twitter account not found")
	// ErrTwitterAccountAlreadyExists 是Twitter账号已存在的错误
	ErrTwitterAccountAlreadyExists = errors.Conflict(v1.ErrorReason_TWITTER_ACCOUNT_ALREADY_EXISTS.String(), "twitter account already exists")
	// ErrInvalidParameter 是参数无效的错误
	ErrInvalidParameter = errors.BadRequest(v1.ErrorReason_INVALID_PARAMETER.String(), "invalid parameter")
)

// TwitterAccountHeaders 是Twitter账号的HTTP请求头信息
type TwitterAccountHeaders struct {
	Authorization string `json:"authorization"`
	XCsrfToken    string `json:"x-csrf-token"`
	Cookie        string `json:"cookie"`
}

// TwitterAccount 是Twitter账号模型
type TwitterAccount struct {
	ID        uint
	CreatedAt time.Time
	UpdatedAt time.Time

	Username string
	Email    string
	Phone    string
	Password string
	Headers  TwitterAccountHeaders
	Status   string
}

// TwitterAccountRepo 是Twitter账号仓库接口
type TwitterAccountRepo interface {
	Create(context.Context, *TwitterAccount) (*TwitterAccount, error)
	Update(context.Context, *TwitterAccount) (*TwitterAccount, error)
	Delete(context.Context, uint) error
	GetByID(context.Context, uint) (*TwitterAccount, error)
	GetByUsername(context.Context, string) (*TwitterAccount, error)
	List(context.Context, int, int, string) ([]*TwitterAccount, int64, error)
	GetAndLockTwitterAccounts(context.Context, int, int, string) ([]*TwitterAccount, error)
	UnlockTwitterAccounts(context.Context, []uint, int) error
}

// TwitterAccountUsecase 是Twitter账号用例
type TwitterAccountUsecase struct {
	repo TwitterAccountRepo
	log  *log.Helper
}

// NewTwitterAccountUsecase 创建一个新的Twitter账号用例
func NewTwitterAccountUsecase(repo TwitterAccountRepo, logger log.Logger) *TwitterAccountUsecase {
	return &TwitterAccountUsecase{repo: repo, log: log.NewHelper(logger)}
}

// Create 创建一个Twitter账号
func (uc *TwitterAccountUsecase) Create(ctx context.Context, ta *TwitterAccount) (*TwitterAccount, error) {
	uc.log.WithContext(ctx).Infof("Create TwitterAccount: %v", ta.Username)

	// 验证邮件、用户名都要有
	if ta.Email == "" || ta.Username == "" {
		return nil, ErrInvalidParameter
	}
	if ta.Password == "" {
		return nil, ErrInvalidParameter
	}

	// 检查用户名是否已存在
	existingAccount, err := uc.repo.GetByUsername(ctx, ta.Username)
	if err != nil && !errors.Is(err, ErrTwitterAccountNotFound) {
		return nil, err
	}
	if existingAccount != nil {
		return nil, ErrTwitterAccountAlreadyExists
	}

	// 状态默认normal
	if ta.Status == "" {
		ta.Status = "normal"
	}

	return uc.repo.Create(ctx, ta)
}

// Update 更新一个Twitter账号
func (uc *TwitterAccountUsecase) Update(ctx context.Context, ta *TwitterAccount) (*TwitterAccount, error) {
	uc.log.WithContext(ctx).Infof("Update TwitterAccount: %v", ta.ID)

	// 获取现有账号
	existingAccount, err := uc.repo.GetByID(ctx, ta.ID)
	if err != nil {
		return nil, err
	}

	// 只更新非空字段
	if ta.Username != "" {
		existingAccount.Username = ta.Username
	}
	if ta.Email != "" {
		existingAccount.Email = ta.Email
	}
	if ta.Phone != "" {
		existingAccount.Phone = ta.Phone
	}
	if ta.Password != "" {
		existingAccount.Password = ta.Password
	}
	if ta.Headers.Authorization != "" {
		existingAccount.Headers.Authorization = ta.Headers.Authorization
	}
	if ta.Headers.XCsrfToken != "" {
		existingAccount.Headers.XCsrfToken = ta.Headers.XCsrfToken
	}
	if ta.Headers.Cookie != "" {
		existingAccount.Headers.Cookie = ta.Headers.Cookie
	}
	if ta.Status != "" {
		existingAccount.Status = ta.Status
	}

	return uc.repo.Update(ctx, existingAccount)
}

// Delete 删除一个Twitter账号
func (uc *TwitterAccountUsecase) Delete(ctx context.Context, id uint) error {
	uc.log.WithContext(ctx).Infof("Delete TwitterAccount: %v", id)
	return uc.repo.Delete(ctx, id)
}

// Get 获取一个Twitter账号
func (uc *TwitterAccountUsecase) Get(ctx context.Context, id uint) (*TwitterAccount, error) {
	uc.log.WithContext(ctx).Infof("Get TwitterAccount: %v", id)
	return uc.repo.GetByID(ctx, id)
}

// List 列出所有Twitter账号
func (uc *TwitterAccountUsecase) List(ctx context.Context, pageSize, pageNum int, status string) ([]*TwitterAccount, int64, error) {
	// 设置默认值
	if pageSize <= 0 {
		pageSize = 20 // 默认每页20条
	}
	if pageSize > 100 {
		pageSize = 100 // 最大每页100条
	}
	if pageNum <= 0 {
		pageNum = 1 // 默认第1页
	}
	uc.log.WithContext(ctx).Infof("List TwitterAccounts: pageSize=%v, pageNum=%v, status=%v", pageSize, pageNum, status)

	return uc.repo.List(ctx, pageSize, pageNum, status)
}

// GetAndLockTwitterAccounts 获取并锁定多个可用的Twitter账号
func (uc *TwitterAccountUsecase) GetAndLockTwitterAccounts(ctx context.Context, count int, lockSeconds int, accountType string) ([]*TwitterAccount, int, error) {
	// 设置默认值
	if count <= 0 {
		count = 1 // 默认获取1个账号
	}
	if count > 100 {
		count = 20 // 最大获取20个账号
	}
	if lockSeconds <= 0 {
		lockSeconds = 60 // 默认锁定60秒
	}
	if lockSeconds > 600 {
		lockSeconds = 600 // 最大锁定600秒
	}

	if accountType == "" {
		accountType = "similar"
	}

	accounts, err := uc.repo.GetAndLockTwitterAccounts(ctx, count, lockSeconds, accountType)
	if err != nil {
		return nil, 0, err
	}

	// 提取账号ID用于日志记录
	accountIDs := make([]uint, 0, len(accounts))
	for _, acc := range accounts {
		accountIDs = append(accountIDs, acc.ID)
	}
	idsString := fmt.Sprintf("%v", accountIDs) // 将ID切片格式化为字符串

	uc.log.WithContext(ctx).Infof("GetAndLockTwitterAccounts: count=%v, lockSeconds=%v, accountType=%v, ids=%s", count, lockSeconds, accountType, idsString)

	return accounts, lockSeconds, nil
}

// UnlockTwitterAccounts 解锁指定的Twitter账号
func (uc *TwitterAccountUsecase) UnlockTwitterAccounts(ctx context.Context, ids []uint, delay int) error {
	// 处理可选的delay参数
	if delay < 0 {
		delay = 0
	}

	uc.log.WithContext(ctx).Infof("UnlockTwitterAccounts: ids=%v, delay=%v", ids, delay)
	return uc.repo.UnlockTwitterAccounts(ctx, ids, delay)
}
