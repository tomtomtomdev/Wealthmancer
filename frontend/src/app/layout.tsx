'use client';

import './globals.css';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Upload,
  PieChart,
  ArrowLeftRight,
  Landmark,
  TrendingUp,
  Settings as SettingsIcon,
} from 'lucide-react';
import { cn } from '@/lib/formatters';
import { Geist } from "next/font/google";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/upload', label: 'Upload', icon: Upload },
  { href: '/portfolio', label: 'Portfolio', icon: PieChart },
  { href: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { href: '/accounts', label: 'Accounts', icon: Landmark },
  { href: '/settings', label: 'Settings', icon: SettingsIcon },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <html lang="en" className={cn("dark", "font-sans", geist.variable)}>
      <body className="bg-slate-950 text-white antialiased min-h-screen flex">
        {/* Sidebar */}
        <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col fixed h-full z-30">
          <div className="p-6 border-b border-slate-800">
            <Link href="/dashboard" className="flex items-center gap-2">
              <TrendingUp className="h-7 w-7 text-emerald-400" />
              <span className="text-xl font-bold tracking-tight">
                Wealthmancer
              </span>
            </Link>
          </div>
          <nav className="flex-1 p-4 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="p-4 border-t border-slate-800">
            <p className="text-xs text-slate-500 text-center">
              Wealthmancer v1.0
            </p>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 ml-64 min-h-screen">
          <div className="p-8">{children}</div>
        </main>
      </body>
    </html>
  );
}
