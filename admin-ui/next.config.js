/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // 不使用任何代理
    return [];
  },
}

module.exports = nextConfig