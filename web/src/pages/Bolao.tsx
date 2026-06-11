import { useQuery } from '@tanstack/react-query'
import { Trophy, Info } from 'lucide-react'
import { api } from '../lib/api'
import type { BolaoResponse, BracketData, BracketMatch } from '../lib/api'
import { flagUrl } from '../lib/flags'

function Flag({ nome, size = 5 }: { nome: string; size?: number }) {
  const u = flagUrl(nome)
  return u
    ? <img src={u} alt={nome} style={{ width: `${size * 4}px` }} className="h-auto rounded-sm inline-block flex-shrink-0" />
    : <span style={{ fontSize: `${size * 3}px` }}>🏳️</span>
}

function abbr(nome?: string): string {
  if (!nome) return ''
  const map: Record<string, string> = {
    'United States': 'EUA', 'South Korea': 'CdS', 'South Africa': 'AFS',
    'Saudi Arabia': 'ARS', 'Czech Republic': 'TCH', 'Ivory Coast': 'CIV',
    'Bosnia & Herzegovina': 'BOS', 'Cape Verde': 'CPV', 'New Zealand': 'NZL',
    'DR Congo': 'COD', 'Netherlands': 'HOL', 'Germany': 'ALE', 'England': 'ING',
    'France': 'FRA', 'Spain': 'ESP', 'Brazil': 'BRA', 'Argentina': 'ARG',
    'Portugal': 'POR', 'Croatia': 'CRO', 'Belgium': 'BEL', 'Morocco': 'MAR',
    'Mexico': 'MEX', 'Norway': 'NOR', 'Japan': 'JAP', 'Uruguay': 'URU',
    'Switzerland': 'SUI', 'Senegal': 'SEN', 'Colombia': 'COL', 'Ecuador': 'EQU',
    'Austria': 'AUT', 'Scotland': 'ESC', 'Canada': 'CAN', 'Turkey': 'TUR',
    'Australia': 'AUS', 'Iran': 'IRA', 'Egypt': 'EGI', 'Algeria': 'AGL',
    'Tunisia': 'TUN', 'Panama': 'PAN', 'Paraguay': 'PAR', 'Qatar': 'CAT',
    'Ghana': 'GAN', 'Haiti': 'HAI', 'Jordan': 'JOR', 'Iraq': 'IRQ',
    'Uzbekistan': 'UZB', 'Curaçao': 'CUR',
  }
  return map[nome] ?? nome.slice(0, 3).toUpperCase()
}

// ---------------------------------------------------------------------------
// Bracket (chaveamento)
// ---------------------------------------------------------------------------

function TeamRow({ nome, win }: { nome?: string; win: boolean }) {
  return (
    <div className={`flex items-center gap-1.5 px-1.5 h-[22px] rounded ${win ? 'bg-[#3fb95018]' : ''}`}>
      <Flag nome={nome ?? ''} size={4} />
      <span className={`text-[10px] leading-none tabular-nums ${win ? 'text-[#e6edf3] font-bold' : 'text-[#6e7681]'}`}>{abbr(nome)}</span>
    </div>
  )
}

function MatchBox({ m }: { m: BracketMatch | null }) {
  return (
    <div className="w-[58px] bg-[#0d1117] border border-[#30363d] rounded-md py-0.5 my-1">
      <TeamRow nome={m?.home} win={!!m && m.winner === m.home} />
      <TeamRow nome={m?.away} win={!!m && m.winner === m.away} />
    </div>
  )
}

function Conn({ side }: { side: 'l' | 'r' }) {
  // espinha vertical 25%-75% + traço horizontal no centro (árvore simétrica → exato)
  const v = side === 'l' ? 'right-0' : 'left-0'
  return (
    <div className="w-3 self-stretch relative">
      <div className={`absolute ${v} top-1/4 bottom-1/4 border-l border-[#30363d]`} />
      <div className={`absolute ${v} top-1/2 w-full border-t border-[#30363d]`} />
    </div>
  )
}

