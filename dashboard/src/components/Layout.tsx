import { NavLink, Outlet } from 'react-router-dom'
import clsx from 'clsx'

export default function Layout() {
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    clsx(
      'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
      isActive
        ? 'bg-indigo-700 text-white'
        : 'text-indigo-100 hover:bg-indigo-600 hover:text-white'
    )

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      {/* Sidebar */}
      <aside className="flex flex-col w-56 bg-indigo-800 text-white flex-shrink-0">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-indigo-700">
          <span className="text-lg font-bold tracking-tight">Proceeds Navigator</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <NavLink to="/leads" className={navLinkClass}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Leads
          </NavLink>
          <NavLink to="/cases" className={navLinkClass}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            Cases
          </NavLink>
        </nav>

        {/* Compliance notice at bottom */}
        <div className="px-3 py-4 border-t border-indigo-700">
          <p className="text-xs text-indigo-300 leading-snug">
            Internal use only. Clients may file directly at no cost.
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
