package data

import (
	"context"
	"fmt"
	"time"

	"Admin/internal/biz"

	"github.com/go-kratos/kratos/v2/log"
	"gorm.io/gorm"
)

type twitterAccountRepo struct {
	data *Data
	log  *log.Helper
}

// NewTwitterAccountRepo 创建一个新的Twitter账号仓库
func NewTwitterAccountRepo(data *Data, logger log.Logger) biz.TwitterAccountRepo {
	return &twitterAccountRepo{
		data: data,
		log:  log.NewHelper(logger),
	}
}

// Create 创建一个Twitter账号
func (r *twitterAccountRepo) Create(ctx context.Context, ta *biz.TwitterAccount) (*biz.TwitterAccount, error) {
	account := &TwitterAccount{
		Username:  ta.Username,
		Email:     ta.Email,
		Phone:     ta.Phone,
		Password:  ta.Password,
		AuthToken: ta.AuthToken,
		CsrfToken: ta.CsrfToken,
		Cookie:    ta.Cookie,
		Status:    AccountStatus(ta.Status),
	}

	result := r.data.db.WithContext(ctx).Create(account)
	if result.Error != nil {
		return nil, result.Error
	}

	return &biz.TwitterAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		AuthToken: account.AuthToken,
		CsrfToken: account.CsrfToken,
		Cookie:    account.Cookie,
		Status:    string(account.Status),
	}, nil
}

// Update 更新一个Twitter账号
func (r *twitterAccountRepo) Update(ctx context.Context, ta *biz.TwitterAccount) (*biz.TwitterAccount, error) {
	account := &TwitterAccount{
		ID:        ta.ID,
		Username:  ta.Username,
		Email:     ta.Email,
		Phone:     ta.Phone,
		Password:  ta.Password,
		AuthToken: ta.AuthToken,
		CsrfToken: ta.CsrfToken,
		Cookie:    ta.Cookie,
		Status:    AccountStatus(ta.Status),
	}

	result := r.data.db.WithContext(ctx).Model(&TwitterAccount{}).Where("id = ?", ta.ID).Updates(account)
	if result.Error != nil {
		return nil, result.Error
	}

	if result.RowsAffected == 0 {
		return nil, biz.ErrTwitterAccountNotFound
	}

	// 获取更新后的账号
	updatedAccount := &TwitterAccount{}
	if err := r.data.db.WithContext(ctx).First(updatedAccount, ta.ID).Error; err != nil {
		return nil, err
	}

	return &biz.TwitterAccount{
		ID:        updatedAccount.ID,
		CreatedAt: updatedAccount.CreatedAt,
		UpdatedAt: updatedAccount.UpdatedAt,
		Username:  updatedAccount.Username,
		Email:     updatedAccount.Email,
		Phone:     updatedAccount.Phone,
		Password:  updatedAccount.Password,
		AuthToken: updatedAccount.AuthToken,
		CsrfToken: updatedAccount.CsrfToken,
		Cookie:    updatedAccount.Cookie,
		Status:    string(updatedAccount.Status),
	}, nil
}

// Delete 删除一个Twitter账号
func (r *twitterAccountRepo) Delete(ctx context.Context, id uint) error {
	result := r.data.db.WithContext(ctx).Delete(&TwitterAccount{}, id)
	if result.Error != nil {
		return result.Error
	}

	if result.RowsAffected == 0 {
		return biz.ErrTwitterAccountNotFound
	}

	return nil
}

// GetByID 根据ID获取一个Twitter账号
func (r *twitterAccountRepo) GetByID(ctx context.Context, id uint) (*biz.TwitterAccount, error) {
	account := &TwitterAccount{}
	if err := r.data.db.WithContext(ctx).First(account, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, biz.ErrTwitterAccountNotFound
		}
		return nil, err
	}

	return &biz.TwitterAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		AuthToken: account.AuthToken,
		CsrfToken: account.CsrfToken,
		Cookie:    account.Cookie,
		Status:    string(account.Status),
	}, nil
}

