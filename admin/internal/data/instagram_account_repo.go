package data

import (
	"context"
	"fmt"
	"math/rand"
	"strconv"
	"time"

	"Admin/internal/biz"

	"github.com/go-kratos/kratos/v2/log"
	"gorm.io/gorm"
)

const (
	// InstagramAccountsOccupiedKey Redis中存储已占用Instagram账号的key
	InstagramAccountsOccupiedKey = "instagram_accounts_occupied"
)

// InstagramAccountRepo 是Instagram账号仓库实现
type InstagramAccountRepo struct {
	data *Data
	log  *log.Helper
}

// NewInstagramAccountRepo 创建一个新的Instagram账号仓库
func NewInstagramAccountRepo(data *Data, logger log.Logger) biz.InstagramAccountRepo {
	return &InstagramAccountRepo{
		data: data,
		log:  log.NewHelper(logger),
	}
}

// Create 创建一个Instagram账号
func (r *InstagramAccountRepo) Create(ctx context.Context, ta *biz.InstagramAccount) (*biz.InstagramAccount, error) {
	account := &InstagramAccount{
		Username: ta.Username,
		Email:    ta.Email,
		Phone:    ta.Phone,
		Password: ta.Password,
		Headers: InstagramAccountHeaders{
			Cookie:     ta.Headers.Cookie,
			XCsrftoken: ta.Headers.XCsrftoken,
		},
		Status: InstagramAccountStatus(ta.Status),
	}

	if err := r.data.db.Create(account).Error; err != nil {
		return nil, err
	}

	return &biz.InstagramAccount{
		ID:       account.ID,
		Username: account.Username,
		Email:    account.Email,
		Phone:    account.Phone,
		Password: account.Password,
		Headers: biz.InstagramAccountHeaders{
			Cookie:     account.Headers.Cookie,
			XCsrftoken: account.Headers.XCsrftoken,
		},
		Status: string(account.Status),
	}, nil
}

// Update 更新一个Instagram账号
func (r *InstagramAccountRepo) Update(ctx context.Context, ta *biz.InstagramAccount) (*biz.InstagramAccount, error) {
	account := &InstagramAccount{
		ID:       ta.ID,
		Username: ta.Username,
		Email:    ta.Email,
		Phone:    ta.Phone,
		Password: ta.Password,
		Headers: InstagramAccountHeaders{
			Cookie:     ta.Headers.Cookie,
			XCsrftoken: ta.Headers.XCsrftoken,
		},
		Status: InstagramAccountStatus(ta.Status),
	}

	result := r.data.db.WithContext(ctx).Model(&InstagramAccount{}).Where("id = ?", ta.ID).Updates(account)
	if result.Error != nil {
		return nil, result.Error
	}

	if result.RowsAffected == 0 {
		return nil, biz.ErrInstagramAccountNotFound
	}

	// 获取更新后的账号
	updatedAccount := &InstagramAccount{}
	if err := r.data.db.WithContext(ctx).First(updatedAccount, ta.ID).Error; err != nil {
		return nil, err
	}

	return &biz.InstagramAccount{
		ID:        updatedAccount.ID,
		CreatedAt: updatedAccount.CreatedAt,
		UpdatedAt: updatedAccount.UpdatedAt,
		Username:  updatedAccount.Username,
		Email:     updatedAccount.Email,
		Phone:     updatedAccount.Phone,
		Password:  updatedAccount.Password,
		Headers: biz.InstagramAccountHeaders{
			Cookie:     updatedAccount.Headers.Cookie,
			XCsrftoken: updatedAccount.Headers.XCsrftoken,
		},
		Status: string(updatedAccount.Status),
	}, nil
}

// Delete 删除一个Instagram账号
func (r *InstagramAccountRepo) Delete(ctx context.Context, id uint) error {
	result := r.data.db.WithContext(ctx).Delete(&InstagramAccount{}, id)
	if result.Error != nil {
		return result.Error
	}

	if result.RowsAffected == 0 {
		return biz.ErrInstagramAccountNotFound
	}

	return nil
}

