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

type tikTokAccountRepo struct {
	data *Data
	log  *log.Helper
}

// NewTikTokAccountRepo 创建一个新的TikTok账号仓库
func NewTikTokAccountRepo(data *Data, logger log.Logger) biz.TikTokAccountRepo {
	return &tikTokAccountRepo{
		data: data,
		log:  log.NewHelper(logger),
	}
}

// Create 创建一个TikTok账号
func (r *tikTokAccountRepo) Create(ctx context.Context, ta *biz.TikTokAccount) (*biz.TikTokAccount, error) {
	account := &TikTokAccount{
		Username: ta.Username,
		Email:    ta.Email,
		Phone:    ta.Phone,
		Password: ta.Password,
		Headers:  ta.Headers,
		Params:   ta.Params,
		Status:   TikTokAccountStatus(ta.Status),
	}

	result := r.data.db.WithContext(ctx).Create(account)
	if result.Error != nil {
		return nil, result.Error
	}

	return &biz.TikTokAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		Headers:   account.Headers,
		Params:    account.Params,
		Status:    string(account.Status),
	}, nil
}

// Update 更新一个TikTok账号
func (r *tikTokAccountRepo) Update(ctx context.Context, ta *biz.TikTokAccount) (*biz.TikTokAccount, error) {
	account := &TikTokAccount{
		ID:       ta.ID,
		Username: ta.Username,
		Email:    ta.Email,
		Phone:    ta.Phone,
		Password: ta.Password,
		Headers:  ta.Headers,
		Params:   ta.Params,
		Status:   TikTokAccountStatus(ta.Status),
	}

	result := r.data.db.WithContext(ctx).Model(&TikTokAccount{}).Where("id = ?", ta.ID).Updates(account)
	if result.Error != nil {
		return nil, result.Error
	}

	if result.RowsAffected == 0 {
		return nil, biz.ErrTikTokAccountNotFound
	}

	// 获取更新后的账号
	updatedAccount := &TikTokAccount{}
	if err := r.data.db.WithContext(ctx).First(updatedAccount, ta.ID).Error; err != nil {
		return nil, err
	}

	return &biz.TikTokAccount{
		ID:        updatedAccount.ID,
		CreatedAt: updatedAccount.CreatedAt,
		UpdatedAt: updatedAccount.UpdatedAt,
		Username:  updatedAccount.Username,
		Email:     updatedAccount.Email,
		Phone:     updatedAccount.Phone,
		Password:  updatedAccount.Password,
		Headers:   updatedAccount.Headers,
		Params:    updatedAccount.Params,
		Status:    string(updatedAccount.Status),
	}, nil
}

// Delete 删除一个TikTok账号
func (r *tikTokAccountRepo) Delete(ctx context.Context, id uint) error {
	result := r.data.db.WithContext(ctx).Delete(&TikTokAccount{}, id)
	if result.Error != nil {
		return result.Error
	}

	if result.RowsAffected == 0 {
		return biz.ErrTikTokAccountNotFound
	}

	return nil
}

// GetByID 根据ID获取一个TikTok账号
func (r *tikTokAccountRepo) GetByID(ctx context.Context, id uint) (*biz.TikTokAccount, error) {
	account := &TikTokAccount{}
	if err := r.data.db.WithContext(ctx).First(account, id).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, biz.ErrTikTokAccountNotFound
		}
		return nil, err
	}

	return &biz.TikTokAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		Headers:   account.Headers,
		Params:    account.Params,
		Status:    string(account.Status),
	}, nil
}

// GetByUsername 根据用户名获取一个TikTok账号
func (r *tikTokAccountRepo) GetByUsername(ctx context.Context, username string) (*biz.TikTokAccount, error) {
	account := &TikTokAccount{}
	if err := r.data.db.WithContext(ctx).Where("username = ?", username).First(account).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, biz.ErrTikTokAccountNotFound
		}
		return nil, err
	}

	return &biz.TikTokAccount{
		ID:        account.ID,
		CreatedAt: account.CreatedAt,
		UpdatedAt: account.UpdatedAt,
		Username:  account.Username,
		Email:     account.Email,
		Phone:     account.Phone,
		Password:  account.Password,
		Headers:   account.Headers,
		Params:    account.Params,
		Status:    string(account.Status),
	}, nil
}