// List 列出所有Twitter账号
func (r *twitterAccountRepo) List(ctx context.Context, pageSize, pageNum int, status string) ([]*biz.TwitterAccount, int64, error) {
	var accounts []*TwitterAccount
	var total int64

	query := r.data.db.WithContext(ctx).Model(&TwitterAccount{})

	// 如果指定了状态，则按状态筛选
	if status != "" {
		query = query.Where("status = ?", AccountStatus(status))
	}

	// 获取总数
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	// 分页查询
	offset := (pageNum - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Find(&accounts).Error; err != nil {
		return nil, 0, err
	}

	// 转换为业务层模型
	result := make([]*biz.TwitterAccount, 0, len(accounts))
	for _, account := range accounts {
		result = append(result, &biz.TwitterAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			AuthToken: account.AuthToken,
			CsrfToken: account.CsrfToken,
			Cookie:    account.Cookie,
			Status:    string(account.Status),
		})
	}

	return result, total, nil
}

// GetAndLockTwitterAccounts 获取并锁定多个可用的Twitter账号
func (r *twitterAccountRepo) GetAndLockTwitterAccounts(ctx context.Context, count int, lockSeconds int) ([]*biz.TwitterAccount, error) {
	// 查找多个状态为normal的账号
	var accounts []*TwitterAccount
	err := r.data.db.WithContext(ctx).
		Where("status = ?", AccountStatusNormal).
		Limit(count).
		Find(&accounts).Error
	if err != nil {
		return nil, err
	}

	if len(accounts) == 0 {
		return nil, biz.ErrTwitterAccountNotFound
	}

	// 尝试获取Redis锁
	lockedAccounts := make([]*biz.TwitterAccount, 0, len(accounts))
	for _, account := range accounts {
		lockKey := fmt.Sprintf("twitter_account_lock:%d", account.ID)
		locked, err := r.data.redis.SetNX(ctx, lockKey, "1", time.Duration(lockSeconds)*time.Second).Result()
		if err != nil {
			// 如果获取锁失败，需要解锁已经获取的账号
			for _, lockedAccount := range lockedAccounts {
				unlockKey := fmt.Sprintf("twitter_account_lock:%d", lockedAccount.ID)
				r.data.redis.Del(ctx, unlockKey)
			}
			return nil, err
		}
		if !locked {
			continue
		}

		// 转换为业务层模型
		lockedAccounts = append(lockedAccounts, &biz.TwitterAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			AuthToken: account.AuthToken,
			CsrfToken: account.CsrfToken,
			Cookie:    account.Cookie,
			Status:    string(account.Status),
		})
	}

	if len(lockedAccounts) == 0 {
		return nil, biz.ErrTwitterAccountNotFound
	}

	return lockedAccounts, nil
}

// UnlockTwitterAccounts 解锁指定的Twitter账号
func (r *twitterAccountRepo) UnlockTwitterAccounts(ctx context.Context, ids []uint) error {
	if len(ids) == 0 {
		return nil
	}

	// 构建管道
	pipe := r.data.redis.Pipeline()
	for _, id := range ids {
		lockKey := fmt.Sprintf("twitter_account_lock:%d", id)
		pipe.Del(ctx, lockKey)
	}

	// 执行管道命令
	_, err := pipe.Exec(ctx)
	return err
}

// GetByUsername 根据用户名获取一个Twitter账号
func (r *twitterAccountRepo) GetByUsername(ctx context.Context, username string) (*biz.TwitterAccount, error) {
	account := &TwitterAccount{}
	if err := r.data.db.WithContext(ctx).Where("username = ?", username).First(account).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, biz.ErrTwitterAccountNotFound
		}
		return nil, err
	}

	return &biz.TwitterAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		AuthToken: account.AuthToken,
		CsrfToken: account.CsrfToken,
		Cookie:    account.Cookie,
		Status:    string(account.Status),
	}, nil
}
