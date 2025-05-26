/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // 只在开发环境中使用代理
    if (process.env.NODE_ENV === 'development') {
      return [
        // 代理到 http://localhost:18103
        {
          source: '/api/v1/:path*',
          destination: `${process.env.API_BASE_URL}/v1/:path*`,
        },
        // 代理到 http://localhost:10081/admin
        {
          source: '/api/admin/v1/:path*',
          destination: `${process.env.API_GATEWAY_URL}/v1/:path*`,
        },
      ]
    }
    
    // 生产环境不使用代理
    return []
  },
}

module.exports = nextConfig