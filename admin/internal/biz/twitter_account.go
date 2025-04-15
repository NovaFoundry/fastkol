package biz

import (
	"context"
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

// TwitterAccount 是Twitter账号模型
type TwitterAccount struct {
	ID        uint
	CreatedAt time.Time
	UpdatedAt time.Time

	Username  string
	Email     string
	Phone     string
	Password  string
	AuthToken string
	CsrfToken string
	Cookie    string
	Status    string
}

// TwitterAccountRepo 是Twitter账号仓库接口
type TwitterAccountRepo interface {
	Create(context.Context, *TwitterAccount) (*TwitterAccount, error)
	Update(context.Context, *TwitterAccount) (*TwitterAccount, error)
	Delete(context.Context, uint) error
	GetByID(context.Context, uint) (*TwitterAccount, error)
	List(context.Context, int, int, string) ([]*TwitterAccount, int64, error)
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
	return uc.repo.Create(ctx, ta)
}

// Update 更新一个Twitter账号
func (uc *TwitterAccountUsecase) Update(ctx context.Context, ta *TwitterAccount) (*TwitterAccount, error) {
	uc.log.WithContext(ctx).Infof("Update TwitterAccount: %v", ta.ID)
	return uc.repo.Update(ctx, ta)
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
	uc.log.WithContext(ctx).Infof("List TwitterAccounts: pageSize=%v, pageNum=%v, status=%v", pageSize, pageNum, status)
	return uc.repo.List(ctx, pageSize, pageNum, status)
}
