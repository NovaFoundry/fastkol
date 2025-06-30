'use client';

import { Menu } from 'antd';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function NavBar() {
  const pathname = usePathname();
  const selectedKey = pathname.startsWith('/search')
    ? '/search'
    : '/similar';

  return (
    <nav className="mb-8 bg-white shadow-sm">
      <div className="max-w-4xl mx-auto px-4">
        <Menu
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={[
            {
              key: '/similar',
              label: <Link href="/similar">相似账号</Link>,
            },
          ]}
        />
      </div>
    </nav>
  );
} 