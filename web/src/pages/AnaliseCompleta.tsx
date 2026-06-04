import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { AlertCircle, ChevronDown } from 'lucide-react'
import { api } from '../lib/api'
import type { AnaliseCompleta as TAnalise, Jogo } from '../lib/api'
import { flag } from '../lib/flags'
import ProbBar from '../components/ProbBar'

function FormaRow({ data, mandante, visitante, placar_m, placar_v, competicao }: {
  data: string; mandante: string; visitante: string
  placar_m: number | null; placar_v: number | null; competicao: string
}) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-[#21262d] last:border-0 text-sm">
      <span className="text-[#484f58] text-xs w-12 flex-shrink-0 tabular-nums">{data.slice(5)}</span>
      <div className="flex-1 flex items-center justify-center gap-2 min-w-0">
        <span className="text-[#c9d1d9] text-xs text-right truncate flex-1">{flag(mandante)} {mandante}</span>
        <span className="font-bold text-[#e6edf3] bg-[#21262d] px-2.5 py-1 rounded-md text-xs flex-shrink-0 tabular-nums">
          {placar_m ?? '?'} – {placar_v ?? '?'}
        </span>
        <span className="text-[#c9d1d9] text-xs text-left truncate flex-1">{flag(visitante)} {visitante}</span>
      </div>
      <span className="text-[#484f58] text-xs w-20 text-right flex-shrink-0">
        {competicao.replace('elim_', '').replace('_2026', '').replace('_2022', '').toUpperCase()}
      </span>
    </div>
  )
}

