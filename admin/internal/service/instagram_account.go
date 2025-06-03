package service

import (
	"context"
	"time"

	v1 "Admin/api/instagram/v1"
	"Admin/internal/biz"

	"github.com/go-kratos/kratos/v2/log"
)

// InstagramAccountService 是Instagram账号服务
type InstagramAccountService struct {
	v1.UnimplementedInstagramAccountServer
	uc  *biz.InstagramAccountUsecase
	log *log.Helper
}

// NewInstagramAccountService 创建一个新的Instagram账号服务
func NewInstagramAccountService(uc *biz.InstagramAccountUsecase, logger log.Logger) *InstagramAccountService {
	return &InstagramAccountService{
		uc:  uc,
		log: log.NewHelper(logger),
	}
}

// CreateInstagramAccount 创建一个Instagram账号
func (s *InstagramAccountService) CreateInstagramAccount(ctx context.Context, req *v1.CreateInstagramAccountRequest) (*v1.CreateInstagramAccountReply, error) {
	var headers biz.InstagramAccountHeaders
	if req.Headers != nil {
		headers = biz.InstagramAccountHeaders{
			Cookie:     req.Headers.Cookie,
			XCsrftoken: req.Headers.XCsrftoken,
		}
	}

	account := &biz.InstagramAccount{
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

	return &v1.CreateInstagramAccountReply{
		Account: &v1.InstagramAccountInfo{
			Id:       int64(result.ID),
			Username: result.Username,
			Email:    result.Email,
			Phone:    result.Phone,
			Password: result.Password,
			Headers: &v1.Headers{
				Cookie:     result.Headers.Cookie,
				XCsrftoken: result.Headers.XCsrftoken,
			},
			Status:    result.Status,
			CreatedAt: result.CreatedAt.Format(time.RFC3339),
			UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
		},
	}, nil
}

// UpdateInstagramAccount 更新一个Instagram账号
func (s *InstagramAccountService) UpdateInstagramAccount(ctx context.Context, req *v1.UpdateInstagramAccountRequest) (*v1.UpdateInstagramAccountReply, error) {
	account := &biz.InstagramAccount{
		ID:       uint(req.Id),
		Username: req.Username,
		Email:    req.Email,
		Phone:    req.Phone,
		Password: req.Password,
		Status:   req.Status,
	}

	// 只有当Headers不为nil时才设置Headers字段
	if req.Headers != nil {
		s.log.WithContext(ctx).Infof("Update InstagramAccount: %v, Headers: %v", req.Username, req.Headers)
		account.Headers = biz.InstagramAccountHeaders{
			Cookie:     req.Headers.Cookie,
			XCsrftoken: req.Headers.XCsrftoken,
		}
	}

	result, err := s.uc.Update(ctx, account)
	if err != nil {
		return nil, err
	}

	return &v1.UpdateInstagramAccountReply{
		Id:       int64(result.ID),
		Username: result.Username,
		Email:    result.Email,
		Phone:    result.Phone,
		Headers: &v1.Headers{
			Cookie:     result.Headers.Cookie,
			XCsrftoken: result.Headers.XCsrftoken,
		},
		Status:    result.Status,
		UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
	}, nil
}

// DeleteInstagramAccount 删除一个Instagram账号
func (s *InstagramAccountService) DeleteInstagramAccount(ctx context.Context, req *v1.DeleteInstagramAccountRequest) (*v1.DeleteInstagramAccountReply, error) {
	err := s.uc.Delete(ctx, uint(req.Id))
	if err != nil {
		return nil, err
	}

	return &v1.DeleteInstagramAccountReply{
		Success: true,
	}, nil
}

// GetInstagramAccount 获取一个Instagram账号
func (s *InstagramAccountService) GetInstagramAccount(ctx context.Context, req *v1.GetInstagramAccountRequest) (*v1.GetInstagramAccountReply, error) {
	result, err := s.uc.Get(ctx, uint(req.Id))
	if err != nil {
		return nil, err
	}

	return &v1.GetInstagramAccountReply{
		Account: &v1.InstagramAccountInfo{
			Id:       int64(result.ID),
			Username: result.Username,
			Email:    result.Email,
			Phone:    result.Phone,
			Password: result.Password,
			Headers: &v1.Headers{
				Cookie:     result.Headers.Cookie,
				XCsrftoken: result.Headers.XCsrftoken,
			},
			Status:    result.Status,
			CreatedAt: result.CreatedAt.Format(time.RFC3339),
			UpdatedAt: result.UpdatedAt.Format(time.RFC3339),
		},
	}, nil
}

// ListInstagramAccounts 列出所有Instagram账号
func (s *InstagramAccountService) ListInstagramAccounts(ctx context.Context, req *v1.ListInstagramAccountsRequest) (*v1.ListInstagramAccountsReply, error) {
	accounts, total, err := s.uc.List(ctx, int(req.PageSize), int(req.PageNum), req.Status, req.Id, req.Username, req.Email, req.SortField, req.SortOrder)
	if err != nil {
		return nil, err
	}

	items := make([]*v1.InstagramAccountInfo, 0, len(accounts))
	for _, account := range accounts {
		items = append(items, &v1.InstagramAccountInfo{
			Id:       int64(account.ID),
			Username: account.Username,
			Email:    account.Email,
			Phone:    account.Phone,
			Password: account.Password,
			Headers: &v1.Headers{
				Cookie:     account.Headers.Cookie,
				XCsrftoken: account.Headers.XCsrftoken,
			},
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		})
	}

	return &v1.ListInstagramAccountsReply{
		Accounts: items,
		Total:    int32(total),
	}, nil
}

// LockInstagramAccounts 获取并锁定Instagram账号
func (s *InstagramAccountService) LockInstagramAccounts(ctx context.Context, req *v1.LockInstagramAccountsRequest) (*v1.LockInstagramAccountsReply, error) {
	accounts, lockSeconds, err := s.uc.GetAndLockInstagramAccounts(ctx, int(req.Count), int(req.LockSeconds))
	if err != nil {
		return nil, err
	}

	items := make([]*v1.InstagramAccountInfo, 0, len(accounts))
	for _, account := range accounts {
		items = append(items, &v1.InstagramAccountInfo{
			Id:       int64(account.ID),
			Username: account.Username,
			Email:    account.Email,
			Phone:    account.Phone,
			Password: account.Password,
			Headers: &v1.Headers{
				Cookie:     account.Headers.Cookie,
				XCsrftoken: account.Headers.XCsrftoken,
			},
			Status:    account.Status,
			CreatedAt: account.CreatedAt.Format(time.RFC3339),
			UpdatedAt: account.UpdatedAt.Format(time.RFC3339),
		})
	}

	return &v1.LockInstagramAccountsReply{
		Accounts:    items,
		LockSeconds: int32(lockSeconds),
	}, nil
}

// UnlockInstagramAccounts 解锁Instagram账号
func (s *InstagramAccountService) UnlockInstagramAccounts(ctx context.Context, req *v1.UnlockInstagramAccountsRequest) (*v1.UnlockInstagramAccountsReply, error) {
	ids := make([]uint, 0, len(req.Ids))
	for _, id := range req.Ids {
		ids = append(ids, uint(id))
	}

	err := s.uc.UnlockInstagramAccounts(ctx, ids, int(req.Delay))
	if err != nil {
		return nil, err
	}

	return &v1.UnlockInstagramAccountsReply{
		Success:       true,
		UnlockedCount: int32(len(ids)),
	}, nil
}
