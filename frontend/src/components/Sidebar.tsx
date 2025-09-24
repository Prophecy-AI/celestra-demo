'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';

const navigation = [
  { name: 'Explore', href: '/explore' },
  { name: 'Clusters', href: '/clusters' },
  { name: 'Analytics', href: '/analytics' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col bg-black">
      <div className="flex h-16 shrink-0 items-center px-5 py-9">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 bg-white rounded-sm flex items-center justify-center">
            <div className="grid grid-cols-2 gap-0.5">
              <div className="h-1.5 w-1.5 bg-black rounded-full"></div>
              <div className="h-1.5 w-1.5 bg-black rounded-full"></div>
              <div className="h-1.5 w-1.5 bg-black rounded-full"></div>
              <div className="h-1.5 w-1.5 bg-black rounded-full"></div>
            </div>
          </div>
          <span className="text-white text-xl font-semibold">Celestra</span>
        </div>
      </div>
      <nav className="flex flex-1 flex-col px-6 py-6">
        <ul role="list" className="flex flex-1 flex-col gap-y-2">
          {navigation.map((item) => (
            <li key={item.name}>
              <Link
                href={item.href}
                className={`group flex gap-x-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  pathname === item.href
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {item.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
