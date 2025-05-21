CREATE TABLE IF NOT EXISTS twitter_accounts (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL DEFAULT ''::character varying,
    phone VARCHAR(20) NOT NULL DEFAULT ''::character varying,
    password VARCHAR(255) NOT NULL,
    headers JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'normal'::character varying
);

-- 创建唯一索引，只对未删除的记录生效
CREATE UNIQUE INDEX IF NOT EXISTS idx_username ON public.twitter_accounts(username) WHERE deleted_at IS NULL;

-- 创建其他索引
CREATE INDEX IF NOT EXISTS idx_twitter_accounts_email ON public.twitter_accounts(email);
CREATE INDEX IF NOT EXISTS idx_twitter_accounts_phone ON public.twitter_accounts(phone);
CREATE INDEX IF NOT EXISTS idx_twitter_accounts_status ON public.twitter_accounts(status);
CREATE INDEX IF NOT EXISTS idx_twitter_accounts_deleted_at ON public.twitter_accounts(deleted_at);