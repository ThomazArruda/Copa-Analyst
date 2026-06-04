import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Zap, CheckCircle, AlertCircle, Database, Globe } from 'lucide-react'
import { api } from '../lib/api'

function StatBlock({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-2xl px-6 py-5">
      <div className={`text-3xl font-black tabular-nums ${accent ? 'text-[#58a6ff]' : 'text-[#e6edf3]'}`}>{value}</div>
      <div className="text-[#484f58] text-xs font-semibold uppercase tracking-wide mt-1.5">{label}</div>
    </div>
  )
}

export default function AtualizarDados() {
  const qc = useQueryClient()
  const [msgAtualizar, setMsgAtualizar] = useState<string | null>(null)
  const [msgElo, setMsgElo] = useState<string | null>(null)

  const { data: status } = useQuery({
    queryKey: ['status'],
    queryFn: api.status,
    refetchInterval: 10_000,
  })

  const mutAtualizar = useMutation({
    mutationFn: api.atualizar,
    onSuccess: (d) => {
      setMsgAtualizar(d.msg)
      setTimeout(() => qc.invalidateQueries({ queryKey: ['status'] }), 3000)
    },
  })

  const mutElo = useMutation({
    mutationFn: api.recalcularElo,
    onSuccess: (d) => {
      setMsgElo(`Elo recalculado para ${d.times_atualizados} times.`)
      qc.invalidateQueries({ queryKey: ['top-elo'] })
    },
  })

  return (
    <div className="px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-[#e6edf3] tracking-tight">Atualizar Dados</h1>
        <p className="text-[#8b949e] text-sm mt-1.5">
          Mantém o banco de dados sincronizado durante a Copa do Mundo 2026.
        </p>
      </div>

      {/* Status do banco */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Database size={15} className="text-[#8b949e]" />
          <h2 className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider">Status do Banco</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatBlock label="Jogos total" value={status?.jogos_total ?? '–'} />
          <StatBlock label="Fixtures Copa 26" value={status?.copa26_fixtures ?? '–'} accent />
          <StatBlock label="Relatórios" value={status?.relatorios ?? '–'} />
          <StatBlock label="Previsões oficiais" value={status?.previsoes_oficiais ?? '–'} />
          <StatBlock label="Times" value={status?.times ?? '–'} />
        </div>
      </div>

      {/* Ações */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <Zap size={15} className="text-[#8b949e]" />
          <h2 className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider">Ações</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Atualizar resultados */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6">
            <h3 className="text-[#e6edf3] font-bold text-base mb-1">Resultados Copa 2026</h3>
            <p className="text-[#8b949e] text-sm mb-5">
              Busca resultados atualizados via TheSportsDB. Execute após cada rodada de jogos.
            </p>
            <button
              onClick={() => mutAtualizar.mutate()}
              disabled={mutAtualizar.isPending}
              className="w-full flex items-center justify-center gap-2 bg-[#21262d] hover:bg-[#388bfd] border border-[#30363d] hover:border-[#388bfd] text-[#e6edf3] rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <RefreshCw size={15} className={mutAtualizar.isPending ? 'animate-spin' : ''} />
              {mutAtualizar.isPending ? 'Atualizando...' : 'Atualizar resultados'}
            </button>
            {msgAtualizar && (
              <div className="mt-3 flex items-center gap-2 text-[#3fb950] text-sm bg-[#3fb9501a] rounded-lg px-3 py-2">
                <CheckCircle size={14} /> {msgAtualizar}
              </div>
            )}
            {mutAtualizar.isError && (
              <div className="mt-3 flex items-center gap-2 text-[#f85149] text-sm bg-[#f851491a] rounded-lg px-3 py-2">
                <AlertCircle size={14} /> Erro ao atualizar
              </div>
            )}
          </div>

          {/* Recalcular Elo */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6">
            <h3 className="text-[#e6edf3] font-bold text-base mb-1">Rating Prior (Elo)</h3>
            <p className="text-[#8b949e] text-sm mb-5">
              Recalcula o Elo de todos os times com base nos dados históricos do banco.
            </p>
            <button
              onClick={() => mutElo.mutate()}
              disabled={mutElo.isPending}
              className="w-full flex items-center justify-center gap-2 bg-[#21262d] hover:bg-[#388bfd] border border-[#30363d] hover:border-[#388bfd] text-[#e6edf3] rounded-xl px-4 py-3 text-sm font-semibold transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Zap size={15} className={mutElo.isPending ? 'animate-pulse' : ''} />
              {mutElo.isPending ? 'Recalculando...' : 'Recalcular Elo'}
            </button>
            {msgElo && (
              <div className="mt-3 flex items-center gap-2 text-[#3fb950] text-sm bg-[#3fb9501a] rounded-lg px-3 py-2">
                <CheckCircle size={14} /> {msgElo}
              </div>
            )}
            {mutElo.isError && (
              <div className="mt-3 flex items-center gap-2 text-[#f85149] text-sm bg-[#f851491a] rounded-lg px-3 py-2">
                <AlertCircle size={14} /> Erro ao recalcular
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Fontes de dados */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Globe size={15} className="text-[#8b949e]" />
          <h2 className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider">Fontes de Dados</h2>
        </div>
        <div className="bg-[#161b22] border border-[#30363d] rounded-2xl divide-y divide-[#21262d]">
          {[
            { src: 'TheSportsDB', desc: 'Resultados em tempo real da Copa 2026', tier: 'Gratuito' },
            { src: 'OpenFootball', desc: 'Calendário Copa 2026 + resultados Copa 2022', tier: 'Gratuito' },
            { src: 'Wikipedia', desc: 'Qualificatórias 2025/26 (CONMEBOL, UEFA, CONCACAF, AFC, CAF)', tier: 'Gratuito' },
            { src: 'API-Football', desc: 'Estatísticas avançadas (escanteios, chutes, cartões)', tier: 'Requer chave' },
          ].map(({ src, desc, tier }) => (
            <div key={src} className="flex items-center gap-4 px-6 py-4">
              <span className={`flex-shrink-0 text-xs px-2.5 py-1 rounded-full font-medium ${
                tier === 'Gratuito'
                  ? 'bg-[#3fb9501a] text-[#3fb950] border border-[#3fb95030]'
                  : 'bg-[#d299221a] text-[#d29922] border border-[#d2992230]'
              }`}>{tier}</span>
              <div className="flex-1 min-w-0">
                <span className="text-[#e6edf3] font-semibold text-sm">{src}</span>
                <span className="text-[#8b949e] text-sm ml-2">{desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
