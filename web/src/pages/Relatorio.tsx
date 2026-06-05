import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Brain, ChevronDown, AlertCircle, CheckCircle, Clock, RefreshCw, Star, FileText } from 'lucide-react'
import { api } from '../lib/api'
import type { Jogo, PrevisaoIA } from '../lib/api'

// ---------------------------------------------------------------------------
// Badges
// ---------------------------------------------------------------------------

const ORIGEM_STYLE: Record<string, string> = {
  calculado: 'bg-[#388bfd1a] text-[#58a6ff] border-[#388bfd30]',
  hibrido: 'bg-[#8957e51a] text-[#c9a2ff] border-[#8957e530]',
  qualitativo: 'bg-[#d299221a] text-[#d29922] border-[#d2992230]',
}
const ORIGEM_LABEL: Record<string, string> = {
  calculado: 'Calculado',
  hibrido: 'Híbrido',
  qualitativo: 'Qualitativo',
}
const INCERTEZA_STYLE: Record<string, string> = {
  baixa: 'bg-[#3fb9501a] text-[#3fb950] border-[#3fb95030]',
  media: 'bg-[#d299221a] text-[#d29922] border-[#d2992230]',
  alta: 'bg-[#f851491a] text-[#f85149] border-[#f8514930]',
}
const MERCADO_LABEL: Record<string, string> = {
  resultado: 'Resultado (1X2)',
  total_gols: 'Total de Gols',
  ambas_marcam: 'Ambas Marcam',
  escanteios: 'Escanteios',
  cartoes_amarelos: 'Cartões Amarelos',
  faltas: 'Faltas',
  chutes_time: 'Chutes por Time',
}

