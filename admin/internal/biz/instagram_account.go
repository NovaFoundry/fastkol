package biz

import (
	"context"
	"fmt"
	"time"

	v1 "Admin/api/instagram/v1"

	"github.com/go-kratos/kratos/v2/errors"
	"github.com/go-kratos/kratos/v2/log"
)

var (
	// ErrInstagramAccountNotFound 是Instagram账号未找到的错误
	ErrInstagramAccountNotFound = errors.NotFound(v1.ErrorReason_INSTAGRAM_ACCOUNT_NOT_FOUND.String(), "instagram account not found")
	// ErrInstagramAccountAlreadyExists 是Instagram账号已存在的错误
	ErrInstagramAccountAlreadyExists = errors.Conflict(v1.ErrorReason_INSTAGRAM_ACCOUNT_ALREADY_EXISTS.String(), "instagram account already exists")
)

// InstagramAccountHeaders 是Instagram账号的HTTP请求头信息
type InstagramAccountHeaders struct {
	Cookie     string `json:"cookie"`
	XCsrftoken string `json:"x-csrftoken"`
}

// InstagramAccount 是Instagram账号模型
type InstagramAccount struct {
	ID        uint
	CreatedAt time.Time
	UpdatedAt time.Time

	Username string
	Email    string
	Phone    string
	Password string
	Headers  InstagramAccountHeaders
	Status   string
}

// InstagramAccountRepo 是Instagram账号仓库接口
type InstagramAccountRepo interface {
	Create(context.Context, *InstagramAccount) (*InstagramAccount, error)
	Update(context.Context, *InstagramAccount) (*InstagramAccount, error)
	Delete(context.Context, uint) error
	GetByID(context.Context, uint) (*InstagramAccount, error)
	GetByUsername(context.Context, string) (*InstagramAccount, error)
	List(context.Context, int, int, string, int64, string, string, string, string) ([]*InstagramAccount, int64, error)
	GetAndLockInstagramAccounts(context.Context, int, int) ([]*InstagramAccount, error)
	UnlockInstagramAccounts(context.Context, []uint, int) error
}

// InstagramAccountUsecase 是Instagram账号用例
type InstagramAccountUsecase struct {
	repo InstagramAccountRepo
	log  *log.Helper
}

// NewInstagramAccountUsecase 创建一个新的Instagram账号用例
func NewInstagramAccountUsecase(repo InstagramAccountRepo, logger log.Logger) *InstagramAccountUsecase {
	return &InstagramAccountUsecase{repo: repo, log: log.NewHelper(logger)}
}

// Create 创建一个Instagram账号
func (uc *InstagramAccountUsecase) Create(ctx context.Context, ta *InstagramAccount) (*InstagramAccount, error) {
	uc.log.WithContext(ctx).Infof("Create InstagramAccount: %v", ta.Username)

	// 验证邮件、用户名都要有
	if ta.Email == "" || ta.Username == "" {
		return nil, errors.BadRequest(v1.ErrorReason_INVALID_PARAMETER.String(), "email and username are required")
	}
	if ta.Password == "" {
		return nil, errors.BadRequest(v1.ErrorReason_INVALID_PARAMETER.String(), "password is required")
	}

	// 检查用户名是否已存在
	existingAccount, err := uc.repo.GetByUsername(ctx, ta.Username)
	if err != nil && !errors.Is(err, ErrInstagramAccountNotFound) {
		return nil, err
	}
	if existingAccount != nil {
		return nil, ErrInstagramAccountAlreadyExists
	}

	// 状态默认normal
	if ta.Status == "" {
		ta.Status = "normal"
	}

	return uc.repo.Create(ctx, ta)
}

// Update 更新一个Instagram账号
func (uc *InstagramAccountUsecase) Update(ctx context.Context, ta *InstagramAccount) (*InstagramAccount, error) {
	uc.log.WithContext(ctx).Infof("Update InstagramAccount: %v", ta.ID)

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
	if ta.Headers.Cookie != "" {
		existingAccount.Headers.Cookie = ta.Headers.Cookie
	}
	if ta.Headers.XCsrftoken != "" {
		existingAccount.Headers.XCsrftoken = ta.Headers.XCsrftoken
	}
	if ta.Status != "" {
		existingAccount.Status = ta.Status
	}

	return uc.repo.Update(ctx, existingAccount)
}

// Delete 删除一个Instagram账号
func (uc *InstagramAccountUsecase) Delete(ctx context.Context, id uint) error {
	uc.log.WithContext(ctx).Infof("Delete InstagramAccount: %v", id)
	return uc.repo.Delete(ctx, id)
}

// Get 获取一个Instagram账号
func (uc *InstagramAccountUsecase) Get(ctx context.Context, id uint) (*InstagramAccount, error) {
	uc.log.WithContext(ctx).Infof("Get InstagramAccount: %v", id)
	return uc.repo.GetByID(ctx, id)
}

// List 列出所有Instagram账号
func (uc *InstagramAccountUsecase) List(ctx context.Context, pageSize, pageNum int, status string, id int64, username, email string, sortField, sortOrder string) ([]*InstagramAccount, int64, error) {
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
	uc.log.WithContext(ctx).Infof("List InstagramAccounts: pageSize=%v, pageNum=%v, status=%v, id=%v, username=%v, email=%v, sortField=%v, sortOrder=%v",
		pageSize, pageNum, status, id, username, email, sortField, sortOrder)

	return uc.repo.List(ctx, pageSize, pageNum, status, id, username, email, sortField, sortOrder)
}

// GetAndLockInstagramAccounts 获取并锁定多个可用的Instagram账号
func (uc *InstagramAccountUsecase) GetAndLockInstagramAccounts(ctx context.Context, count int, lockSeconds int) ([]*InstagramAccount, int, error) {
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

	accounts, err := uc.repo.GetAndLockInstagramAccounts(ctx, count, lockSeconds)
	if err != nil {
		return nil, 0, err
	}

	// 提取账号ID用于日志记录
	accountIDs := make([]uint, 0, len(accounts))
	for _, acc := range accounts {
		accountIDs = append(accountIDs, acc.ID)
	}
	idsString := fmt.Sprintf("%v", accountIDs) // 将ID切片格式化为字符串

	uc.log.WithContext(ctx).Infof("GetAndLockInstagramAccounts: count=%v, lockSeconds=%v, ids=%s", count, lockSeconds, idsString)

	return accounts, lockSeconds, nil
}

// UnlockInstagramAccounts 解锁指定的Instagram账号
func (uc *InstagramAccountUsecase) UnlockInstagramAccounts(ctx context.Context, ids []uint, delay int) error {
	// 处理可选的delay参数
	if delay < 0 {
		delay = 0
	}

	uc.log.WithContext(ctx).Infof("UnlockInstagramAccounts: ids=%v, delay=%v", ids, delay)
	return uc.repo.UnlockInstagramAccounts(ctx, ids, delay)
}
