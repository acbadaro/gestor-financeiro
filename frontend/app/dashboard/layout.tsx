'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, List, PieChart, BarChart2, Tags } from 'lucide-react'

const nav = [
  { href: '/dashboard',                    label: 'Visão Geral',  icon: LayoutDashboard },
  { href: '/dashboard/transacoes',         label: 'Transações',   icon: List },
  { href: '/dashboard/categorias',         label: 'Gastos',       icon: PieChart },
  { href: '/dashboard/relatorio',          label: 'Relatório',    icon: BarChart2 },
  { href: '/dashboard/categorias/config',  label: 'Categorias',   icon: Tags },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-white border-r flex flex-col">
        <div className="px-6 py-5 border-b">
          <span className="font-bold text-lg text-green-600">💰 Gestor</span>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                pathname === href || pathname.startsWith(href + '/') && href !== '/dashboard'
                  ? 'bg-green-50 text-green-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  )
}
