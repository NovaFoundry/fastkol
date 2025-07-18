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
		Username: ta.Username,
		Email:    ta.Email,
		Phone:    ta.Phone,
		Password: ta.Password,
		Headers: TwitterAccountHeaders{
			Authorization:        ta.Headers.Authorization,
			XCsrfToken:           ta.Headers.XCsrfToken,
			Cookie:               ta.Headers.Cookie,
			XClientTransactionID: ta.Headers.XClientTransactionID,
		},
		Status: AccountStatus(ta.Status),
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
		Headers: biz.TwitterAccountHeaders{
			Authorization:        account.Headers.Authorization,
			XCsrfToken:           account.Headers.XCsrfToken,
			Cookie:               account.Headers.Cookie,
			XClientTransactionID: account.Headers.XClientTransactionID,
		},
		Status: string(account.Status),
	}, nil
}

// Update 更新一个Twitter账号
func (r *twitterAccountRepo) Update(ctx context.Context, ta *biz.TwitterAccount) (*biz.TwitterAccount, error) {
	account := &TwitterAccount{
		ID:       ta.ID,
		Username: ta.Username,
		Email:    ta.Email,
		Phone:    ta.Phone,
		Password: ta.Password,
		Headers: TwitterAccountHeaders{
			Authorization:        ta.Headers.Authorization,
			XCsrfToken:           ta.Headers.XCsrfToken,
			Cookie:               ta.Headers.Cookie,
			XClientTransactionID: ta.Headers.XClientTransactionID,
		},
		Status: AccountStatus(ta.Status),
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
		Headers: biz.TwitterAccountHeaders{
			Authorization:        updatedAccount.Headers.Authorization,
			XCsrfToken:           updatedAccount.Headers.XCsrfToken,
			Cookie:               updatedAccount.Headers.Cookie,
			XClientTransactionID: updatedAccount.Headers.XClientTransactionID,
		},
		Status: string(updatedAccount.Status),
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
		Headers: biz.TwitterAccountHeaders{
			Authorization:        account.Headers.Authorization,
			XCsrfToken:           account.Headers.XCsrfToken,
			Cookie:               account.Headers.Cookie,
			XClientTransactionID: account.Headers.XClientTransactionID,
		},
		Status: string(account.Status),
	}, nil
}

// List 列出所有Twitter账号
func (r *twitterAccountRepo) List(ctx context.Context, pageSize, pageNum int, status string, id int64, username, email string, sortField, sortOrder string) ([]*biz.TwitterAccount, int64, error) {
	var accounts []*TwitterAccount
	var total int64

	query := r.data.db.WithContext(ctx).Model(&TwitterAccount{})

	// 如果指定了状态，则按状态筛选
	if status != "" {
		query = query.Where("status = ?", AccountStatus(status))
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
			Headers: biz.TwitterAccountHeaders{
				Authorization:        account.Headers.Authorization,
				XCsrfToken:           account.Headers.XCsrfToken,
				Cookie:               account.Headers.Cookie,
				XClientTransactionID: account.Headers.XClientTransactionID,
			},
			Status: string(account.Status),
		})
	}

	return result, total, nil
}

// 获取未被占用的指定状态账号，并随机打乱顺序
func (r *twitterAccountRepo) getAvailableAccountsByStatus(
	ctx context.Context,
	status AccountStatus,
	occupiedMap map[string]string,
) ([]*TwitterAccount, error) {
	var accounts []*TwitterAccount
	err := r.data.db.WithContext(ctx).
		Where("status = ?", status).
		Find(&accounts).Error
	if err != nil {
		return nil, err
	}

	var available []*TwitterAccount
	now := time.Now().Unix()
	occupiedKey := "twitter_accounts_occupied"
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

	shuffleTwitterAccounts(available)
	return available, nil
}