function Badge({ text, style }: { text: string; style: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${style}`}>
      {text}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Card de previsão individual
// ---------------------------------------------------------------------------

function PrevisaoCard({ p }: { p: PrevisaoIA }) {
  const [aberto, setAberto] = useState(false)
  const prob = p.probabilidade_estimada
  const probOrig = p.probabilidade_calculada_original

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      <button
        className="w-full px-5 py-4 flex items-center gap-3 text-left hover:bg-[#1c2128] transition-colors"
        onClick={() => setAberto(!aberto)}
      >
        {/* Mercado */}
        <div className="flex-1 min-w-0">
          <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-1">
            {MERCADO_LABEL[p.mercado] ?? p.mercado}
          </div>
          <div className="text-[#e6edf3] font-bold text-sm">{p.previsao}</div>
        </div>

        {/* Probabilidade */}
        {prob !== null && prob !== undefined && (
          <div className="flex-shrink-0 text-right">
            <div className="text-[#e6edf3] font-black text-2xl tabular-nums">
              {Math.round(prob * 100)}%
            </div>
            {p.origem === 'hibrido' && probOrig !== null && probOrig !== undefined && (
              <div className="text-[#484f58] text-xs tabular-nums">
                base: {Math.round(probOrig * 100)}%
              </div>
            )}
          </div>
        )}

        {/* Badges */}
        <div className="flex-shrink-0 flex flex-col gap-1.5 items-end">
          <Badge text={ORIGEM_LABEL[p.origem] ?? p.origem} style={ORIGEM_STYLE[p.origem] ?? ''} />
          <Badge text={p.incerteza.charAt(0).toUpperCase() + p.incerteza.slice(1)} style={INCERTEZA_STYLE[p.incerteza] ?? ''} />
        </div>

        <ChevronDown
          size={15}
          className={`flex-shrink-0 text-[#484f58] transition-transform ${aberto ? 'rotate-180' : ''}`}
        />
      </button>

      {aberto && (
        <div className="px-5 pb-5 border-t border-[#21262d] pt-4 space-y-3">
          {/* Barra de probabilidade */}
          {prob !== null && prob !== undefined && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-[#8b949e]">
                <span>Probabilidade estimada</span>
                <span className="font-mono">{(prob * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 bg-[#21262d] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#388bfd] to-[#58a6ff]"
                  style={{ width: `${Math.round(prob * 100)}%` }}
                />
              </div>
              {p.origem === 'hibrido' && probOrig !== null && probOrig !== undefined && (
                <div className="text-xs text-[#8b949e]">
                  Valor calculado original: <span className="text-[#c9a2ff] font-mono">{(probOrig * 100).toFixed(1)}%</span>
                  {' '}→ ajuste qualitativo de{' '}
                  <span className="text-[#c9a2ff] font-mono">
                    {((prob - probOrig) * 100 > 0 ? '+' : '')}{((prob - probOrig) * 100).toFixed(1)}pp
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Justificativa */}
          <div>
            <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-1.5">Justificativa</div>
            <p className="text-[#c9d1d9] text-sm leading-relaxed">{p.justificativa}</p>
          </div>

          {/* Fontes */}
          {p.fontes?.length > 0 && (
            <div>
              <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-1.5">Fontes</div>
              <ul className="space-y-0.5">
                {p.fontes.map((f, i) => (
                  <li key={i} className="text-[#484f58] text-xs font-mono truncate">· {f}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

export default function Relatorio() {
  const [searchParams] = useSearchParams()
  const jogoIdParam = searchParams.get('jogo')
  const qc = useQueryClient()
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

  const { data: relData, isLoading: loadingRel } = useQuery({
    queryKey: ['relatorio', jogoId],
    queryFn: () => api.relatorio(jogoId!),
    enabled: !!jogoId,
    refetchInterval: (q) => {
      const data = q.state.data
      return data?.gerando ? 5000 : false
    },
    staleTime: 0,
  })

  const mutGerar = useMutation({
    mutationFn: () => api.gerarRelatorio(jogoId!),
    onSuccess: () => {
      setTimeout(() => qc.invalidateQueries({ queryKey: ['relatorio', jogoId] }), 2000)
    },
  })

  const mutOficial = useMutation({
    mutationFn: (id: number) => api.marcarOficial(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['relatorio', jogoId] }),
  })

  const rel = relData?.relatorio
  const gerando = relData?.gerando || mutGerar.isPending

  return (
    <div className="px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-black text-[#e6edf3] tracking-tight">Relatório IA</h1>
        <p className="text-[#8b949e] text-sm mt-1.5">
          Análise qualitativa com Claude · pesquisa web · previsões rastreáveis
        </p>
      </div>

      {/* Seletor de jogo */}
      <div className="mb-8 flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-[#8b949e] text-xs font-semibold mb-2 uppercase tracking-wider">Selecionar Jogo</label>
          <div className="relative">
            <select
              className="w-full bg-[#161b22] border border-[#30363d] text-[#e6edf3] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#58a6ff] appearance-none pr-10 cursor-pointer"
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

        <button
          onClick={() => mutGerar.mutate()}
          disabled={gerando || !jogoId}
          className="flex items-center gap-2 px-5 py-3 rounded-xl font-semibold text-sm transition-all duration-150 bg-[#388bfd] hover:bg-[#58a6ff] text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-[#388bfd30]"
        >
          {gerando
            ? <><RefreshCw size={15} className="animate-spin" /> Analisando...</>
            : <><Brain size={15} /> {rel ? 'Nova análise' : 'Gerar análise'}</>
          }
        </button>
      </div>

      {/* Estado: gerando */}
      {gerando && (
        <div className="flex items-center gap-3 text-[#d29922] bg-[#d299221a] border border-[#d2992230] rounded-xl px-5 py-4 mb-6">
          <RefreshCw size={16} className="animate-spin flex-shrink-0" />
          <div>
            <div className="font-semibold text-sm">Análise em andamento</div>
            <div className="text-xs mt-0.5 text-[#8b949e]">Claude está pesquisando + sintetizando. Aguarde 30–60s…</div>
          </div>
        </div>
      )}

      {/* Estado: sem relatório */}
      {!loadingRel && !gerando && !rel && jogoId && (
        <div className="flex flex-col items-center justify-center py-24 text-[#8b949e]">
          <FileText size={48} className="mb-4 opacity-30" />
          <div className="font-semibold text-lg text-[#e6edf3]">Nenhum relatório gerado</div>
          <div className="text-sm mt-1">Clique em "Gerar análise" para acionar o pipeline com Claude.</div>
        </div>
      )}

      {/* Relatório */}
      {rel && (
        <div className="space-y-6">
          {/* Cabeçalho do relatório */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                  {rel.eh_relatorio_oficial && (
                    <Badge text="Relatório Oficial" style="bg-[#3fb9501a] text-[#3fb950] border-[#3fb95030]" />
                  )}
                  <Badge text={`Prompt ${rel.prompt_versao}`} style="bg-[#21262d] text-[#8b949e] border-[#30363d]" />
                  <Badge text={rel.modelo_versao} style="bg-[#21262d] text-[#8b949e] border-[#30363d]" />
                </div>
                <div className="flex items-center gap-2 text-[#484f58] text-xs">
                  <Clock size={11} />
                  Gerado em {new Date(rel.gerado_em).toLocaleString('pt-BR')}
                </div>
              </div>
              {!rel.eh_relatorio_oficial && (
                <button
                  onClick={() => mutOficial.mutate(rel.id)}
                  disabled={mutOficial.isPending}
                  className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-[#3fb950] transition-colors px-3 py-2 rounded-lg border border-[#30363d] hover:border-[#3fb95030] hover:bg-[#3fb9501a]"
                >
                  <Star size={13} />
                  Marcar como oficial
                </button>
              )}
            </div>

            {/* Resumo executivo */}
            <div className="mt-4 pt-4 border-t border-[#21262d]">
              <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-2">Resumo executivo</div>
              <p className="text-[#c9d1d9] text-sm leading-relaxed">{rel.resumo_executivo}</p>
            </div>
          </div>

          {/* Previsões */}
          <div>
            <h2 className="text-[#e6edf3] font-bold text-base mb-4 flex items-center gap-2">
              Previsões por Mercado
              <span className="text-xs text-[#484f58] font-normal">{rel.previsoes?.length ?? 0} mercados avaliados</span>
            </h2>
            <div className="space-y-3">
              {(rel.previsoes ?? []).map((p, i) => (
                <PrevisaoCard key={i} p={p} />
              ))}
            </div>
          </div>

          {/* Legenda de origem */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl px-5 py-4">
            <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-3">Legenda de origem</div>
            <div className="flex flex-wrap gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Badge text="Calculado" style={ORIGEM_STYLE.calculado} />
                <span className="text-[#484f58]">probabilidade diretamente do modelo Dixon-Coles</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge text="Híbrido" style={ORIGEM_STYLE.hibrido} />
                <span className="text-[#484f58]">modelo ajustado pela IA dentro de ±10pp</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge text="Qualitativo" style={ORIGEM_STYLE.qualitativo} />
                <span className="text-[#484f58]">raciocínio da IA, sem número do modelo</span>
              </div>
            </div>
          </div>

          {/* Fatores avaliados */}
          {rel.fatores_avaliados?.length > 0 && (
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl px-5 py-4">
              <div className="flex items-center gap-2 text-[#3fb950] text-sm font-bold mb-3">
                <CheckCircle size={15} />
                Fatores considerados na análise
              </div>
              <div className="flex flex-wrap gap-2">
                {rel.fatores_avaliados.map((f, i) => (
                  <span key={i} className="text-xs text-[#8b949e] bg-[#21262d] border border-[#30363d] rounded-full px-3 py-1">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Fatores ausentes */}
          {rel.fatores_ausentes?.length > 0 && (
            <div className="bg-[#d299221a] border border-[#d2992230] rounded-xl px-5 py-4">
              <div className="flex items-center gap-2 text-[#d29922] text-sm font-bold mb-3">
                <AlertCircle size={15} />
                Fatores NÃO avaliados (rebaixam confiança)
              </div>
              <ul className="space-y-1.5">
                {rel.fatores_ausentes.map((f, i) => (
                  <li key={i} className="text-[#8b949e] text-sm flex items-start gap-2">
                    <span className="text-[#d29922] mt-0.5 flex-shrink-0">·</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Histórico */}
          {relData?.historico && relData.historico.length > 1 && (
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl px-5 py-4">
              <div className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-3">
                Histórico de análises ({relData.historico.length})
              </div>
              <div className="space-y-2">
                {relData.historico.map(h => (
                  <div key={h.id} className="flex items-center gap-3 text-xs">
                    <span className="text-[#484f58] font-mono">{new Date(h.gerado_em).toLocaleString('pt-BR')}</span>
                    {h.oficial && <Badge text="Oficial" style="bg-[#3fb9501a] text-[#3fb950] border-[#3fb95030]" />}
                    {h.id === rel.id && <span className="text-[#58a6ff]">← atual</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
