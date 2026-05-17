'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Users,
  Video,
  Scissors,
  FileVideo,
  Send,
  BarChart2,
  Settings,
  Activity,
} from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/creators', label: 'Creators', icon: Users },
  { href: '/videos', label: 'Videos', icon: Video },
  { href: '/candidates', label: 'Candidates', icon: Scissors },
  { href: '/assets', label: 'Assets', icon: FileVideo },
  { href: '/publishing', label: 'Publishing', icon: Send },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/health', label: 'Health', icon: Activity },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 min-h-screen bg-gray-900 text-gray-100 flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <span className="text-xl font-bold tracking-tight text-white">
          ClipOS
        </span>
        <span className="ml-2 text-xs text-gray-400 font-medium uppercase tracking-widest">
          Admin
        </span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                active
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        ClipOS v0.1.0
      </div>
    </aside>
  );
}
