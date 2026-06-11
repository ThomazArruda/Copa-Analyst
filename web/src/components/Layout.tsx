import { NavLink, Outlet } from 'react-router-dom'
import { BarChart2, Calendar, Database, Sliders, Brain, Trophy, Award } from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { to: '/', label: 'Jogos do Dia', icon: Calendar },
  { to: '/analise', label: 'Análise Dixon-Coles', icon: BarChart2 },
  { to: '/relatorio', label: 'Relatório IA', icon: Brain },
  { to: '/bolao', label: 'Bolão', icon: Award },
  { to: '/calibracao', label: 'Calibração', icon: Sliders },
  { to: '/atualizar', label: 'Atualizar Dados', icon: Database },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-[#161b22] border-r border-[#30363d] flex flex-col">
        {/* Logo */}
        <div className="px-6 py-7 border-b border-[#30363d]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#388bfd] to-[#1f6feb] flex items-center justify-center shadow-lg">
              <Trophy size={18} className="text-white" />
            </div>
            <div>
              <div className="text-[#e6edf3] font-bold text-base leading-tight tracking-tight">Copa Analyst</div>
              <div className="text-[#8b949e] text-xs mt-0.5">Mundial 2026</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-5 space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-[#388bfd1a] text-[#58a6ff] border border-[#388bfd30]'
                    : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] border border-transparent'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-5 border-t border-[#30363d]">
          <div className="flex items-center gap-2 mb-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-[#3fb950] animate-pulse" />
            <span className="text-[#8b949e] text-xs font-medium">API online</span>
          </div>
          <div className="text-[#484f58] text-xs">
            {new Date().toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-[#0d1117]">
        <Outlet />
      </main>
    </div>
  )
}
