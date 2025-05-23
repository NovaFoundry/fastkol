import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ConfigProvider, Menu } from 'antd';
import zhCN from 'antd/locale/zh_CN';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'FastKOL管理系统',
  description: 'FastKOL管理系统',
};

function NavBar() {
  return (
    <div style={{ background: '#1677ff', color: '#fff', marginBottom: 24, boxShadow: '0 2px 8px #f0f1f2' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', alignItems: 'center', height: 56 }}>
        <span style={{ fontWeight: 700, fontSize: 20, letterSpacing: 2 }}>FastKOL管理系统</span>
        <Menu
          mode="horizontal"
          theme="dark"
          style={{ background: 'transparent', marginLeft: 32, flex: 1 }}
          defaultSelectedKeys={['twitter']}
          items={[
            { key: 'twitter', label: 'twitter账号管理' },
            // 可扩展更多菜单
          ]}
        />
      </div>
    </div>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <ConfigProvider
          locale={zhCN}
          theme={{
            token: {
              colorPrimary: '#1677ff',
            },
          }}
        >
          <NavBar />
          {children}
        </ConfigProvider>
      </body>
    </html>
  );
} 