// GetByID 通过ID获取一个Instagram账号
func (r *InstagramAccountRepo) GetByID(ctx context.Context, id uint) (*biz.InstagramAccount, error) {
	account := &InstagramAccount{}
	if err := r.data.db.WithContext(ctx).First(account, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, biz.ErrInstagramAccountNotFound
		}
		return nil, err
	}

	return &biz.InstagramAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		Headers: biz.InstagramAccountHeaders{
			Cookie:     account.Headers.Cookie,
			XCsrftoken: account.Headers.XCsrftoken,
		},
		Status: string(account.Status),
	}, nil
}

// GetByUsername 通过用户名获取一个Instagram账号
func (r *InstagramAccountRepo) GetByUsername(ctx context.Context, username string) (*biz.InstagramAccount, error) {
	account := &InstagramAccount{}
	if err := r.data.db.WithContext(ctx).Where("username = ?", username).First(account).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, biz.ErrInstagramAccountNotFound
		}
		return nil, err
	}

	return &biz.InstagramAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		Headers: biz.InstagramAccountHeaders{
			Cookie:     account.Headers.Cookie,
			XCsrftoken: account.Headers.XCsrftoken,
		},
		Status: string(account.Status),
	}, nil
}

// List 列出所有Instagram账号
func (r *InstagramAccountRepo) List(ctx context.Context, pageSize, pageNum int, status string, id int64, username, email string, sortField, sortOrder string) ([]*biz.InstagramAccount, int64, error) {
	var accounts []*InstagramAccount
	var total int64

	query := r.data.db.WithContext(ctx).Model(&InstagramAccount{})

	// 添加查询条件
	if status != "" {
		query = query.Where("status = ?", InstagramAccountStatus(status))
	}
	if id > 0 {
		query = query.Where("id = ?", id)
	}
	if username != "" {
		query = query.Where("username LIKE ?", username+"%")
	}
	if email != "" {
		query = query.Where("email LIKE ?", email+"%")
	}

	// 获取总数
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	// 设置排序
	if sortField == "" {
		sortField = "id"
	}
	if sortOrder == "" {
		sortOrder = "asc"
	}

	// 验证排序字段
	validFields := map[string]string{
		"id": "id",
	}
	if field, ok := validFields[sortField]; ok {
		// 验证排序方向
		if sortOrder != "asc" && sortOrder != "desc" {
			sortOrder = "asc"
		}
		query = query.Order(field + " " + sortOrder)
	} else {
		// 如果排序字段无效，使用默认排序
		query = query.Order("id asc")
	}

	// 分页
	offset := (pageNum - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Find(&accounts).Error; err != nil {
		return nil, 0, err
	}

	// 转换为业务模型
	result := make([]*biz.InstagramAccount, 0, len(accounts))
	for _, account := range accounts {
		result = append(result, &biz.InstagramAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers: biz.InstagramAccountHeaders{
				Cookie:     account.Headers.Cookie,
				XCsrftoken: account.Headers.XCsrftoken,
			},
			Status: string(account.Status),
		})
	}

	return result, total, nil
}

// 获取未被占用的指定状态账号，并随机打乱顺序
func (r *InstagramAccountRepo) getAvailableAccountsByStatus(
	ctx context.Context,
	status InstagramAccountStatus,
	occupiedMap map[string]string,
) ([]*InstagramAccount, error) {
	var accounts []*InstagramAccount
	err := r.data.db.WithContext(ctx).
		Where("status = ?", status).
		Find(&accounts).Error
	if err != nil {
		return nil, err
	}

	var available []*InstagramAccount
	now := time.Now().Unix()
	pipe := r.data.redis.Pipeline()

	for _, acc := range accounts {
		accID := fmt.Sprintf("%d", acc.ID)
		expireTimeStr, exists := occupiedMap[accID]
		if !exists {
			available = append(available, acc)
			continue
		}

		expireTime, err := strconv.ParseInt(expireTimeStr, 10, 64)
		if err != nil {
			r.log.Warnf("解析过期时间失败: account_id=%d, expire_time=%s, error=%v", acc.ID, expireTimeStr, err)
			continue
		}

		if now > expireTime {
			available = append(available, acc)
			// 清理过期的记录
			pipe.HDel(ctx, InstagramAccountsOccupiedKey, accID)
		}
	}

	// 执行清理过期记录的操作
	if _, err := pipe.Exec(ctx); err != nil {
		r.log.Warnf("清理过期记录失败: %v", err)
	}

	shuffleInstagramAccounts(available)
	return available, nil
}

