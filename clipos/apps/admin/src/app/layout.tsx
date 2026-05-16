import type { Metadata } from 'next';
import './globals.css';
import Sidebar from '@/components/Sidebar';
import Providers from './providers';

export const metadata: Metadata = {
  title: 'ClipOS Admin',
  description: 'Autonomous short-form video clipping system — admin dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 overflow-auto p-8 bg-gray-50">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