function MercadoCard({ nome, mercado }: { nome: string; mercado: { media_esperada: number; prob_linhas: Record<string, number>; intervalo_80pct: [number, number]; ausente: boolean } }) {
  const labels: Record<string, string> = {
    escanteios: 'Escanteios',
    cartoes_amarelos: 'Cartões Amarelos',
    faltas: 'Faltas',
    chutes_time: 'Chutes Totais',
  }
  const icons: Record<string, string> = {
    escanteios: '🚩',
    cartoes_amarelos: '🟨',
    faltas: '⚠️',
    chutes_time: '🎯',
  }

  if (mercado.ausente) {
    return (
      <div className="bg-[#0d1117] border border-[#21262d] rounded-xl p-5 opacity-40">
        <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wide mb-1">{icons[nome]} {labels[nome] ?? nome}</div>
        <div className="text-[#484f58] text-sm">Dados insuficientes</div>
      </div>
    )
  }

  return (
    <div className="bg-[#0d1117] border border-[#30363d] rounded-xl p-5">
      <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wide mb-3">{icons[nome]} {labels[nome] ?? nome}</div>
      <div className="text-3xl font-black text-[#e6edf3] mb-1 tabular-nums">{mercado.media_esperada}</div>
      <div className="text-[#484f58] text-xs mb-4">
        IC 80%: {mercado.intervalo_80pct[0]}–{mercado.intervalo_80pct[1]}
      </div>
      <div className="space-y-2">
        {Object.entries(mercado.prob_linhas).map(([linha, prob]) => (
          <div key={linha} className="flex items-center gap-2">
            <span className="text-[#484f58] text-xs w-14 flex-shrink-0">Over {linha}</span>
            <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#388bfd] to-[#58a6ff] rounded-full transition-all"
                style={{ width: `${Math.round(prob * 100)}%` }}
              />
            </div>
            <span className="text-[#c9d1d9] text-xs w-9 text-right flex-shrink-0 tabular-nums font-medium">
              {Math.round(prob * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatPill({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className={`rounded-xl px-5 py-4 border ${accent ? 'bg-[#388bfd12] border-[#388bfd30]' : 'bg-[#161b22] border-[#30363d]'}`}>
      <div className={`text-2xl font-black tabular-nums ${accent ? 'text-[#58a6ff]' : 'text-[#e6edf3]'}`}>{value}</div>
      <div className="text-[#484f58] text-xs mt-1 font-medium uppercase tracking-wide">{label}</div>
    </div>
  )
}

export default function AnaliseCompletaPage() {
  const [searchParams] = useSearchParams()
  const jogoIdParam = searchParams.get('jogo')

  const { data: todosJogos = [] } = useQuery<Jogo[]>({
    queryKey: ['jogos'],
    queryFn: () => api.jogos(),
    staleTime: 10 * 60 * 1000,
  })

  const [jogoId, setJogoId] = useState<number | null>(null)

  useEffect(() => {
    if (jogoIdParam) {
      setJogoId(Number(jogoIdParam))
    } else if (todosJogos.length > 0 && !jogoId) {
      const hoje = new Date().toISOString().slice(0, 10)
      const proximo = todosJogos.find(j => j.data >= hoje && !j.placar_m) ?? todosJogos[0]
      setJogoId(proximo.id)
    }
  }, [jogoIdParam, todosJogos])

  const { data: analise, isLoading, error } = useQuery<TAnalise>({
    queryKey: ['analise', jogoId],
    queryFn: () => api.analise(jogoId!),
    enabled: !!jogoId,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div className="px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-[#e6edf3] tracking-tight">Análise Completa</h1>
        <p className="text-[#8b949e] text-sm mt-1.5">Dixon-Coles · mercados secundários · forma recente · head-to-head</p>
      </div>

      {/* Seletor de jogo */}
      <div className="mb-8 relative">
        <label className="block text-[#8b949e] text-xs font-semibold mb-2 uppercase tracking-wider">Selecionar Jogo</label>
        <div className="relative">
          <select
            className="w-full bg-[#161b22] border border-[#30363d] text-[#e6edf3] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#58a6ff] focus:ring-1 focus:ring-[#388bfd40] appearance-none pr-10 cursor-pointer"
            value={jogoId ?? ''}
            onChange={e => setJogoId(Number(e.target.value))}
          >
            {todosJogos.map(j => (
              <option key={j.id} value={j.id}>
                {j.data} · {j.mandante} × {j.visitante} (Grupo {j.grupo})
              </option>
            ))}
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8b949e] pointer-events-none" />
        </div>
      </div>

      {isLoading && (
        <div className="space-y-5 animate-pulse">
          <div className="h-52 bg-[#161b22] rounded-2xl border border-[#30363d]" />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[1,2,3,4].map(i => <div key={i} className="h-24 bg-[#161b22] rounded-xl border border-[#30363d]" />)}
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 text-[#f85149] bg-[#f851491a] border border-[#f8514930] rounded-xl px-5 py-4">
          <AlertCircle size={18} />
          <span className="text-sm font-medium">Erro ao carregar análise</span>
        </div>
      )}

      {analise?.ok && (
        <div className="space-y-6">
          {/* Hero — times */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl overflow-hidden">
            <div className="px-5 py-3 bg-[#1c2128] border-b border-[#30363d] flex items-center justify-between">
              <span className="text-xs text-[#8b949e] font-semibold uppercase tracking-wider">
                Grupo {analise.jogo.grupo} · {analise.jogo.fase} · {analise.jogo.cidade}
                {analise.jogo.hora && ` · ${analise.jogo.hora} UTC`}
              </span>
              <span className="text-xs text-[#484f58]">{analise.jogo.data}</span>
            </div>

            <div className="px-8 py-8">
              <div className="flex items-center justify-between mb-8">
                {/* Mandante */}
                <div className="flex-1 flex flex-col items-center gap-3">
                  <div className="text-7xl leading-none">{flag(analise.mandante.nome)}</div>
                  <div className="text-center">
                    <div className="text-[#e6edf3] font-black text-xl">{analise.mandante.nome}</div>
                    {analise.mandante.elo && (
                      <div className="text-[#484f58] text-sm mt-0.5">Elo {analise.mandante.elo}</div>
                    )}
                  </div>
                </div>

                {/* VS */}
                <div className="px-10 text-center">
                  <div className="text-[#30363d] text-3xl font-black">VS</div>
                </div>

                {/* Visitante */}
                <div className="flex-1 flex flex-col items-center gap-3">
                  <div className="text-7xl leading-none">{flag(analise.visitante.nome)}</div>
                  <div className="text-center">
                    <div className="text-[#e6edf3] font-black text-xl">{analise.visitante.nome}</div>
                    {analise.visitante.elo && (
                      <div className="text-[#484f58] text-sm mt-0.5">Elo {analise.visitante.elo}</div>
                    )}
                  </div>
                </div>
              </div>

              <ProbBar
                mandante={analise.mandante.nome}
                visitante={analise.visitante.nome}
                probM={analise.previsao.prob_vitoria_m}
                probE={analise.previsao.prob_empate}
                probV={analise.previsao.prob_vitoria_v}
              />
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <StatPill
              label="Gols esperados"
              value={`${analise.previsao.gols_esperados_m} – ${analise.previsao.gols_esperados_v}`}
              accent
            />
            <StatPill
              label="Over 2.5"
              value={`${Math.round((analise.previsao.prob_over['2.5'] ?? 0) * 100)}%`}
            />
            <StatPill
              label="Over 1.5"
              value={`${Math.round((analise.previsao.prob_over['1.5'] ?? 0) * 100)}%`}
            />
            <StatPill
              label={`Vitória ${analise.mandante.nome}`}
              value={`${Math.round(analise.previsao.prob_vitoria_m * 100)}%`}
            />
            {analise.previsao.cold_start && (
              <div className="bg-[#d299221a] border border-[#d2992230] rounded-xl px-5 py-4">
                <div className="text-[#d29922] text-2xl font-black">!</div>
                <div className="text-[#d29922] text-xs mt-1 font-semibold uppercase tracking-wide">Cold Start</div>
                <div className="text-[#8b949e] text-xs mt-0.5">Histórico escasso</div>
              </div>
            )}
          </div>

          {/* Mercados secundários */}
          <div>
            <h2 className="text-[#e6edf3] font-bold text-base mb-4 flex items-center gap-2">
              Mercados Secundários
              <span className="text-xs text-[#484f58] font-normal">baseado em dados históricos</span>
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(analise.mercados).map(([k, m]) => (
                <MercadoCard key={k} nome={k} mercado={m} />
              ))}
            </div>
          </div>

          {/* Forma recente + H2H */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-5">
              <h3 className="text-[#e6edf3] text-sm font-bold mb-4 flex items-center gap-2">
                <span className="text-xl">{flag(analise.mandante.nome)}</span>
                Forma recente — {analise.mandante.nome}
              </h3>
              {analise.forma_recente.mandante.length === 0 ? (
                <p className="text-[#484f58] text-sm py-4 text-center">Sem dados disponíveis</p>
              ) : (
                analise.forma_recente.mandante.map((j, i) => <FormaRow key={i} {...j} />)
              )}
            </div>
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-5">
              <h3 className="text-[#e6edf3] text-sm font-bold mb-4 flex items-center gap-2">
                <span className="text-xl">{flag(analise.visitante.nome)}</span>
                Forma recente — {analise.visitante.nome}
              </h3>
              {analise.forma_recente.visitante.length === 0 ? (
                <p className="text-[#484f58] text-sm py-4 text-center">Sem dados disponíveis</p>
              ) : (
                analise.forma_recente.visitante.map((j, i) => <FormaRow key={i} {...j} />)
              )}
            </div>
          </div>

          {/* Head-to-Head */}
          {analise.head_to_head.length > 0 && (
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-5">
              <h3 className="text-[#e6edf3] text-sm font-bold mb-4">Histórico direto (H2H)</h3>
              {analise.head_to_head.map((j, i) => <FormaRow key={i} {...j} />)}
            </div>
          )}

          {/* Fatores ausentes */}
          {analise.fatores_ausentes?.length > 0 && (
            <div className="bg-[#d299221a] border border-[#d2992230] rounded-xl p-5">
              <div className="flex items-center gap-2 text-[#d29922] text-sm font-bold mb-3">
                <AlertCircle size={16} />
                Fatores ausentes na análise
              </div>
              <ul className="space-y-1.5">
                {analise.fatores_ausentes.map((f, i) => (
                  <li key={i} className="text-[#8b949e] text-sm flex items-start gap-2">
                    <span className="text-[#d29922] mt-0.5">·</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!jogoId && todosJogos.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center py-24 text-[#8b949e]">
          <div className="text-6xl mb-4">📊</div>
          <div className="font-semibold text-lg text-[#e6edf3]">Nenhum jogo disponível</div>
        </div>
      )}
    </div>
  )
}
