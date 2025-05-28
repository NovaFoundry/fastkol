package service

import (
	"context"
	"time"

	v1 "Admin/api/twitter/v1"
	"Admin/internal/biz"

	"github.com/go-kratos/kratos/v2/log"
)

// TwitterAccountService 是Twitter账号服务
type TwitterAccountService struct {
	v1.UnimplementedTwitterAccountServer

	uc  *biz.TwitterAccountUsecase
	log *log.Helper
}

// NewTwitterAccountService 创建一个新的Twitter账号服务
func NewTwitterAccountService(uc *biz.TwitterAccountUsecase, logger log.Logger) *TwitterAccountService {
	return &TwitterAccountService{
		uc:  uc,
		log: log.NewHelper(logger),
	}
}

// CreateTwitterAccount 创建一个Twitter账号
func (s *TwitterAccountService) CreateTwitterAccount(ctx context.Context, req *v1.CreateTwitterAccountRequest) (*v1.CreateTwitterAccountReply, error) {
	var headers biz.TwitterAccountHeaders
	if req.Headers != nil {
		headers = biz.TwitterAccountHeaders{
			Authorization:        req.Headers.Authorization,
			XCsrfToken:           req.Headers.XCsrfToken,
			Cookie:               req.Headers.Cookie,
			XClientTransactionID: req.Headers.XClientTransactionId,
		}
	}

	account := &biz.TwitterAccount{
		Username: req.Username,
		Email:    req.Email,
		Phone:    req.Phone,
		Password: req.Password,
		Headers:  headers,
		Status:   req.Status,
	}

	result, err := s.uc.Create(ctx, account)
	if err != nil {
		return nil, err
	}

	return &v1.CreateTwitterAccountReply{
		Account: &v1.TwitterAccountInfo{
			Id:       int64(result.ID),
			Username: result.Username,
			Email:    result.Email,
			Phone:    result.Phone,
			Password: result.Password,
			Headers: &v1.Headers{
				Authorization:        result.Headers.Authorization,
				XCsrfToken:           result.Headers.XCsrfToken,
				Cookie:               result.Headers.Cookie,
				XClientTransactionId: result.Headers.XClientTransactionID,
			},
			Status:    result.Status,
			CreatedAt: result.CreatedAt.Format(time.RFC3339),
			UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
		},
	}, nil
}

// UpdateTwitterAccount 更新一个Twitter账号
func (s *TwitterAccountService) UpdateTwitterAccount(ctx context.Context, req *v1.UpdateTwitterAccountRequest) (*v1.UpdateTwitterAccountReply, error) {
	account := &biz.TwitterAccount{
		ID:       uint(req.Id),
		Username: req.Username,
		Email:    req.Email,
		Phone:    req.Phone,
		Password: req.Password,
		Headers: biz.TwitterAccountHeaders{
			Authorization:        req.Headers.Authorization,
			XCsrfToken:           req.Headers.XCsrfToken,
			Cookie:               req.Headers.Cookie,
			XClientTransactionID: req.Headers.XClientTransactionId,
		},
		Status: req.Status,
	}

	result, err := s.uc.Update(ctx, account)
	if err != nil {
		return nil, err
	}

	return &v1.UpdateTwitterAccountReply{
		Id:       int64(result.ID),
		Username: result.Username,
		Email:    result.Email,
		Phone:    result.Phone,
		Headers: &v1.Headers{
			Authorization:        result.Headers.Authorization,
			XCsrfToken:           result.Headers.XCsrfToken,
			Cookie:               result.Headers.Cookie,
			XClientTransactionId: result.Headers.XClientTransactionID,
		},
		Status:    result.Status,
		UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
	}, nil
}

// DeleteTwitterAccount 删除一个Twitter账号
func (s *TwitterAccountService) DeleteTwitterAccount(ctx context.Context, req *v1.DeleteTwitterAccountRequest) (*v1.DeleteTwitterAccountReply, error) {
	err := s.uc.Delete(ctx, uint(req.Id))
	if err != nil {
		return nil, err
	}

	return &v1.DeleteTwitterAccountReply{
		Success: true,
	}, nil
}