// shuffleInstagramAccounts 随机打乱账号顺序
func shuffleInstagramAccounts(accounts []*InstagramAccount) {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	n := len(accounts)
	for i := n - 1; i > 0; i-- {
		j := r.Intn(i + 1)
		accounts[i], accounts[j] = accounts[j], accounts[i]
	}
}

// GetAndLockInstagramAccounts 获取并锁定多个可用的Instagram账号
func (r *InstagramAccountRepo) GetAndLockInstagramAccounts(ctx context.Context, count int, lockSeconds int) ([]*biz.InstagramAccount, error) {
	occupiedMap, err := r.data.redis.HGetAll(ctx, InstagramAccountsOccupiedKey).Result()
	if err != nil {
		return nil, fmt.Errorf("获取已占用账号ID失败: %v", err)
	}

	availableAccounts, err := r.getAvailableAccountsByStatus(ctx, InstagramAccountStatusNormal, occupiedMap)
	if err != nil {
		return nil, err
	}

	if len(availableAccounts) == 0 {
		return nil, biz.ErrInstagramAccountNotFound
	}

	if len(availableAccounts) > count {
		availableAccounts = availableAccounts[:count]
	}

	// 将选中的账号ID添加到Redis Hash中，并设置过期时间
	now := time.Now().Unix()
	pipe := r.data.redis.Pipeline()
	maxExpireTime := now + int64(lockSeconds)
	for _, account := range availableAccounts {
		expireTime := now + int64(lockSeconds)
		pipe.HSet(ctx, InstagramAccountsOccupiedKey, fmt.Sprintf("%d", account.ID), expireTime)
		if expireTime > maxExpireTime {
			maxExpireTime = expireTime
		}
	}

	// 设置整个Hash的过期时间为最晚过期时间，并添加1分钟的冗余时间
	redundantSeconds := int64(60) // 1分钟冗余
	pipe.Expire(ctx, InstagramAccountsOccupiedKey, time.Duration(maxExpireTime-now+redundantSeconds)*time.Second)

	if _, err := pipe.Exec(ctx); err != nil {
		return nil, fmt.Errorf("锁定账号失败: %v", err)
	}

	// 转换为业务层模型
	result := make([]*biz.InstagramAccount, 0, len(availableAccounts))
	for _, account := range availableAccounts {
		result = append(result, &biz.InstagramAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers: biz.InstagramAccountHeaders{
				Cookie:     account.Headers.Cookie,
				XCsrftoken: account.Headers.XCsrftoken,
			},
			Status: string(account.Status),
		})
	}
	return result, nil
}

// UnlockInstagramAccounts 解锁指定的Instagram账号
func (r *InstagramAccountRepo) UnlockInstagramAccounts(ctx context.Context, ids []uint, delay int) error {
	if len(ids) == 0 {
		return nil
	}

	// 构建管道
	pipe := r.data.redis.Pipeline()

	now := time.Now().Unix()
	for _, id := range ids {
		accID := fmt.Sprintf("%d", id)
		r.log.Infof("delay: %d", delay)
		if delay > 0 {
			// 如果设置了延迟，更新过期时间为当前时间+延迟时间
			expireTime := now + int64(delay)
			pipe.HSet(ctx, InstagramAccountsOccupiedKey, accID, expireTime)
		} else {
			// 如果没有延迟，直接删除记录
			pipe.HDel(ctx, InstagramAccountsOccupiedKey, accID)
		}
	}

	// 执行管道命令
	_, err := pipe.Exec(ctx)
	return err
}
