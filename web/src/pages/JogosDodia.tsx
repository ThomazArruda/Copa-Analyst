import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, MapPin, Clock, TrendingUp, ArrowRight } from 'lucide-react'
import { api } from '../lib/api'
import type { Jogo, Previsao } from '../lib/api'
import { flagUrl } from '../lib/flags'
import ProbBar from '../components/ProbBar'
import Tag from '../components/Tag'

function JogoCard({ jogo }: { jogo: Jogo }) {
  const navigate = useNavigate()
  const [showPrevisao, setShowPrevisao] = useState(false)

  const { data: prev, isLoading } = useQuery<Previsao>({
    queryKey: ['previsao', jogo.id],
    queryFn: () => api.previsao(jogo.id),
    enabled: showPrevisao,
    staleTime: 5 * 60 * 1000,
  })

  const temPlacar = jogo.placar_m !== null && jogo.placar_v !== null

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-2xl overflow-hidden hover:border-[#58a6ff40] hover:shadow-xl hover:shadow-black/20 transition-all duration-200">
      {/* Header grupo/fase */}
      <div className="px-5 py-3 bg-[#1c2128] border-b border-[#30363d] flex items-center justify-between">
        <span className="text-xs text-[#8b949e] font-semibold uppercase tracking-wider">
          Grupo {jogo.grupo} · {jogo.fase?.replace('matchday', 'Rodada').replace('group', 'Fase de Grupos')}
        </span>
        {temPlacar ? (
          <span className="text-xs font-bold text-[#3fb950] bg-[#3fb9501a] px-2.5 py-1 rounded-full border border-[#3fb95030]">
            Encerrado
          </span>
        ) : jogo.hora ? (
          <span className="flex items-center gap-1 text-xs text-[#8b949e]">
            <Clock size={10} />
            {jogo.hora} UTC
          </span>
        ) : null}
      </div>

      <div className="px-6 py-6">
        {/* Times e placar */}
        <div className="flex items-center justify-between mb-5">
          {/* Mandante */}
          <div className="flex-1 flex flex-col items-center gap-2">
            <div className="w-12 h-9 flex items-center justify-center">
              {flagUrl(jogo.mandante)
                ? <img src={flagUrl(jogo.mandante)} alt={jogo.mandante} className="w-12 h-auto rounded shadow-sm" />
                : <span className="text-3xl">🏳️</span>}
            </div>
            <div className="text-center">
              <div className="text-[#e6edf3] font-bold text-base">{jogo.mandante}</div>
              {jogo.mandante_elo && (
                <div className="text-[#484f58] text-xs mt-0.5">Elo {jogo.mandante_elo}</div>
              )}
            </div>
          </div>

          {/* Placar ou VS */}
          <div className="flex-shrink-0 text-center px-6">
            {temPlacar ? (
              <div>
                <div className="text-4xl font-black text-[#e6edf3] tracking-tight tabular-nums">
                  {jogo.placar_m} — {jogo.placar_v}
                </div>
                <div className="text-[#484f58] text-xs mt-1">resultado final</div>
              </div>
            ) : (
              <div>
                <div className="text-2xl font-black text-[#30363d]">VS</div>
              </div>
            )}
          </div>

          {/* Visitante */}
          <div className="flex-1 flex flex-col items-center gap-2">
            <div className="w-12 h-9 flex items-center justify-center">
              {flagUrl(jogo.visitante)
                ? <img src={flagUrl(jogo.visitante)} alt={jogo.visitante} className="w-12 h-auto rounded shadow-sm" />
                : <span className="text-3xl">🏳️</span>}
            </div>
            <div className="text-center">
              <div className="text-[#e6edf3] font-bold text-base">{jogo.visitante}</div>
              {jogo.visitante_elo && (
                <div className="text-[#484f58] text-xs mt-0.5">Elo {jogo.visitante_elo}</div>
              )}
            </div>
          </div>
        </div>

        {/* Cidade */}
        {jogo.cidade && (
          <div className="flex items-center gap-1.5 text-[#484f58] text-xs justify-center mb-4">
            <MapPin size={10} />
            {jogo.cidade}
          </div>
        )}

        {/* Previsão toggle */}
        {!temPlacar && (
          <div className="border-t border-[#21262d] pt-4">
            {!showPrevisao ? (
              <button
                onClick={() => setShowPrevisao(true)}
                className="w-full flex items-center justify-center gap-2 text-sm text-[#8b949e] hover:text-[#58a6ff] transition-colors py-2 rounded-lg hover:bg-[#388bfd0d]"
              >
                <TrendingUp size={14} />
                Ver previsão Dixon-Coles
              </button>
            ) : isLoading ? (
              <div className="space-y-3 animate-pulse py-1">
                <div className="h-2.5 bg-[#30363d] rounded-full" />
                <div className="flex justify-between">
                  <div className="h-4 w-12 bg-[#30363d] rounded" />
                  <div className="h-4 w-12 bg-[#30363d] rounded" />
                  <div className="h-4 w-12 bg-[#30363d] rounded" />
                </div>
              </div>
            ) : prev?.ok ? (
              <div className="space-y-4">
                <ProbBar
                  mandante={jogo.mandante}
                  visitante={jogo.visitante}
                  probM={prev.prob_vitoria_m}
                  probE={prev.prob_empate}
                  probV={prev.prob_vitoria_v}
                />
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-[#1c2128] rounded-lg px-3 py-2 text-center">
                    <div className="text-[#e6edf3] font-bold text-sm">{prev.gols_esperados_m}</div>
                    <div className="text-[#484f58] text-xs">Gols esp. M</div>
                  </div>
                  <div className="bg-[#1c2128] rounded-lg px-3 py-2 text-center">
                    <div className="text-[#3fb950] font-bold text-sm">{Math.round((prev.prob_over['2.5'] ?? 0) * 100)}%</div>
                    <div className="text-[#484f58] text-xs">Over 2.5</div>
                  </div>
                  <div className="bg-[#1c2128] rounded-lg px-3 py-2 text-center">
                    <div className="text-[#e6edf3] font-bold text-sm">{prev.gols_esperados_v}</div>
                    <div className="text-[#484f58] text-xs">Gols esp. V</div>
                  </div>
                </div>
                {prev.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {prev.tags.map((t, i) => <Tag key={i} label={t} />)}
                  </div>
                )}
                <button
                  onClick={() => navigate(`/analise?jogo=${jogo.id}`)}
                  className="w-full flex items-center justify-center gap-2 text-sm text-[#58a6ff] hover:text-white bg-[#388bfd15] hover:bg-[#388bfd] rounded-lg py-2.5 transition-all duration-150 font-medium border border-[#388bfd30] hover:border-[#388bfd]"
                >
                  Análise completa
                  <ArrowRight size={14} />
                </button>
              </div>
            ) : (
              <div className="text-sm text-[#8b949e] text-center py-2">
                Previsão indisponível
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function JogosDodia() {
  const [dataAtual, setDataAtual] = useState<string>('')

  const { data: datas = [], isLoading: loadingDatas } = useQuery({
    queryKey: ['datas'],
    queryFn: api.datas,
    staleTime: 10 * 60 * 1000,
  })

  useEffect(() => {
    if (datas.length === 0 || dataAtual) return
    const hoje = new Date().toISOString().slice(0, 10)
    const futura = datas.find(d => d >= hoje)
    setDataAtual(futura ?? datas[0])
  }, [datas, dataAtual])

  const { data: jogos = [], isLoading: loadingJogos } = useQuery({
    queryKey: ['jogos', dataAtual],
    queryFn: () => api.jogos(dataAtual),
    enabled: !!dataAtual,
    staleTime: 5 * 60 * 1000,
  })

  const idxAtual = datas.indexOf(dataAtual)
  const podeAnterior = idxAtual > 0
  const podePróximo = idxAtual < datas.length - 1

  function fmtData(d: string) {
    if (!d) return ''
    const dt = new Date(d + 'T12:00:00')
    return dt.toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' })
  }

  function fmtDataLong(d: string) {
    if (!d) return ''
    const dt = new Date(d + 'T12:00:00')
    return dt.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  }

  return (
    <div className="px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-[#e6edf3] tracking-tight">Jogos do Dia</h1>
        <p className="text-[#8b949e] text-sm mt-1.5">Copa do Mundo 2026 — Previsões Dixon-Coles em tempo real</p>
      </div>

      {/* Navegação de datas */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => setDataAtual(datas[idxAtual - 1])}
          disabled={!podeAnterior}
          className="p-2.5 rounded-xl border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#58a6ff] hover:bg-[#388bfd0d] disabled:opacity-25 disabled:cursor-not-allowed transition-all"
        >
          <ChevronLeft size={18} />
        </button>

        <div className="flex-1 overflow-x-auto flex gap-2 py-1 scrollbar-hide">
          {loadingDatas ? (
            <div className="h-10 w-72 bg-[#21262d] rounded-xl animate-pulse" />
          ) : (
            datas.map(d => (
              <button
                key={d}
                onClick={() => setDataAtual(d)}
                className={`flex-shrink-0 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-150 ${
                  d === dataAtual
                    ? 'bg-[#388bfd] text-white shadow-lg shadow-[#388bfd30]'
                    : 'bg-[#161b22] border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#58a6ff40]'
                }`}
              >
                {fmtData(d)}
              </button>
            ))
          )}
        </div>

        <button
          onClick={() => setDataAtual(datas[idxAtual + 1])}
          disabled={!podePróximo}
          className="p-2.5 rounded-xl border border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#58a6ff] hover:bg-[#388bfd0d] disabled:opacity-25 disabled:cursor-not-allowed transition-all"
        >
          <ChevronRight size={18} />
        </button>
      </div>

      {/* Título da data selecionada */}
      {dataAtual && !loadingJogos && (
        <div className="flex items-baseline gap-3 mb-6">
          <h2 className="text-[#e6edf3] font-semibold text-lg capitalize">{fmtDataLong(dataAtual)}</h2>
          <span className="text-[#484f58] text-sm">
            {jogos.length} {jogos.length === 1 ? 'jogo' : 'jogos'}
          </span>
        </div>
      )}

      {/* Cards */}
      {loadingJogos ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-[#161b22] border border-[#30363d] rounded-2xl h-56 animate-pulse" />
          ))}
        </div>
      ) : jogos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-[#8b949e]">
          <div className="text-6xl mb-4">📅</div>
          <div className="font-semibold text-lg text-[#e6edf3]">Nenhum jogo nesta data</div>
          <div className="text-sm mt-1">Selecione outra data no calendário acima</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
          {jogos.map(j => <JogoCard key={j.id} jogo={j} />)}
        </div>
      )}
    </div>
  )
}
