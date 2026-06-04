import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { TopElo } from '../lib/api'
import { flag } from '../lib/flags'

export default function Calibracao() {
  const { data: cal } = useQuery({
    queryKey: ['calibracao'],
    queryFn: api.calibracao,
  })

  const { data: topElo = [] } = useQuery<TopElo[]>({
    queryKey: ['top-elo'],
    queryFn: api.topElo,
    staleTime: 10 * 60 * 1000,
  })

  const maxElo = topElo.length > 0 ? topElo[0].elo : 1800
  const minElo = 1400

  return (
    <div className="px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-[#e6edf3] tracking-tight">Painel de Calibração</h1>
        <p className="text-[#8b949e] text-sm mt-1.5">
          Qualidade das previsões medida por Brier score e log-loss — apenas relatórios marcados como <strong className="text-[#c9d1d9]">oficiais</strong> entram nesta análise.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-5 mb-8 max-w-sm">
        <div className="bg-[#161b22] border border-[#30363d] rounded-2xl px-6 py-5">
          <div className="text-3xl font-black text-[#58a6ff] tabular-nums">{cal?.relatorios_oficiais ?? '–'}</div>
          <div className="text-[#484f58] text-xs font-semibold uppercase tracking-wide mt-1.5">Relatórios oficiais</div>
        </div>
        <div className="bg-[#161b22] border border-[#30363d] rounded-2xl px-6 py-5">
          <div className="text-3xl font-black text-[#3fb950] tabular-nums">{cal?.total_avaliados ?? '–'}</div>
          <div className="text-[#484f58] text-xs font-semibold uppercase tracking-wide mt-1.5">Previsões avaliadas</div>
        </div>
      </div>

      {cal?.msg && (
        <div className="bg-[#d299221a] border border-[#d2992230] rounded-xl px-5 py-4 mb-8 text-[#d29922] text-sm">
          {cal.msg}
        </div>
      )}

      {!cal?.msg && cal?.total_avaliados === 0 && (
        <div className="bg-[#388bfd0d] border border-[#388bfd20] rounded-xl px-5 py-4 mb-8 text-[#58a6ff] text-sm">
          Nenhuma previsão com resultado disponível ainda. O painel ficará ativo após os primeiros jogos da Copa.
        </div>
      )}

      {/* Top Elo */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#30363d] flex items-baseline justify-between">
          <div>
            <h2 className="text-[#e6edf3] font-bold text-base">Top 10 — Rating Elo</h2>
            <p className="text-[#484f58] text-xs mt-0.5">Calculado sobre Copa 2022 + qualificatórias 2025/26</p>
          </div>
          <span className="text-[#484f58] text-xs">{topElo.length} times</span>
        </div>

        <div className="divide-y divide-[#21262d]">
          {topElo.map((t, i) => {
            const pct = Math.max(0, Math.min(100, Math.round(((t.elo - minElo) / (maxElo - minElo)) * 100)))
            const isTop3 = i < 3
            return (
              <div key={t.nome} className="flex items-center gap-4 px-6 pr-8 py-4 hover:bg-[#1c2128] transition-colors">
                {/* Rank */}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-black flex-shrink-0 ${
                  i === 0 ? 'bg-[#d2992220] text-[#d29922]' :
                  i === 1 ? 'bg-[#8b949e20] text-[#8b949e]' :
                  i === 2 ? 'bg-[#f0883e20] text-[#f0883e]' :
                  'bg-[#21262d] text-[#484f58]'
                }`}>
                  {i + 1}
                </div>

                {/* Flag */}
                <div className="text-3xl leading-none flex-shrink-0">{flag(t.nome)}</div>

                {/* Name + group */}
                <div className="flex-1 min-w-0">
                  <div className="text-[#e6edf3] font-semibold text-sm">{t.nome}</div>
                  {t.grupo && <div className="text-[#484f58] text-xs mt-0.5">Grupo {t.grupo}</div>}
                </div>

                {/* Bar */}
                <div className="w-32 flex-shrink-0">
                  <div className="h-1.5 bg-[#21262d] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${isTop3 ? 'bg-gradient-to-r from-[#388bfd] to-[#58a6ff]' : 'bg-[#388bfd]'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>

                {/* Elo */}
                <div className="text-right flex-shrink-0 w-20">
                  <div className={`font-black text-sm tabular-nums ${isTop3 ? 'text-[#58a6ff]' : 'text-[#c9d1d9]'}`}>{t.elo}</div>
                  <div className="text-[#484f58] text-xs">Elo</div>
                </div>
              </div>
            )
          })}

          {topElo.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-[#484f58]">
              <div className="text-4xl mb-3">🏆</div>
              <div className="text-sm">Nenhum dado de Elo disponível</div>
              <div className="text-xs mt-1">Execute o recálculo em "Atualizar Dados"</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