// List 列出所有TikTok账号
func (r *tikTokAccountRepo) List(ctx context.Context, pageSize, pageNum int, status string, id int64, username, email string, sortField, sortOrder string) ([]*biz.TikTokAccount, int64, error) {
	var accounts []*TikTokAccount
	var total int64

	query := r.data.db.WithContext(ctx).Model(&TikTokAccount{})

	// 如果指定了状态，则按状态筛选
	if status != "" {
		query = query.Where("status = ?", TikTokAccountStatus(status))
	}

	// 如果指定了ID，则按ID筛选
	if id > 0 {
		query = query.Where("id = ?", id)
	}

	// 如果指定了用户名，则按用户名搜索
	if username != "" {
		query = query.Where("username LIKE ?", username+"%")
	}

	// 如果指定了邮箱，则按邮箱搜索
	if email != "" {
		query = query.Where("email LIKE ?", email+"%")
	}

	// 获取总数
	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	// 处理排序
	if sortField == "" {
		sortField = "id" // 默认按id排序
	}
	if sortOrder == "" {
		sortOrder = "asc" // 默认升序
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

	// 分页查询
	offset := (pageNum - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Find(&accounts).Error; err != nil {
		return nil, 0, err
	}

	// 转换为业务层模型
	result := make([]*biz.TikTokAccount, 0, len(accounts))
	for _, account := range accounts {
		result = append(result, &biz.TikTokAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers:   account.Headers,
			Params:    account.Params,
			Status:    string(account.Status),
		})
	}

	return result, total, nil
}

// 随机打乱TikTok账号列表顺序
func shuffleTikTokAccounts(accounts []*TikTokAccount) {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	for i := range accounts {
		j := r.Intn(i + 1)
		accounts[i], accounts[j] = accounts[j], accounts[i]
	}
}

// 获取未被占用的指定状态账号，并随机打乱顺序
func (r *tikTokAccountRepo) getAvailableAccountsByStatus(
	ctx context.Context,
	status TikTokAccountStatus,
	occupiedMap map[string]string,
) ([]*TikTokAccount, error) {
	var accounts []*TikTokAccount
	err := r.data.db.WithContext(ctx).
		Where("status = ?", status).
		Find(&accounts).Error
	if err != nil {
		return nil, err
	}

	var available []*TikTokAccount
	now := time.Now().Unix()
	occupiedKey := "tiktok_accounts_occupied"
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
			pipe.HDel(ctx, occupiedKey, accID)
		}
	}

	// 执行清理过期记录的操作
	if _, err := pipe.Exec(ctx); err != nil {
		r.log.Warnf("清理过期记录失败: %v", err)
	}

	shuffleTikTokAccounts(available)
	return available, nil
}

// GetAndLockTikTokAccounts 获取并锁定TikTok账号
func (r *tikTokAccountRepo) GetAndLockTikTokAccounts(ctx context.Context, count int, lockSeconds int) ([]*biz.TikTokAccount, error) {
	occupiedKey := "tiktok_accounts_occupied"
	occupiedMap, err := r.data.redis.HGetAll(ctx, occupiedKey).Result()
	if err != nil {
		return nil, fmt.Errorf("获取已占用账号ID失败: %v", err)
	}

	var selectedAccounts []*TikTokAccount

	// 只获取状态为normal的账号
	availableNormal, err := r.getAvailableAccountsByStatus(ctx, TikTokAccountStatusNormal, occupiedMap)
	if err != nil {
		return nil, err
	}
	if len(availableNormal) == 0 {
		return nil, biz.ErrTikTokAccountNotFound
	}
	if len(availableNormal) > count {
		availableNormal = availableNormal[:count]
	}
	selectedAccounts = append(selectedAccounts, availableNormal...)

	// 将选中的账号ID添加到Redis Hash中，并设置过期时间
	now := time.Now().Unix()
	pipe := r.data.redis.Pipeline()
	maxExpireTime := now + int64(lockSeconds)
	for _, account := range selectedAccounts {
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
	result := make([]*biz.TikTokAccount, 0, len(selectedAccounts))
	for _, account := range selectedAccounts {
		result = append(result, &biz.TikTokAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers:   account.Headers,
			Params:    account.Params,
			Status:    string(account.Status),
		})
	}

	return result, nil
}

// UnlockTikTokAccounts 解锁指定的TikTok账号
func (r *tikTokAccountRepo) UnlockTikTokAccounts(ctx context.Context, ids []uint, delay int) error {
	occupiedKey := "tiktok_accounts_occupied"
	pipe := r.data.redis.Pipeline()

	for _, id := range ids {
		if delay > 0 {
			// 设置延迟释放时间
			expireTime := time.Now().Unix() + int64(delay)
			pipe.HSet(ctx, occupiedKey, fmt.Sprintf("%d", id), expireTime)
		} else {
			// 立即释放
			pipe.HDel(ctx, occupiedKey, fmt.Sprintf("%d", id))
		}
	}

	_, err := pipe.Exec(ctx)
	return err
}