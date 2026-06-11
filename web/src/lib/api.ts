const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path, { method: 'POST' })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export interface Jogo {
  id: number
  data: string
  hora: string
  mandante: string
  visitante: string
  mandante_elo: number | null
  visitante_elo: number | null
  grupo: string
  fase: string
  cidade: string
  placar_m: number | null
  placar_v: number | null
}

export interface Previsao {
  ok: boolean
  mandante: string
  visitante: string
  prob_vitoria_m: number
  prob_empate: number
  prob_vitoria_v: number
  gols_esperados_m: number
  gols_esperados_v: number
  prob_over: Record<string, number>
  cold_start: boolean
  tags: string[]
  fatores_ausentes: string[]
}

export interface Mercado {
  media_esperada: number
  prob_linhas: Record<string, number>
  intervalo_80pct: [number, number]
  ausente: boolean
  parcial?: boolean
  nota?: string
}

export interface AnaliseCompleta {
  ok: boolean
  jogo: { id: number; data: string; hora: string; cidade: string; grupo: string; fase: string }
  mandante: { nome: string; elo: number | null }
  visitante: { nome: string; elo: number | null }
  previsao: {
    prob_vitoria_m: number
    prob_empate: number
    prob_vitoria_v: number
    gols_esperados_m: number
    gols_esperados_v: number
    prob_over: Record<string, number>
    cold_start: boolean
  }
  mercados: Record<string, Mercado>
  forma_recente: {
    mandante: FormaJogo[]
    visitante: FormaJogo[]
  }
  head_to_head: FormaJogo[]
  fatores_ausentes: string[]
}

export interface FormaJogo {
  data: string
  mandante: string
  visitante: string
  placar_m: number | null
  placar_v: number | null
  competicao: string
}

export interface Status {
  jogos_total: number
  copa26_fixtures: number
  relatorios: number
  previsoes_oficiais: number
  times: number
}

export interface TopElo {
  nome: string
  elo: number
  grupo: string | null
}

export interface PrevisaoIA {
  mercado: string
  previsao: string
  probabilidade_estimada: number | null
  probabilidade_calculada_original: number | null
  incerteza: 'baixa' | 'media' | 'alta'
  origem: 'calculado' | 'qualitativo' | 'hibrido'
  justificativa: string
  fontes: string[]
}

export interface Relatorio {
  id: number
  jogo_id: number
  gerado_em: string
  prompt_versao: string
  modelo_versao: string
  eh_relatorio_oficial: boolean
  resumo_executivo: string
  fatores_avaliados: string[]
  fatores_ausentes: string[]
  previsoes: PrevisaoIA[]
}

export interface RelatorioResponse {
  ok: boolean
  gerando: boolean
  erro?: string | null
  relatorio: Relatorio | null
  historico: { id: number; gerado_em: string; oficial: boolean }[]
}

export interface MetricaMercado {
  mercado: string
  n: number
  brier_score: number
  log_loss: number
  acerto_binario: number
  ruido_alto: boolean
  alerta_leakage: boolean
}

export interface PontoCalibracao {
  prob_prevista: number
  freq_real: number
  n: number
}

export interface CalibracaoResponse {
  total_avaliados: number
  relatorios_oficiais: number
  msg: string | null
  por_mercado?: MetricaMercado[]
  aviso_ruido?: string | null
  alerta_leakage?: string | null
  pontos_calibracao?: PontoCalibracao[]
}

export interface BolaoGrupoLinha {
  time: string
  pts_medio: number
  p_1o: number
  p_avanca: number
  cravado: string
}
export interface BolaoFavorito {
  time: string
  p_campeao: number
  p_final: number
  p_semi: number
  p_quartas: number
  p_oitavas: number
  p_avanca: number
}
export interface BolaoResponse {
  n_simulacoes: number
  grupos: Record<string, BolaoGrupoLinha[]>
  favoritos: BolaoFavorito[]
}

export const api = {
  jogos: (data?: string) => get<Jogo[]>(data ? `/jogos?data=${data}` : '/jogos'),
  datas: () => get<string[]>('/jogos/datas'),
  previsao: (id: number) => get<Previsao>(`/jogos/${id}/previsao`),
  analise: (id: number) => get<AnaliseCompleta>(`/jogos/${id}/analise`),
  status: () => get<Status>('/status'),
  topElo: () => get<TopElo[]>('/top-elo'),
  atualizar: () => post<{ ok: boolean; msg: string }>('/atualizar'),
  recalcularElo: () => post<{ ok: boolean; times_atualizados: number }>('/recalcular-elo'),
  calibracao: () => get<CalibracaoResponse>('/calibracao'),
  relatorio: (jogoId: number) => get<RelatorioResponse>(`/jogos/${jogoId}/relatorio`),
  gerarRelatorio: (jogoId: number, modelo?: string) =>
    post<{ ok: boolean; msg: string }>(
      `/jogos/${jogoId}/gerar-relatorio${modelo ? `?modelo=${modelo}` : ''}`
    ),
  marcarOficial: (relatorioId: number) => post<{ ok: boolean; motivo?: string }>(`/relatorios/${relatorioId}/marcar-oficial`),
  bolao: () => get<BolaoResponse>('/bolao'),
}
