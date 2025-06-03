CREATE TABLE instagram_accounts (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL DEFAULT '',
    phone VARCHAR(20) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL,
    headers JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'normal'
);

CREATE UNIQUE INDEX instagram_accounts_username_idx ON instagram_accounts (username) WHERE deleted_at IS NULL;
CREATE INDEX instagram_accounts_email_idx ON instagram_accounts (email);
CREATE INDEX instagram_accounts_phone_idx ON instagram_accounts (phone);
CREATE INDEX instagram_accounts_status_idx ON instagram_accounts (status);
CREATE INDEX instagram_accounts_deleted_at_idx ON instagram_accounts (deleted_at);

COMMENT ON TABLE instagram_accounts IS 'Instagram账号表';
COMMENT ON COLUMN instagram_accounts.id IS '主键ID';
COMMENT ON COLUMN instagram_accounts.created_at IS '创建时间';
COMMENT ON COLUMN instagram_accounts.updated_at IS '更新时间';
COMMENT ON COLUMN instagram_accounts.deleted_at IS '删除时间（软删除）';
COMMENT ON COLUMN instagram_accounts.username IS 'Instagram用户名';
COMMENT ON COLUMN instagram_accounts.email IS '邮箱地址';
COMMENT ON COLUMN instagram_accounts.phone IS '手机号码';
COMMENT ON COLUMN instagram_accounts.password IS '密码';
COMMENT ON COLUMN instagram_accounts.headers IS 'HTTP请求头信息，包含cookie和x-csrftoken';
COMMENT ON COLUMN instagram_accounts.status IS '账号状态：normal-正常，login_expired-登录已失效，disabled-已禁用，deprecated-已废弃'; 