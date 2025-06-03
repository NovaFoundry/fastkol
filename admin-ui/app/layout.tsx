import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Navbar from '../src/components/Navbar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'FastKOL管理系统',
  description: 'FastKOL管理系统',
};

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
          <Navbar />
          {children}
        </ConfigProvider>
      </body>
    </html>
  );
} 