function Node({ rounds, r, i, side }: { rounds: (BracketMatch | null)[][]; r: number; i: number; side: 'l' | 'r' }) {
  const box = <MatchBox m={rounds[r]?.[i] ?? null} />
  if (r === 0) return box
  const filhos = (
    <div className="flex flex-col">
      <Node rounds={rounds} r={r - 1} i={2 * i} side={side} />
      <Node rounds={rounds} r={r - 1} i={2 * i + 1} side={side} />
    </div>
  )
  return side === 'l'
    ? <div className="flex items-center">{filhos}<Conn side="l" />{box}</div>
    : <div className="flex items-center">{box}<Conn side="r" />{filhos}</div>
}

function Bracket({ b }: { b: BracketData }) {
  const rootL = b.esq.length - 1
  const rootR = b.dir.length - 1
  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-center justify-center min-w-[900px] gap-1">
        {/* Esquerda */}
        <Node rounds={b.esq} r={rootL} i={0} side="l" />

        {/* Centro: final + campeão */}
        <div className="flex flex-col items-center px-2">
          <Trophy size={26} className="text-[#d29922] mb-1" />
          <div className="text-[10px] text-[#8b949e] uppercase tracking-wide">Campeão</div>
          <div className="flex items-center gap-1.5 my-1">
            <Flag nome={b.campeao ?? ''} size={6} />
            <span className="text-[#e6edf3] font-black text-sm">{b.campeao}</span>
          </div>
          <div className="w-[64px] bg-[#0d1117] border border-[#d2992240] rounded-md py-0.5 mt-1">
            <TeamRow nome={b.final?.home} win={!!b.final && b.final.winner === b.final.home} />
            <TeamRow nome={b.final?.away} win={!!b.final && b.final.winner === b.final.away} />
          </div>
          <div className="text-[9px] text-[#484f58] mt-1">Final</div>
        </div>

        {/* Direita */}
        <Node rounds={b.dir} r={rootR} i={0} side="r" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------------

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.round(pct * 100)}%`, background: color }} />
    </div>
  )
}

export default function Bolao() {
  const { data, isLoading, error } = useQuery<BolaoResponse>({
    queryKey: ['bolao'],
    queryFn: api.bolao,
    staleTime: 30 * 60 * 1000,
  })

  return (
    <div className="px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-black text-[#e6edf3] tracking-tight flex items-center gap-2">
          <Trophy size={26} className="text-[#d29922]" /> Bolão
        </h1>
        <p className="text-[#8b949e] text-sm mt-1.5">
          O que os números diriam — simulação Monte Carlo do torneio inteiro a partir das previsões do modelo.
        </p>
      </div>

      <div className="flex items-start gap-2 text-[#8b949e] bg-[#388bfd0d] border border-[#388bfd20] rounded-xl px-4 py-3 mb-8 text-xs leading-relaxed">
        <Info size={15} className="text-[#58a6ff] flex-shrink-0 mt-0.5" />
        <span>
          Cada jogo (grupos + mata-mata) é sorteado milhares de vezes pelo modelo Dixon-Coles. O chaveamento (incl. 8 melhores
          terceiros) é o oficial, lido das fixtures. O bracket mostra o <span className="text-[#c9d1d9]">caminho mais provável</span>
          {' '}(em cada jogo avança o favorito); o resto são <span className="text-[#c9d1d9]">probabilidades</span>.
          {data && <span className="text-[#484f58]"> · {data.n_simulacoes.toLocaleString('pt-BR')} simulações</span>}
        </span>
      </div>

      {isLoading && <div className="text-[#8b949e] text-sm py-16 text-center animate-pulse">Simulando o torneio…</div>}
      {error && <div className="text-[#f85149] bg-[#f851491a] border border-[#f8514930] rounded-xl px-5 py-4 text-sm">Erro ao carregar a simulação.</div>}

      {data && (
        <div className="space-y-10">
          {/* Chaveamento provável */}
          {data.bracket && data.bracket.campeao && (
            <div>
              <h2 className="text-[#e6edf3] font-bold text-base mb-1">Chaveamento provável</h2>
              <p className="text-[#484f58] text-xs mb-4">Caminho mais provável — em cada confronto avança o favorito do modelo.</p>
              <div className="bg-[#161b22] border border-[#30363d] rounded-2xl p-5">
                <Bracket b={data.bracket} />
                {data.bracket.terceiro && (
                  <div className="text-center text-[11px] text-[#8b949e] mt-3 pt-3 border-t border-[#21262d]">
                    3º lugar: <span className="text-[#c9d1d9] font-semibold">{data.bracket.terceiro.winner}</span>
                    {' '}(venceu {data.bracket.terceiro.winner === data.bracket.terceiro.home ? data.bracket.terceiro.away : data.bracket.terceiro.home})
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Favoritos ao título */}
          <div>
            <h2 className="text-[#e6edf3] font-bold text-base mb-4">Favoritos ao título</h2>
            <div className="bg-[#161b22] border border-[#30363d] rounded-2xl overflow-hidden">
              <div className="grid grid-cols-[2rem_1fr_repeat(4,4.5rem)] gap-2 px-5 py-3 text-[10px] font-bold uppercase tracking-wide text-[#484f58] border-b border-[#30363d]">
                <span>#</span><span>Seleção</span>
                <span className="text-right">Campeão</span><span className="text-right">Final</span>
                <span className="text-right">Semi</span><span className="text-right">Quartas</span>
              </div>
              {data.favoritos.slice(0, 16).map((f, i) => (
                <div key={f.time} className="grid grid-cols-[2rem_1fr_repeat(4,4.5rem)] gap-2 px-5 py-2.5 items-center border-b border-[#21262d] last:border-0 hover:bg-[#1c2128]">
                  <span className={`text-sm font-black ${i < 3 ? 'text-[#d29922]' : 'text-[#484f58]'}`}>{i + 1}</span>
                  <span className="flex items-center gap-2 text-[#e6edf3] text-sm font-semibold min-w-0">
                    <Flag nome={f.time} /> <span className="truncate">{f.time}</span>
                  </span>
                  <span className="text-right text-[#58a6ff] font-black tabular-nums text-sm">{(f.p_campeao * 100).toFixed(1)}%</span>
                  <span className="text-right text-[#c9d1d9] tabular-nums text-xs">{(f.p_final * 100).toFixed(1)}%</span>
                  <span className="text-right text-[#8b949e] tabular-nums text-xs">{(f.p_semi * 100).toFixed(0)}%</span>
                  <span className="text-right text-[#8b949e] tabular-nums text-xs">{(f.p_quartas * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* Grupos */}
          <div>
            <h2 className="text-[#e6edf3] font-bold text-base mb-4">Por grupo — quem avança</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {Object.entries(data.grupos).map(([g, linhas]) => (
                <div key={g} className="bg-[#161b22] border border-[#30363d] rounded-2xl p-5">
                  <div className="text-[#8b949e] text-xs font-bold uppercase tracking-wider mb-3">Grupo {g}</div>
                  <div className="space-y-2.5">
                    {linhas.map((l) => (
                      <div key={l.time} className="flex items-center gap-2.5">
                        <span className={`w-6 text-[10px] font-black flex-shrink-0 ${l.cravado === '1º' ? 'text-[#3fb950]' : l.cravado === '2º' ? 'text-[#58a6ff]' : 'text-[#30363d]'}`}>
                          {l.cravado || '—'}
                        </span>
                        <Flag nome={l.time} />
                        <span className="text-[#c9d1d9] text-xs flex-1 truncate">{l.time}</span>
                        <Bar pct={l.p_avanca} color={l.p_avanca > 0.5 ? '#3fb950' : '#484f58'} />
                        <span className="text-[#e6edf3] text-xs font-bold tabular-nums w-9 text-right">{Math.round(l.p_avanca * 100)}%</span>
                      </div>
                    ))}
                  </div>
                  <div className="text-[10px] text-[#484f58] mt-3 flex items-center gap-3">
                    <span><span className="text-[#3fb950] font-bold">1º</span>/<span className="text-[#58a6ff] font-bold">2º</span> = palpite cravado</span>
                    <span>% = chance de avançar</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
