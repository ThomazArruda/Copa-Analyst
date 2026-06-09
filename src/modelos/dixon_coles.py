"""
Motor Dixon-Coles ancorado no rating prior (Elo).
PRD Seção 7.1.

Fluxo:
  1. Converter Elo → parâmetros de ataque/defesa (prior)
  2. Estimar parâmetros a partir de dados observados (forma recente)
  3. Shrinkage: mesclar prior + observado conforme qtd de jogos disponíveis
  4. Calcular λ, μ (gols esperados por cada time)
  5. Gerar matriz de probabilidade de placares com correção τ (Dixon-Coles)
  6. Derivar probabilidades para todos os mercados calculáveis

Parâmetros versionados (PRD Seção 7.1 — nunca mudar silenciosamente):
    DECAIMENTO_TEMPORAL = 0.005
    SHRINKAGE_PRIOR     = 0.7
    JANELA_FORMA        = 10
    HA_REAL             = 0.25   (log-odds, anfitriões Copa 2026)
    RHO                 = -0.13  (correção Dixon-Coles para 0-0)
    LOG_MEDIA_GOLS      = log(1.30)  (média gols/time/jogo em Copas)
    ELO_SCALE           = 400.0  (escala Elo → diferença de gols esperados)
    MAX_GOLS            = 8      (truncamento da matriz de placares)
"""

import math
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.stats import poisson

from src.db.repositorio import Repositorio, Jogo, Time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parâmetros versionados — alterar aqui exige nota no DECISIONS.md
# ---------------------------------------------------------------------------
DECAIMENTO_TEMPORAL = 0.005   # decaimento exponencial por jogo anterior
SHRINKAGE_PRIOR     = 0.70    # 0=só dados, 1=só prior
SHRINKAGE_FLOOR     = 0.60    # piso: o Elo retém ≥60% mesmo com muitos jogos
                              # (impede goleada intra-confederação de inflar ataque)
JANELA_FORMA        = 40      # usa TODOS os jogos recentes (decaimento pondera os antigos)
HA_REAL             = 0.25    # vantagem de casa em log-odds (anfitriões somente)

# Peso por competição: Copa (cross-confederação) vale mais que qualificatória
# (intra-confederação, força do adversário já no Elo) e amistoso. Nada é descartado.
PESOS_COMPETICAO = {"copa_2026": 1.0, "copa_2022": 1.0}
PESO_QUALIFICATORIA = 0.5
PESO_AMISTOSO = 0.4


def _peso_competicao(competicao: str) -> float:
    if not competicao:
        return PESO_QUALIFICATORIA
    if competicao.startswith("amistos"):
        return PESO_AMISTOSO
    return PESOS_COMPETICAO.get(competicao, PESO_QUALIFICATORIA)
RHO                 = -0.13   # parâmetro de dependência Dixon-Coles
LOG_MEDIA_GOLS      = math.log(1.30)  # ln(média gols/time/jogo em Copas)
ELO_SCALE           = 400.0   # Elo → parâmetro log-gols (mesmo da fórmula Elo)
MAX_GOLS            = 8       # truncamento da matriz de placares

# Anfitriões Copa 2026 — HA aplicado APENAS para eles em casa (PRD 7.1)
ANFITRIOES = {"Canada", "United States", "Mexico"}

# Gols médios por time por jogo usados como referência
MEDIA_GOLS = math.exp(LOG_MEDIA_GOLS)


# ---------------------------------------------------------------------------
# Output structures
# ---------------------------------------------------------------------------

@dataclass
class ParametrosTime:
    nome: str
    elo: float
    alpha: float   # parâmetro de ataque (log-space, centrado em 0)
    beta: float    # parâmetro de defesa (log-space, centrado em 0)
    n_jogos: int   # quantos jogos usados na estimativa
    cold_start: bool  # True se baseado só no prior


@dataclass
class PrevisaoCalculada:
    """Saída do motor estatístico para um jogo."""
    lambda_m: float                    # gols esperados mandante
    mu_v: float                        # gols esperados visitante
    matriz: np.ndarray                 # shape (MAX_GOLS+1, MAX_GOLS+1)
    # Resultado
    prob_vitoria_m: float
    prob_empate: float
    prob_vitoria_v: float
    # Over/Under gols totais
    prob_over: dict = field(default_factory=dict)  # {0.5: p, 1.5: p, 2.5: p, 3.5: p}
    # Ambas marcam
    prob_ambas_marcam: float = 0.0
    # Placar mais provável
    placar_mais_provavel: tuple = (1, 0)
    # Metadados
    params_m: Optional[ParametrosTime] = None
    params_v: Optional[ParametrosTime] = None
    ha_aplicado: float = 0.0
    cold_start: bool = False


# ---------------------------------------------------------------------------
# Motor principal
# ---------------------------------------------------------------------------