/*
*
获取并锁定Twitter账号
accountType: suspended, normal

	suspended: 被封禁的账号
	normal: 正常账号
	空字符串: 正常账号 + 被封禁的账号

count: 获取的账号数量
lockSeconds: 锁定时间(秒)
*/
func (r *twitterAccountRepo) GetAndLockTwitterAccounts(ctx context.Context, count int, lockSeconds int, accountType string) ([]*biz.TwitterAccount, error) {
	occupiedKey := "twitter_accounts_occupied"
	occupiedMap, err := r.data.redis.HGetAll(ctx, occupiedKey).Result()
	if err != nil {
		return nil, fmt.Errorf("获取已占用账号ID失败: %v", err)
	}

	var selectedAccounts []*TwitterAccount

	if accountType == "suspended" {
		availableSuspended, err := r.getAvailableAccountsByStatus(ctx, AccountStatusSuspended, occupiedMap)
		if err != nil {
			return nil, err
		}
		if len(availableSuspended) == 0 {
			return nil, biz.ErrTwitterAccountNotFound
		}
		if len(availableSuspended) > count {
			availableSuspended = availableSuspended[:count]
		}
		selectedAccounts = append(selectedAccounts, availableSuspended...)
	} else if accountType == "normal" {
		availableNormal, err := r.getAvailableAccountsByStatus(ctx, AccountStatusNormal, occupiedMap)
		if err != nil {
			return nil, err
		}
		if len(availableNormal) == 0 {
			return nil, biz.ErrTwitterAccountNotFound
		}
		if len(availableNormal) > count {
			availableNormal = availableNormal[:count]
		}
		selectedAccounts = append(selectedAccounts, availableNormal...)
	} else {
		availableSuspended, err := r.getAvailableAccountsByStatus(ctx, AccountStatusSuspended, occupiedMap)
		if err != nil {
			return nil, err
		}
		need := count - len(availableSuspended)
		var availableNormal []*TwitterAccount
		if need > 0 {
			availableNormal, err = r.getAvailableAccountsByStatus(ctx, AccountStatusNormal, occupiedMap)
			if err != nil {
				return nil, err
			}
			if need > len(availableNormal) {
				need = len(availableNormal)
			}
			availableNormal = availableNormal[:need]
		}
		selectedAccounts = append(selectedAccounts, availableSuspended...)
		selectedAccounts = append(selectedAccounts, availableNormal...)
		if len(selectedAccounts) == 0 {
			return nil, biz.ErrTwitterAccountNotFound
		}
		if len(selectedAccounts) > count {
			selectedAccounts = selectedAccounts[:count]
		}
	}

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
	result := make([]*biz.TwitterAccount, 0, len(selectedAccounts))
	for _, account := range selectedAccounts {
		result = append(result, &biz.TwitterAccount{
			ID:        account.ID,
			CreatedAt: account.CreatedAt,
			UpdatedAt: account.UpdatedAt,
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers: biz.TwitterAccountHeaders{
				Authorization:        account.Headers.Authorization,
				XCsrfToken:           account.Headers.XCsrfToken,
				Cookie:               account.Headers.Cookie,
				XClientTransactionID: account.Headers.XClientTransactionID,
			},
			Status: string(account.Status),
		})
	}
	return result, nil
}

// shuffleTwitterAccounts 随机打乱账号顺序
func shuffleTwitterAccounts(accounts []*TwitterAccount) {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	n := len(accounts)
	for i := n - 1; i > 0; i-- {
		j := r.Intn(i + 1)
		accounts[i], accounts[j] = accounts[j], accounts[i]
	}
}

// UnlockTwitterAccounts 解锁指定的Twitter账号
func (r *twitterAccountRepo) UnlockTwitterAccounts(ctx context.Context, ids []uint, delay int) error {
	if len(ids) == 0 {
		return nil
	}

	// 使用 Redis Hash 存储已占用的账号ID和过期时间
	occupiedKey := "twitter_accounts_occupied"

	// 构建管道
	pipe := r.data.redis.Pipeline()

	now := time.Now().Unix()
	for _, id := range ids {
		accID := fmt.Sprintf("%d", id)
		r.log.Infof("delay: %d", delay)
		if delay > 0 {
			// 如果设置了延迟，更新过期时间为当前时间+延迟时间
			expireTime := now + int64(delay)
			pipe.HSet(ctx, occupiedKey, accID, expireTime)
		} else {
			// 如果没有延迟，直接删除记录
			pipe.HDel(ctx, occupiedKey, accID)
		}
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
		Headers: biz.TwitterAccountHeaders{
			Authorization:        account.Headers.Authorization,
			XCsrfToken:           account.Headers.XCsrfToken,
			Cookie:               account.Headers.Cookie,
			XClientTransactionID: account.Headers.XClientTransactionID,
		},
		Status: string(account.Status),
	}, nil
}
