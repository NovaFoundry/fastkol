"use client";

import { usePathname, useRouter } from 'next/navigation';
import { Menu, Dropdown, Button } from 'antd';
import { DownOutlined } from '@ant-design/icons';

const menuItems = [
  {
    key: '/twitterAccount',
    label: 'Twitter账号管理',
  },
  {
    key: '/instagramAccount',
    label: 'Instagram账号管理',
  },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleMenuClick = (e: any) => {
    router.push(e.key);
  };

  const current = menuItems.find(item => pathname.startsWith(item.key));

  return (
    <div style={{
      width: '100%',
      background: '#1677ff',
      borderBottom: '1px solid #eee',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      height: 56,
      zIndex: 100,
      position: 'sticky',
      top: 0,
      boxShadow: '0 2px 8px #f0f1f2',
    }}>
      <Dropdown
        menu={{
          onClick: handleMenuClick,
          selectedKeys: [current?.key || ''],
          items: menuItems,
        }}
        trigger={['click']}
      >
        <Button type="text" style={{ fontWeight: 600, fontSize: 16, color: '#fff' }}>
          账号管理 <DownOutlined style={{ color: '#fff' }} />
        </Button>
      </Dropdown>
      <span style={{ marginLeft: 16, color: '#e6f4ff', fontWeight: 500 }}>
        {current ? `当前位置：${current.label}` : ''}
      </span>
    </div>
  );
} 