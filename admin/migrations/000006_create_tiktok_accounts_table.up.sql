CREATE TABLE IF NOT EXISTS tiktok_accounts (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL DEFAULT ''::character varying,
    phone VARCHAR(20) NOT NULL DEFAULT ''::character varying,
    password VARCHAR(255) NOT NULL,
    headers JSONB,
    params JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'normal'::character varying
);

-- 添加字段注释
COMMENT ON COLUMN tiktok_accounts.id IS '主键ID';
COMMENT ON COLUMN tiktok_accounts.created_at IS '创建时间';
COMMENT ON COLUMN tiktok_accounts.updated_at IS '更新时间';
COMMENT ON COLUMN tiktok_accounts.deleted_at IS '删除时间（软删除）';
COMMENT ON COLUMN tiktok_accounts.username IS 'TikTok用户名';
COMMENT ON COLUMN tiktok_accounts.email IS '邮箱地址';
COMMENT ON COLUMN tiktok_accounts.phone IS '手机号码';
COMMENT ON COLUMN tiktok_accounts.password IS '密码';
COMMENT ON COLUMN tiktok_accounts.headers IS 'HTTP请求头信息，JSON格式';
COMMENT ON COLUMN tiktok_accounts.params IS 'HTTP请求参数，JSON格式';
COMMENT ON COLUMN tiktok_accounts.status IS '账号状态：normal-正常，login_expired-登录已失效，disabled-已禁用，deprecated-已废弃';

-- 创建唯一索引，只对未删除的记录生效
CREATE UNIQUE INDEX IF NOT EXISTS idx_tiktok_username ON public.tiktok_accounts(username) WHERE deleted_at IS NULL;

-- 创建其他索引
CREATE INDEX IF NOT EXISTS idx_tiktok_accounts_email ON public.tiktok_accounts(email);
CREATE INDEX IF NOT EXISTS idx_tiktok_accounts_phone ON public.tiktok_accounts(phone);
CREATE INDEX IF NOT EXISTS idx_tiktok_accounts_status ON public.tiktok_accounts(status);
CREATE INDEX IF NOT EXISTS idx_tiktok_accounts_deleted_at ON public.tiktok_accounts(deleted_at);