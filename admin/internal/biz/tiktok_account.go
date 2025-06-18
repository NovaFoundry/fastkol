package biz

import (
	"context"
	"fmt"
	"time"

	v1 "Admin/api/tiktok/v1"

	"github.com/go-kratos/kratos/v2/errors"
	"github.com/go-kratos/kratos/v2/log"
)

var (
	// ErrTikTokAccountNotFound 是TikTok账号未找到的错误
	ErrTikTokAccountNotFound = errors.NotFound(v1.ErrorReason_TIKTOK_ACCOUNT_NOT_FOUND.String(), "tiktok account not found")
	// ErrTikTokAccountAlreadyExists 是TikTok账号已存在的错误
	ErrTikTokAccountAlreadyExists = errors.Conflict(v1.ErrorReason_TIKTOK_ACCOUNT_ALREADY_EXISTS.String(), "tiktok account already exists")
	// ErrTikTokInvalidParameter 是参数无效的错误
	ErrTikTokInvalidParameter = errors.BadRequest(v1.ErrorReason_INVALID_PARAMETER.String(), "invalid parameter")
)

// TikTokAccount 是TikTok账号模型
type TikTokAccount struct {
	ID        uint
	CreatedAt time.Time
	UpdatedAt time.Time

	Username string
	Email    string
	Phone    string
	Password string
	Headers  map[string]string
	Params   map[string]string
	Status   string
}

// TikTokAccountRepo 是TikTok账号仓库接口
type TikTokAccountRepo interface {
	Create(context.Context, *TikTokAccount) (*TikTokAccount, error)
	Update(context.Context, *TikTokAccount) (*TikTokAccount, error)
	Delete(context.Context, uint) error
	GetByID(context.Context, uint) (*TikTokAccount, error)
	GetByUsername(context.Context, string) (*TikTokAccount, error)
	List(context.Context, int, int, string, int64, string, string, string, string) ([]*TikTokAccount, int64, error)
	GetAndLockTikTokAccounts(context.Context, int, int) ([]*TikTokAccount, error)
	UnlockTikTokAccounts(context.Context, []uint, int) error
}

// TikTokAccountUsecase 是TikTok账号用例
type TikTokAccountUsecase struct {
	repo TikTokAccountRepo
	log  *log.Helper
}

// NewTikTokAccountUsecase 创建一个新的TikTok账号用例
func NewTikTokAccountUsecase(repo TikTokAccountRepo, logger log.Logger) *TikTokAccountUsecase {
	return &TikTokAccountUsecase{repo: repo, log: log.NewHelper(logger)}
}

// Create 创建一个TikTok账号
func (uc *TikTokAccountUsecase) Create(ctx context.Context, ta *TikTokAccount) (*TikTokAccount, error) {
	uc.log.WithContext(ctx).Infof("Create TikTokAccount: %v", ta.Username)

	// 验证邮件、用户名都要有
	if ta.Email == "" || ta.Username == "" {
		return nil, ErrTikTokInvalidParameter
	}
	if ta.Password == "" {
		return nil, ErrTikTokInvalidParameter
	}

	// 检查用户名是否已存在
	existingAccount, err := uc.repo.GetByUsername(ctx, ta.Username)
	if err != nil && !errors.Is(err, ErrTikTokAccountNotFound) {
		return nil, err
	}
	if existingAccount != nil {
		return nil, ErrTikTokAccountAlreadyExists
	}

	// 状态默认normal
	if ta.Status == "" {
		ta.Status = "normal"
	}

	return uc.repo.Create(ctx, ta)
}

// Update 更新一个TikTok账号
func (uc *TikTokAccountUsecase) Update(ctx context.Context, ta *TikTokAccount) (*TikTokAccount, error) {
	uc.log.WithContext(ctx).Infof("Update TikTokAccount: %v", ta.ID)

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
	if ta.Headers != nil {
		if existingAccount.Headers == nil {
			existingAccount.Headers = make(map[string]string)
		}
		for k, v := range ta.Headers {
			existingAccount.Headers[k] = v
		}
	}
	if ta.Params != nil {
		if existingAccount.Params == nil {
			existingAccount.Params = make(map[string]string)
		}
		for k, v := range ta.Params {
			existingAccount.Params[k] = v
		}
	}
	if ta.Status != "" {
		existingAccount.Status = ta.Status
	}

	return uc.repo.Update(ctx, existingAccount)
}

// Delete 删除一个TikTok账号
func (uc *TikTokAccountUsecase) Delete(ctx context.Context, id uint) error {
	uc.log.WithContext(ctx).Infof("Delete TikTokAccount: %v", id)
	return uc.repo.Delete(ctx, id)
}

// Get 获取一个TikTok账号
func (uc *TikTokAccountUsecase) Get(ctx context.Context, id uint) (*TikTokAccount, error) {
	uc.log.WithContext(ctx).Infof("Get TikTokAccount: %v", id)
	return uc.repo.GetByID(ctx, id)
}

// List 列出所有TikTok账号
func (uc *TikTokAccountUsecase) List(ctx context.Context, pageSize, pageNum int, status string, id int64, username, email string, sortField, sortOrder string) ([]*TikTokAccount, int64, error) {
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
	uc.log.WithContext(ctx).Infof("List TikTokAccounts: pageSize=%v, pageNum=%v, status=%v, id=%v, username=%v, email=%v, sortField=%v, sortOrder=%v",
		pageSize, pageNum, status, id, username, email, sortField, sortOrder)

	return uc.repo.List(ctx, pageSize, pageNum, status, id, username, email, sortField, sortOrder)
}

// GetAndLockTikTokAccounts 获取并锁定多个可用的TikTok账号
func (uc *TikTokAccountUsecase) GetAndLockTikTokAccounts(ctx context.Context, count int, lockSeconds int) ([]*TikTokAccount, int, error) {
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

	accounts, err := uc.repo.GetAndLockTikTokAccounts(ctx, count, lockSeconds)
	if err != nil {
		return nil, 0, err
	}

	// 提取账号ID用于日志记录
	accountIDs := make([]uint, 0, len(accounts))
	for _, acc := range accounts {
		accountIDs = append(accountIDs, acc.ID)
	}
	idsString := fmt.Sprintf("%v", accountIDs) // 将ID切片格式化为字符串

	uc.log.WithContext(ctx).Infof("GetAndLockTikTokAccounts: count=%v, lockSeconds=%v, ids=%s", count, lockSeconds, idsString)

	return accounts, lockSeconds, nil
}

// UnlockTikTokAccounts 解锁指定的TikTok账号
func (uc *TikTokAccountUsecase) UnlockTikTokAccounts(ctx context.Context, ids []uint, delay int) error {
	return uc.repo.UnlockTikTokAccounts(ctx, ids, delay)
}