class DixonColes:
    def __init__(self, repo: Repositorio):
        self.repo = repo

    # --- Parâmetros com shrinkage ---

    def _elo_para_param(self, elo: float) -> float:
        """
        Converte Elo em parâmetro log-gols centrado em 0.
        Um time com Elo 1500 tem alpha=beta=0 (time médio).
        Fórmula: (elo - 1500) / ELO_SCALE × ln(10)/4
        """
        return (elo - 1500) / ELO_SCALE * (math.log(10) / 4)

    def _estimar_params(self, time: Time, forma: list[Jogo],
                        time_id_ref: int) -> ParametrosTime:
        """
        Estima parâmetros de ataque e defesa com shrinkage para o prior Elo.

        forma: lista de jogos recentes (já filtrada, até JANELA_FORMA)
        time_id_ref: ID do time que estamos estimando
        """
        elo = time.rating_prior or 1500.0
        alpha_prior = self._elo_para_param(elo)
        beta_prior  = self._elo_para_param(elo)  # times fortes defendem bem também

        # Usa TODOS os jogos disponíveis (Copa + qualificatórias + amistosos).
        # Nenhum dado é descartado: cada jogo contribui com peso =
        #   decaimento por recência × peso da competição.
        # O risco de inflação intra-confederação (Brasil goleando a CONMEBOL) é
        # contido pelo SHRINKAGE_FLOOR: o Elo — que já codifica a força do
        # adversário — retém peso mínimo garantido. (PRD 7.1: usar os jogos
        # disponíveis com regularização ao prior.)
        jogos = [j for j in forma
                 if j.placar_mandante is not None
                 and j.placar_visitante is not None]

        if not jogos:
            return ParametrosTime(
                nome=time.nome, elo=elo,
                alpha=alpha_prior, beta=beta_prior,
                n_jogos=0, cold_start=True,
            )

        gols_pro    = []
        gols_contra = []
        pesos       = []
        for i, jogo in enumerate(jogos):
            peso = math.exp(-DECAIMENTO_TEMPORAL * i) * _peso_competicao(jogo.competicao)
            pesos.append(peso)
            if jogo.time_mandante_id == time_id_ref:
                gols_pro.append(jogo.placar_mandante)
                gols_contra.append(jogo.placar_visitante)
            else:
                gols_pro.append(jogo.placar_visitante)
                gols_contra.append(jogo.placar_mandante)

        soma_pesos   = sum(pesos)
        media_pro    = sum(g * p for g, p in zip(gols_pro,    pesos)) / soma_pesos
        media_contra = sum(g * p for g, p in zip(gols_contra, pesos)) / soma_pesos

        # Parâmetros observados em log-space centrado
        alpha_obs = math.log(max(media_pro,   0.05)) - LOG_MEDIA_GOLS
        beta_obs  = math.log(max(media_contra, 0.05)) - LOG_MEDIA_GOLS
        beta_obs  = -beta_obs  # menor concessão = maior defesa

        # n efetivo = soma dos pesos. Shrinkage decai com mais dados, mas nunca
        # abaixo do piso (Elo sempre retém ≥ SHRINKAGE_FLOOR).
        n_eff = soma_pesos
        s = max(SHRINKAGE_FLOOR, SHRINKAGE_PRIOR * math.exp(-n_eff / 5))

        alpha = s * alpha_prior + (1 - s) * alpha_obs
        beta  = s * beta_prior  + (1 - s) * beta_obs

        return ParametrosTime(
            nome=time.nome, elo=elo,
            alpha=alpha, beta=beta,
            n_jogos=len(jogos), cold_start=(n_eff < 3),
        )

    # --- Correção τ de Dixon-Coles ---

    @staticmethod
    def _tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
        """
        Fator de correção para dependência em placares baixos.
        τ(0,0) = 1 − λμρ
        τ(1,0) = 1 + μρ
        τ(0,1) = 1 + λρ
        τ(1,1) = 1 − ρ
        τ(i,j) = 1  para i+j > 2
        """
        if i == 0 and j == 0:
            return 1 - lam * mu * rho
        if i == 1 and j == 0:
            return 1 + mu * rho
        if i == 0 and j == 1:
            return 1 + lam * rho
        if i == 1 and j == 1:
            return 1 - rho
        return 1.0

    # --- Matriz de placares ---

    def _matriz_placares(self, lam: float, mu: float) -> np.ndarray:
        """
        Gera matriz (MAX_GOLS+1) × (MAX_GOLS+1) de probabilidades de placar.
        Linhas = gols mandante, colunas = gols visitante.
        """
        n = MAX_GOLS + 1
        mat = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                p = (poisson.pmf(i, lam) * poisson.pmf(j, mu)
                     * self._tau(i, j, lam, mu, RHO))
                mat[i, j] = max(p, 0.0)  # τ pode gerar valor levemente negativo

        # Normalizar para somar 1 (truncamento introduz pequeno erro)
        total = mat.sum()
        if total > 0:
            mat /= total
        return mat

    # --- Derivar mercados da matriz ---

    @staticmethod
    def _derivar_mercados(mat: np.ndarray, lam: float, mu: float) -> dict:
        n = mat.shape[0]

        # Resultado — usar sum() nativo (np.sum com generator deprecado no numpy moderno)
        prob_vitoria_m = float(sum(mat[i, j] for i in range(n) for j in range(n) if i > j))
        prob_empate    = float(sum(mat[i, i] for i in range(n)))
        prob_vitoria_v = float(sum(mat[i, j] for i in range(n) for j in range(n) if j > i))

        # Over/Under
        over = {}
        for linha in [0.5, 1.5, 2.5, 3.5]:
            p_over = float(sum(mat[i, j] for i in range(n) for j in range(n) if i + j > linha))
            over[linha] = p_over

        # Ambas marcam
        ambas = float(sum(mat[i, j] for i in range(1, n) for j in range(1, n)))

        # Placar mais provável
        idx = np.unravel_index(np.argmax(mat), mat.shape)
        placar_mv = (int(idx[0]), int(idx[1]))

        return {
            "vitoria_mandante": prob_vitoria_m,
            "empate":           prob_empate,
            "vitoria_visitante": prob_vitoria_v,
            "over":             over,
            "ambas_marcam":     ambas,
            "placar_mais_provavel": placar_mv,
        }

    # --- Verificar vantagem de casa ---

    def _calcular_ha(self, jogo: Jogo, time_m: Time) -> float:
        """
        Vantagem de casa em log-odds.
        Zero para campo neutro (quase toda a Copa 2026).
        HA_REAL apenas para Canadá, EUA e México jogando em casa (PRD 7.1).
        """
        if jogo.campo_neutro:
            return 0.0
        if time_m and time_m.nome in ANFITRIOES:
            return HA_REAL
        return 0.0

    # --- Ponto de entrada principal ---

    def prever(self, jogo: Jogo, time_m: Time, time_v: Time,
               forma_m: list[Jogo], forma_v: list[Jogo]) -> PrevisaoCalculada:
        """
        Gera previsão estatística completa para um jogo.

        jogo:    objeto Jogo (com campo_neutro, etc.)
        time_m:  time mandante (com rating_prior)
        time_v:  time visitante
        forma_m: últimos JANELA_FORMA jogos do mandante com resultado
        forma_v: últimos JANELA_FORMA jogos do visitante com resultado
        """
        # Parâmetros com shrinkage
        pm = self._estimar_params(time_m, forma_m[:JANELA_FORMA], time_m.id)
        pv = self._estimar_params(time_v, forma_v[:JANELA_FORMA], time_v.id)

        # Vantagem de casa
        ha = self._calcular_ha(jogo, time_m)

        # Gols esperados
        lam = math.exp(LOG_MEDIA_GOLS + pm.alpha - pv.beta + ha)
        mu  = math.exp(LOG_MEDIA_GOLS + pv.alpha - pm.beta)

        # Garantir valores sensatos (entre 0.1 e 8)
        lam = min(max(lam, 0.1), 8.0)
        mu  = min(max(mu,  0.1), 8.0)

        # Matriz de placares
        mat = self._matriz_placares(lam, mu)

        # Derivar mercados
        mkt = self._derivar_mercados(mat, lam, mu)

        cold_start = pm.cold_start or pv.cold_start

        return PrevisaoCalculada(
            lambda_m=round(lam, 3),
            mu_v=round(mu, 3),
            matriz=mat,
            prob_vitoria_m=round(mkt["vitoria_mandante"], 4),
            prob_empate=round(mkt["empate"], 4),
            prob_vitoria_v=round(mkt["vitoria_visitante"], 4),
            prob_over=mkt["over"],
            prob_ambas_marcam=round(mkt["ambas_marcam"], 4),
            placar_mais_provavel=mkt["placar_mais_provavel"],
            params_m=pm,
            params_v=pv,
            ha_aplicado=ha,
            cold_start=cold_start,
        )

    def prever_por_pacote(self, pacote: dict) -> PrevisaoCalculada:
        """
        Interface de alto nível: recebe o pacote de ingestao.pacote_jogo()
        e retorna a previsão calculada.
        """
        jogo   = pacote["jogo"]
        time_m = pacote["time_mandante"]
        time_v = pacote["time_visitante"]

        if not time_m or not time_v:
            raise ValueError("Pacote sem time_mandante ou time_visitante")

        # Forma combinada: Copa 2026 primeiro (mais recente), depois forma geral.
        # Dedup por id (jogos de Copa aparecem nas duas listas) preservando ordem.
        def _combinar(copa, recente):
            vistos = set()
            out = []
            for j in copa + recente:
                if j.id not in vistos:
                    vistos.add(j.id)
                    out.append(j)
            return out[:JANELA_FORMA]

        forma_m = _combinar(pacote["forma_copa"]["mandante"], pacote["forma_recente"]["mandante"])
        forma_v = _combinar(pacote["forma_copa"]["visitante"], pacote["forma_recente"]["visitante"])

        return self.prever(jogo, time_m, time_v, forma_m, forma_v)
