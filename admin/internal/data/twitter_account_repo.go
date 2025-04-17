package data

import (
	"context"
	"fmt"
	"strconv"
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
	// 使用 Redis Hash 存储已占用的账号ID和过期时间
	occupiedKey := "twitter_accounts_occupied"

	// 获取已占用的账号ID列表
	occupiedMap, err := r.data.redis.HGetAll(ctx, occupiedKey).Result()
	if err != nil {
		return nil, fmt.Errorf("获取已占用账号ID失败: %v", err)
	}

	// 查找所有状态为normal的账号
	var accounts []*TwitterAccount
	err = r.data.db.WithContext(ctx).
		Where("status = ?", AccountStatusNormal).
		Find(&accounts).Error
	if err != nil {
		return nil, err
	}

	// 筛选出未被占用的账号
	availableAccounts := make([]*TwitterAccount, 0, count)
	for _, account := range accounts {
		if len(availableAccounts) >= count {
			break
		}
		if _, exists := occupiedMap[fmt.Sprintf("%d", account.ID)]; !exists {
			availableAccounts = append(availableAccounts, account)
		}
	}

	if len(availableAccounts) == 0 {
		return nil, biz.ErrTwitterAccountNotFound
	}

	// 将选中的账号ID添加到Redis Hash中，并设置过期时间
	pipe := r.data.redis.Pipeline()
	now := time.Now().Unix()

	// 找出最晚的过期时间
	maxExpireTime := now + int64(lockSeconds)

	// 检查已存在的过期时间
	for _, expireTimeStr := range occupiedMap {
		if expireTime, err := strconv.ParseInt(expireTimeStr, 10, 64); err == nil && expireTime > maxExpireTime {
			maxExpireTime = expireTime
		}
	}

	// 添加新的账号和过期时间
	for _, account := range availableAccounts {
		expireTime := now + int64(lockSeconds)
		pipe.HSet(ctx, occupiedKey, fmt.Sprintf("%d", account.ID), expireTime)
		if expireTime > maxExpireTime {
			maxExpireTime = expireTime
		}
	}

	// 设置整个Hash的过期时间为最晚过期时间，并添加1分钟的冗余时间
	redundantSeconds := int64(60) // 1分钟冗余
	pipe.Expire(ctx, occupiedKey, time.Duration(maxExpireTime-now+redundantSeconds)*time.Second)

	if _, err := pipe.Exec(ctx); err != nil {
		return nil, fmt.Errorf("锁定账号失败: %v", err)
	}

	// 转换为业务层模型
	result := make([]*biz.TwitterAccount, 0, len(availableAccounts))
	for _, account := range availableAccounts {
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

	return result, nil
}

// UnlockTwitterAccounts 解锁指定的Twitter账号
func (r *twitterAccountRepo) UnlockTwitterAccounts(ctx context.Context, ids []uint) error {
	if len(ids) == 0 {
		return nil
	}

	// 使用 Redis Hash 存储已占用的账号ID和过期时间
	occupiedKey := "twitter_accounts_occupied"

	// 构建管道
	pipe := r.data.redis.Pipeline()

	// 从Hash中删除指定的账号ID
	for _, id := range ids {
		pipe.HDel(ctx, occupiedKey, fmt.Sprintf("%d", id))
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
