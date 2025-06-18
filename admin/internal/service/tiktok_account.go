package service

import (
	"context"
	"time"

	v1 "Admin/api/tiktok/v1"
	"Admin/internal/biz"

	"github.com/go-kratos/kratos/v2/log"
)

// TikTokAccountService 是TikTok账号服务
type TikTokAccountService struct {
	v1.UnimplementedTikTokAccountServer

	uc  *biz.TikTokAccountUsecase
	log *log.Helper
}

// NewTikTokAccountService 创建一个新的TikTok账号服务
func NewTikTokAccountService(uc *biz.TikTokAccountUsecase, logger log.Logger) *TikTokAccountService {
	return &TikTokAccountService{
		uc:  uc,
		log: log.NewHelper(logger),
	}
}

// CreateTikTokAccount 创建一个TikTok账号
func (s *TikTokAccountService) CreateTikTokAccount(ctx context.Context, req *v1.CreateTikTokAccountRequest) (*v1.CreateTikTokAccountReply, error) {
	account := &biz.TikTokAccount{
		Username: req.Username,
		Email:    req.Email,
		Phone:    req.Phone,
		Password: req.Password,
		Headers:  req.Headers,
		Params:   req.Params,
		Status:   req.Status,
	}

	result, err := s.uc.Create(ctx, account)
	if err != nil {
		return nil, err
	}

	return &v1.CreateTikTokAccountReply{
		Account: &v1.TikTokAccountInfo{
			Id:        int64(result.ID),
			Username:  result.Username,
			Email:     result.Email,
			Phone:     result.Phone,
			Password:  result.Password,
			Headers:   result.Headers,
			Params:    result.Params,
			Status:    result.Status,
			CreatedAt: result.CreatedAt.Format(time.RFC3339),
			UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
		},
	}, nil
}

// UpdateTikTokAccount 更新一个TikTok账号
func (s *TikTokAccountService) UpdateTikTokAccount(ctx context.Context, req *v1.UpdateTikTokAccountRequest) (*v1.UpdateTikTokAccountReply, error) {
	account := &biz.TikTokAccount{
		ID:       uint(req.Id),
		Username: req.Username,
		Email:    req.Email,
		Phone:    req.Phone,
		Password: req.Password,
		Headers:  req.Headers,
		Params:   req.Params,
		Status:   req.Status,
	}

	result, err := s.uc.Update(ctx, account)
	if err != nil {
		return nil, err
	}

	return &v1.UpdateTikTokAccountReply{
		Id:        int64(result.ID),
		Username:  result.Username,
		Email:     result.Email,
		Phone:     result.Phone,
		Headers:   result.Headers,
		Params:    result.Params,
		Status:    result.Status,
		UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
	}, nil
}

// DeleteTikTokAccount 删除一个TikTok账号
func (s *TikTokAccountService) DeleteTikTokAccount(ctx context.Context, req *v1.DeleteTikTokAccountRequest) (*v1.DeleteTikTokAccountReply, error) {
	err := s.uc.Delete(ctx, uint(req.Id))
	if err != nil {
		return nil, err
	}

	return &v1.DeleteTikTokAccountReply{
		Success: true,
	}, nil
}

// GetTikTokAccount 获取一个TikTok账号
func (s *TikTokAccountService) GetTikTokAccount(ctx context.Context, req *v1.GetTikTokAccountRequest) (*v1.GetTikTokAccountReply, error) {
	account, err := s.uc.Get(ctx, uint(req.Id))
	if err != nil {
		return nil, err
	}

	return &v1.GetTikTokAccountReply{
		Account: &v1.TikTokAccountInfo{
			Id:        int64(account.ID),
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers:   account.Headers,
			Params:    account.Params,
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		},
	}, nil
}

// ListTikTokAccounts 列出所有TikTok账号
func (s *TikTokAccountService) ListTikTokAccounts(ctx context.Context, req *v1.ListTikTokAccountsRequest) (*v1.ListTikTokAccountsReply, error) {
	accounts, total, err := s.uc.List(ctx, int(req.PageSize), int(req.PageNum), req.Status, req.Id, req.Username, req.Email, req.SortField, req.SortOrder)
	if err != nil {
		return nil, err
	}

	result := &v1.ListTikTokAccountsReply{
		Total: int32(total),
	}

	for _, account := range accounts {
		result.Accounts = append(result.Accounts, &v1.TikTokAccountInfo{
			Id:        int64(account.ID),
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers:   account.Headers,
			Params:    account.Params,
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		})
	}

	return result, nil
}

// LockTikTokAccounts 获取并锁定多个TikTok账号
func (s *TikTokAccountService) LockTikTokAccounts(ctx context.Context, req *v1.LockTikTokAccountsRequest) (*v1.LockTikTokAccountsReply, error) {
	accounts, lockSeconds, err := s.uc.GetAndLockTikTokAccounts(ctx, int(req.Count), int(req.LockSeconds))
	if err != nil {
		return nil, err
	}

	reply := &v1.LockTikTokAccountsReply{
		LockSeconds: int32(lockSeconds),
	}

	for _, account := range accounts {
		reply.Accounts = append(reply.Accounts, &v1.TikTokAccountInfo{
			Id:        int64(account.ID),
			Username:  account.Username,
			Email:     account.Email,
			Phone:     account.Phone,
			Password:  account.Password,
			Headers:   account.Headers,
			Params:    account.Params,
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		})
	}

	return reply, nil
}

// UnlockTikTokAccounts 解锁指定的TikTok账号
func (s *TikTokAccountService) UnlockTikTokAccounts(ctx context.Context, req *v1.UnlockTikTokAccountsRequest) (*v1.UnlockTikTokAccountsReply, error) {
	ids := make([]uint, len(req.Ids))
	for i, id := range req.Ids {
		ids[i] = uint(id)
	}

	err := s.uc.UnlockTikTokAccounts(ctx, ids, int(req.Delay))
	if err != nil {
		return nil, err
	}

	return &v1.UnlockTikTokAccountsReply{
		Success:       true,
		UnlockedCount: int32(len(ids)),
	}, nil
}