// GetTwitterAccount 获取一个Twitter账号
func (s *TwitterAccountService) GetTwitterAccount(ctx context.Context, req *v1.GetTwitterAccountRequest) (*v1.GetTwitterAccountReply, error) {
	account, err := s.uc.Get(ctx, uint(req.Id))
	if err != nil {
		return nil, err
	}

	return &v1.GetTwitterAccountReply{
		Account: &v1.TwitterAccountInfo{
			Id:       int64(account.ID),
			Username: account.Username,
			Email:    account.Email,
			Phone:    account.Phone,
			Password: account.Password,
			Headers: &v1.Headers{
				Authorization:        account.Headers.Authorization,
				XCsrfToken:           account.Headers.XCsrfToken,
				Cookie:               account.Headers.Cookie,
				XClientTransactionId: account.Headers.XClientTransactionID,
			},
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		},
	}, nil
}

// ListTwitterAccounts 列出所有Twitter账号
func (s *TwitterAccountService) ListTwitterAccounts(ctx context.Context, req *v1.ListTwitterAccountsRequest) (*v1.ListTwitterAccountsReply, error) {
	accounts, total, err := s.uc.List(ctx, int(req.PageSize), int(req.PageNum), req.Status)
	if err != nil {
		return nil, err
	}

	result := &v1.ListTwitterAccountsReply{
		Total: int32(total),
	}

	for _, account := range accounts {
		result.Accounts = append(result.Accounts, &v1.TwitterAccountInfo{
			Id:       int64(account.ID),
			Username: account.Username,
			Email:    account.Email,
			Phone:    account.Phone,
			Password: account.Password,
			Headers: &v1.Headers{
				Authorization:        account.Headers.Authorization,
				XCsrfToken:           account.Headers.XCsrfToken,
				Cookie:               account.Headers.Cookie,
				XClientTransactionId: account.Headers.XClientTransactionID,
			},
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		})
	}

	return result, nil
}

// LockTwitterAccounts 获取并锁定多个Twitter账号
func (s *TwitterAccountService) LockTwitterAccounts(ctx context.Context, req *v1.LockTwitterAccountsRequest) (*v1.LockTwitterAccountsReply, error) {
	accounts, lockSeconds, err := s.uc.GetAndLockTwitterAccounts(ctx, int(req.Count), int(req.LockSeconds), req.Type)
	if err != nil {
		return nil, err
	}

	reply := &v1.LockTwitterAccountsReply{
		LockSeconds: int32(lockSeconds),
	}

	for _, account := range accounts {
		reply.Accounts = append(reply.Accounts, &v1.TwitterAccountInfo{
			Id:       int64(account.ID),
			Username: account.Username,
			Email:    account.Email,
			Phone:    account.Phone,
			Password: account.Password,
			Headers: &v1.Headers{
				Authorization:        account.Headers.Authorization,
				XCsrfToken:           account.Headers.XCsrfToken,
				Cookie:               account.Headers.Cookie,
				XClientTransactionId: account.Headers.XClientTransactionID,
			},
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		})
	}

	return reply, nil
}

// UnlockTwitterAccounts 解锁指定的Twitter账号
func (s *TwitterAccountService) UnlockTwitterAccounts(ctx context.Context, req *v1.UnlockTwitterAccountsRequest) (*v1.UnlockTwitterAccountsReply, error) {
	ids := make([]uint, len(req.Ids))
	for i, id := range req.Ids {
		ids[i] = uint(id)
	}

	err := s.uc.UnlockTwitterAccounts(ctx, ids, int(req.Delay))
	if err != nil {
		return nil, err
	}

	return &v1.UnlockTwitterAccountsReply{
		Success:       true,
		UnlockedCount: int32(len(ids)),
	}, nil
}
