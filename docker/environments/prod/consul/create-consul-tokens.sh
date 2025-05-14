#!/bin/sh

# 请确保已设置CONSUL_HTTP_TOKEN为master token
# 用法: CONSUL_HTTP_TOKEN=your-master-token ./create-consul-tokens.sh

set -e

CONSUL_HTTP_ADDR=${CONSUL_HTTP_ADDR:-http://localhost:8500}
POLICY_DIR=${POLICY_DIR:-./policy}

# 创建policy
consul acl policy create -name "service-registration-policy" -description "Service registration and discovery" -rules @${POLICY_DIR}/service-registration-policy.hcl || true
consul acl policy create -name "kv-policy" -description "KV store access" -rules @${POLICY_DIR}/kv-policy.hcl || true
consul acl policy create -name "health-check-policy" -description "Health check access" -rules @${POLICY_DIR}/health-check-policy.hcl || true

# 创建token
consul acl token create -description "Service Registration Token" -policy-name "service-registration-policy"
consul acl token create -description "KV Store Token" -policy-name "kv-policy"
consul acl token create -description "Health Check Token" -policy-name "health-check-policy" 